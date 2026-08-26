from pathlib import Path

import pytest

from src import config
from src.downloader import JobManager, fetch_info
from src.models import DownloadFormat, JobStatus, Quality


class _SyncExecutor:
    """Runs submitted jobs inline so tests don't need to poll background threads."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

    def shutdown(self, wait=True):
        pass


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
def reset_fake_ydl():
    _FakeYoutubeDL.calls = []
    _FakeYoutubeDL.duration = 42
    _FakeYoutubeDL.raise_on_download = None
    yield


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr("src.downloader.yt_dlp.YoutubeDL", _FakeYoutubeDL)
    return JobManager(executor=_SyncExecutor())


def test_fetch_info_returns_simplified_fields(monkeypatch):
    monkeypatch.setattr("src.downloader.yt_dlp.YoutubeDL", _FakeYoutubeDL)
    info = fetch_info("https://youtube.com/watch?v=abc")
    assert info == {
        "title": "Sample Video",
        "duration": 42,
        "thumbnail": "https://example.com/thumb.jpg",
        "uploader": "Example Channel",
        "webpage_url": "https://youtube.com/watch?v=abc",
        "extractor": "youtube",
    }


def test_create_job_completes_and_produces_file(manager):
    job_id = manager.create_job(
        "https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST
    )
    job = manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100.0
    assert job.title == "Sample Video"
    assert job.filename == f"{job_id}.mp4"

    path = manager.get_file_path(job_id)
    assert path.exists()
    assert path.read_bytes() == b"fake-media-bytes"


def test_create_job_audio_uses_mp3_extension_and_postprocessor(manager):
    job_id = manager.create_job(
        "https://youtube.com/watch?v=abc", DownloadFormat.AUDIO, Quality.BEST
    )
    job = manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.filename == f"{job_id}.mp3"

    download_call = next(c for c in _FakeYoutubeDL.calls if c["download"])
    assert download_call["opts"]["postprocessors"][0]["key"] == "FFmpegExtractAudio"


def test_quality_cap_selects_matching_format_string(manager):
    manager.create_job("https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.Q720)
    download_call = next(c for c in _FakeYoutubeDL.calls if c["download"])
    assert download_call["opts"]["format"] == config.QUALITY_FORMAT_MAP["720p"]


def test_job_marked_failed_on_download_exception(manager):
    _FakeYoutubeDL.raise_on_download = RuntimeError("network exploded")
    job_id = manager.create_job(
        "https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST
    )
    job = manager.get_job(job_id)
    assert job.status == JobStatus.FAILED
    assert "network exploded" in job.error


def test_duration_over_limit_fails_job_without_downloading(manager, monkeypatch):
    monkeypatch.setattr(config, "MAX_VIDEO_DURATION_SECONDS", 10)
    _FakeYoutubeDL.duration = 42
    job_id = manager.create_job(
        "https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST
    )
    job = manager.get_job(job_id)
    assert job.status == JobStatus.FAILED
    assert "exceeds" in job.error
    assert all(not c["download"] for c in _FakeYoutubeDL.calls)


def test_duration_check_disabled_when_limit_is_zero(manager, monkeypatch):
    monkeypatch.setattr(config, "MAX_VIDEO_DURATION_SECONDS", 0)
    _FakeYoutubeDL.duration = 999999
    job_id = manager.create_job(
        "https://youtube.com/watch?v=abc", DownloadFormat.VIDEO, Quality.BEST
    )
    job = manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED


def test_get_job_unknown_returns_none(manager):
    assert manager.get_job("does-not-exist") is None


def test_get_file_path_none_when_job_unknown(manager):
    assert manager.get_file_path("does-not-exist") is None


def test_get_file_path_none_when_not_completed(manager, monkeypatch):
    monkeypatch.setattr("src.downloader.yt_dlp.YoutubeDL", _FakeYoutubeDL)
    job_id = "pending-job"
    from src.models import JobInfo

    manager._jobs[job_id] = JobInfo(
        job_id=job_id,
        url="https://x",
        format=DownloadFormat.VIDEO,
        quality=Quality.BEST,
        status=JobStatus.DOWNLOADING,
    )
    assert manager.get_file_path(job_id) is None


def test_resolve_downloaded_file_raises_when_missing(manager):
    with pytest.raises(FileNotFoundError):
        manager._resolve_downloaded_file("no-such-job")


def test_shutdown_delegates_to_executor():
    calls = []

    class _TrackingExecutor(_SyncExecutor):
        def shutdown(self, wait=True):
            calls.append(wait)

    manager = JobManager(executor=_TrackingExecutor())
    manager.shutdown()
    assert calls == [False]
