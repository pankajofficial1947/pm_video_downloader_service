"""
downloader.py
==============

yt-dlp wrapper and background job manager.

fetch_info() does a metadata-only lookup (no download). JobManager runs
actual downloads on a thread pool (yt-dlp's own download() call is
blocking network + subprocess I/O) and tracks each one's progress/
result in memory, keyed by job id.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, Optional

import yt_dlp

from src import config
from src.models import DownloadFormat, JobInfo, JobStatus, Quality


def fetch_info(url: str) -> dict:
    """Look up a video's metadata without downloading it."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
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


def _build_ydl_opts(
    job_id: str, fmt: DownloadFormat, quality: Quality, hook: Callable[[dict], None]
) -> dict:
    outtmpl = str(config.DOWNLOAD_DIR / f"{job_id}.%(ext)s")
    opts: dict = {
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
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


class JobManager:
    """Tracks download jobs and runs them on a background thread pool."""

    def __init__(self, executor=None):
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()
        self._executor = executor or ThreadPoolExecutor(
            max_workers=config.MAX_CONCURRENT_DOWNLOADS
        )

    def create_job(self, url: str, fmt: DownloadFormat, quality: Quality) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = JobInfo(
                job_id=job_id,
                url=url,
                format=fmt,
                quality=quality,
                status=JobStatus.PENDING,
                progress=0.0,
            )
        self._executor.submit(self._run_job, job_id, url, fmt, quality)
        return job_id

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_file_path(self, job_id: str) -> Optional[Path]:
        job = self.get_job(job_id)
        if not job or job.status != JobStatus.COMPLETED or not job.filename:
            return None
        return config.DOWNLOAD_DIR / job.filename

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    def _update(self, job_id: str, **fields) -> None:
        with self._lock:
            current = self._jobs.get(job_id)
            if current is not None:
                self._jobs[job_id] = current.model_copy(update=fields)

    def _run_job(self, job_id: str, url: str, fmt: DownloadFormat, quality: Quality) -> None:
        self._update(job_id, status=JobStatus.DOWNLOADING)
        try:
            if config.MAX_VIDEO_DURATION_SECONDS:
                duration = fetch_info(url).get("duration")
                if duration and duration > config.MAX_VIDEO_DURATION_SECONDS:
                    raise ValueError(
                        f"Video duration ({duration:.0f}s) exceeds the configured "
                        f"limit ({config.MAX_VIDEO_DURATION_SECONDS}s)"
                    )

            def hook(d: dict) -> None:
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    progress = round(downloaded / total * 100, 1) if total else 0.0
                    self._update(job_id, progress=progress)
                elif d.get("status") == "finished":
                    self._update(job_id, progress=99.0)

            opts = _build_ydl_opts(job_id, fmt, quality, hook)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            filename = self._resolve_downloaded_file(job_id)
            self._update(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100.0,
                title=info.get("title") if info else None,
                filename=filename,
            )
        except Exception as exc:
            self._update(job_id, status=JobStatus.FAILED, error=str(exc))

    def _resolve_downloaded_file(self, job_id: str) -> str:
        candidates = [
            p
            for p in config.DOWNLOAD_DIR.glob(f"{job_id}.*")
            if p.suffix not in {".part", ".ytdl"}
        ]
        if not candidates:
            raise FileNotFoundError(f"No output file was produced for job {job_id}")
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        return newest.name


job_manager = JobManager()
