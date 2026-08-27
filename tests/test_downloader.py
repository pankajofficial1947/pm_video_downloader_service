from pathlib import Path

import pytest

import config
from downloader import _resolve_downloaded_file, download, fetch_info
from models import DownloadFormat, Quality


class _FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL: returns canned metadata and writes a fake file."""

    calls = []
    duration = 42
    raise_on_download = None

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def extract_info(self, url, download=True):
        _FakeYoutubeDL.calls.append({"url": url, "download": download, "opts": self.opts})
        if download and _FakeYoutubeDL.raise_on_download:
            raise _FakeYoutubeDL.raise_on_download

        info = {
            "title": "Sample Video",
            "duration": _FakeYoutubeDL.duration,
            "thumbnail": "https://example.com/thumb.jpg",
            "uploader": "Example Channel",
            "webpage_url": url,
            "extractor": "youtube",
        }
        if download:
            ext = "mp3" if self.opts.get("postprocessors") else "mp4"
            path = Path(self.opts["outtmpl"].replace("%(ext)s", ext))
            path.write_bytes(b"fake-media-bytes")
            for hook in self.opts.get("progress_hooks", []):
                hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
                hook({"status": "finished"})
        return info


@pytest.fixture(autouse=True)
def fake_ydl(monkeypatch):
    _FakeYoutubeDL.calls = []
    _FakeYoutubeDL.duration = 42
    _FakeYoutubeDL.raise_on_download = None
    monkeypatch.setattr("downloader.yt_dlp.YoutubeDL", _FakeYoutubeDL)
    yield


def test_fetch_info_returns_simplified_fields():
    info = fetch_info("https://youtube.com/watch?v=abc")
    assert info == {
        "title": "Sample Video",
        "duration": 42,
        "thumbnail": "https://example.com/thumb.jpg",
        "uploader": "Example Channel",
        "webpage_url": "https://youtube.com/watch?v=abc",
        "extractor": "youtube",
    }


def test_download_returns_bytes_and_reports_progress():
    events = []
    result = download(
        "https://youtube.com/watch?v=abc",
        DownloadFormat.VIDEO,
        Quality.BEST,
        progress_callback=lambda pct, status: events.append((pct, status)),
    )
    assert result.title == "Sample Video"
    assert result.filename.endswith(".mp4")
    assert result.data == b"fake-media-bytes"
    # "preparing"/"connecting" fire before any byte transfer starts, so the
    # UI has something to show during yt-dlp's own (sometimes multi-second)
    # metadata lookups instead of sitting frozen on its initial text.
    assert events[0] == (0.0, "preparing")
    assert (0.0, "connecting") in events
    assert events[-1] == (100.0, "completed")
    assert (50.0, "downloading") in events
    assert (99.0, "processing") in events


def test_download_works_without_progress_callback():
    result = download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)
    assert result.data == b"fake-media-bytes"


def test_download_audio_uses_mp3_extension_and_postprocessor():
    result = download("https://youtube.com/watch?v=abc", DownloadFormat.AUDIO, Quality.BEST)
    assert result.filename.endswith(".mp3")

    download_call = next(c for c in _FakeYoutubeDL.calls if c["download"])
    assert download_call["opts"]["postprocessors"][0]["key"] == "FFmpegExtractAudio"


def test_quality_cap_selects_matching_format_string():
    download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.Q720)
    download_call = next(c for c in _FakeYoutubeDL.calls if c["download"])
    assert download_call["opts"]["format"] == config.QUALITY_FORMAT_MAP["720p"]


def test_opts_always_point_yt_dlp_at_bundled_ffmpeg():
    download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)
    download_call = next(c for c in _FakeYoutubeDL.calls if c["download"])
    assert download_call["opts"]["ffmpeg_location"] == config.FFMPEG_LOCATION


def test_download_propagates_exception():
    _FakeYoutubeDL.raise_on_download = RuntimeError("network exploded")
    with pytest.raises(RuntimeError, match="network exploded"):
        download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)


def test_download_translates_likely_ip_block_into_clear_message():
    _FakeYoutubeDL.raise_on_download = RuntimeError("ERROR: The downloaded file is empty")
    with pytest.raises(RuntimeError, match="blocking or throttling"):
        download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)


def test_opts_include_player_client_fallback_and_retries():
    download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)
    download_call = next(c for c in _FakeYoutubeDL.calls if c["download"])
    opts = download_call["opts"]
    assert opts["extractor_args"] == {"youtube": {"player_client": config.YOUTUBE_PLAYER_CLIENTS}}
    assert opts["retries"] == 5
    assert opts["fragment_retries"] == 5


def test_duration_over_limit_raises_without_downloading(monkeypatch):
    monkeypatch.setattr(config, "MAX_VIDEO_DURATION_SECONDS", 10)
    _FakeYoutubeDL.duration = 42
    with pytest.raises(ValueError, match="exceeds"):
        download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)
    assert all(not c["download"] for c in _FakeYoutubeDL.calls)


def test_duration_check_disabled_when_limit_is_zero(monkeypatch):
    monkeypatch.setattr(config, "MAX_VIDEO_DURATION_SECONDS", 0)
    _FakeYoutubeDL.duration = 999999
    result = download("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST)
    assert result.data == b"fake-media-bytes"


def test_resolve_downloaded_file_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        _resolve_downloaded_file(tmp_path, "no-such-job")


def test_resolve_downloaded_file_ignores_partial_files(tmp_path):
    (tmp_path / "job1.part").write_bytes(b"partial")
    final = tmp_path / "job1.mp4"
    final.write_bytes(b"done")
    resolved = _resolve_downloaded_file(tmp_path, "job1")
    assert resolved == final
