"""
downloader.py
==============

yt-dlp wrapper. fetch_info() does a metadata-only lookup; download()
runs a real download to a scratch directory and returns the result as
in-memory bytes, so the Streamlit UI can hand it straight to
st.download_button without relying on any persistent storage - useful
since Streamlit Community Cloud's filesystem is ephemeral.
"""

import tempfile
import uuid
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

import config
from models import DownloadFormat, DownloadResult, Quality

ProgressCallback = Callable[[float, str], None]

# Substrings seen in yt-dlp's own error text when a site (YouTube in
# particular) has blocked/throttled this server's IP: metadata
# extraction succeeds, but every request for actual video/audio bytes
# comes back empty or refused. Best-effort pattern match, not
# exhaustive - see download()'s docstring for the full explanation.
_LIKELY_BLOCKED_INDICATORS = (
    "downloaded file is empty",
    "sign in to confirm",
    "http error 403",
)


def fetch_info(url: str) -> dict:
    """Look up a video's metadata without downloading it."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "ffmpeg_location": config.FFMPEG_LOCATION,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return _simplify_info(info)


def _simplify_info(info: dict) -> dict:
    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url"),
        "extractor": info.get("extractor"),
    }


def download(
    url: str,
    fmt: DownloadFormat,
    quality: Quality,
    progress_callback: Optional[ProgressCallback] = None,
) -> DownloadResult:
    """Download a video/audio file and return it as in-memory bytes.

    Raises ValueError if the source exceeds MAX_VIDEO_DURATION_SECONDS.
    Raises RuntimeError with a clearer message when the failure looks
    like the source site blocking/throttling this server's IP (see
    _LIKELY_BLOCKED_INDICATORS) - common for YouTube specifically when
    running from a cloud platform's datacenter IP range, and not
    something this app can reliably work around. Otherwise re-raises
    whatever yt-dlp itself raised (yt_dlp.utils.DownloadError etc.).
    """
    # Both the duration pre-check below and yt-dlp's own extract_info()
    # call inside the real download can each take several real seconds
    # (a full metadata fetch, not just a HEAD request) before any byte
    # of the actual file has been requested - and progress_hooks only
    # fire once byte transfer starts. Without these early callbacks the
    # UI sits on its static initial text the whole time, indistinguishable
    # from being frozen.
    if progress_callback is not None:
        progress_callback(0.0, "preparing")

    if config.MAX_VIDEO_DURATION_SECONDS:
        duration = fetch_info(url).get("duration")
        if duration and duration > config.MAX_VIDEO_DURATION_SECONDS:
            raise ValueError(
                f"Video duration ({duration:.0f}s) exceeds the configured "
                f"limit ({config.MAX_VIDEO_DURATION_SECONDS}s)"
            )

    if progress_callback is not None:
        progress_callback(0.0, "connecting")

    job_id = uuid.uuid4().hex

    def hook(d: dict) -> None:
        if progress_callback is None:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            progress = round(downloaded / total * 100, 1) if total else 0.0
            progress_callback(progress, "downloading")
        elif d.get("status") == "finished":
            progress_callback(99.0, "processing")

    try:
        with tempfile.TemporaryDirectory(prefix="video_downloader_") as tmpdir:
            tmp_path = Path(tmpdir)
            opts = _build_ydl_opts(tmp_path, job_id, fmt, quality, hook)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            result_path = _resolve_downloaded_file(tmp_path, job_id)
            data = result_path.read_bytes()
    except Exception as exc:
        message = str(exc).lower()
        if any(indicator in message for indicator in _LIKELY_BLOCKED_INDICATORS):
            raise RuntimeError(
                "Download failed: the source returned no video/audio data. "
                "This usually means the site (YouTube in particular) is "
                "blocking or throttling requests from this server's IP "
                "address, rather than a problem with this app - a known "
                "limitation of running yt-dlp from a cloud platform. Try "
                "again shortly, try a different video, or run this app "
                "locally for more reliable downloads."
            ) from exc
        raise

    if progress_callback is not None:
        progress_callback(100.0, "completed")

    return DownloadResult(
        title=info.get("title") if info else None,
        filename=result_path.name,
        data=data,
    )


def _build_ydl_opts(
    download_dir: Path,
    job_id: str,
    fmt: DownloadFormat,
    quality: Quality,
    hook: Callable[[dict], None],
) -> dict:
    outtmpl = str(download_dir / f"{job_id}.%(ext)s")
    opts: dict = {
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "ffmpeg_location": config.FFMPEG_LOCATION,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_args": {"youtube": {"player_client": config.YOUTUBE_PLAYER_CLIENTS}},
    }
    if fmt == DownloadFormat.AUDIO:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": config.AUDIO_CODEC,
                "preferredquality": config.AUDIO_QUALITY,
            }
        ]
    else:
        opts["format"] = config.QUALITY_FORMAT_MAP.get(
            quality.value, config.QUALITY_FORMAT_MAP["best"]
        )
        opts["merge_output_format"] = "mp4"
    return opts


def _resolve_downloaded_file(download_dir: Path, job_id: str) -> Path:
    candidates = [
        p for p in download_dir.glob(f"{job_id}.*") if p.suffix not in {".part", ".ytdl"}
    ]
    if not candidates:
        raise FileNotFoundError(f"No output file was produced for job {job_id}")
    return max(candidates, key=lambda p: p.stat().st_mtime)
