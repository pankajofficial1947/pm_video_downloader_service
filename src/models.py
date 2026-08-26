"""
models.py
=========

Pydantic request/response schemas for the Video Downloader Service API.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl


class DownloadFormat(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class Quality(str, Enum):
    BEST = "best"
    Q1080 = "1080p"
    Q720 = "720p"
    Q480 = "480p"


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class UrlRequest(BaseModel):
    url: HttpUrl


class DownloadRequest(BaseModel):
    url: HttpUrl
    format: DownloadFormat = DownloadFormat.VIDEO
    quality: Quality = Quality.BEST


class JobInfo(BaseModel):
    job_id: str
    url: str
    format: DownloadFormat
    quality: Quality
    status: JobStatus
    progress: float = 0.0
    title: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


class VideoInfo(BaseModel):
    title: Optional[str] = None
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    webpage_url: Optional[str] = None
    extractor: Optional[str] = None
