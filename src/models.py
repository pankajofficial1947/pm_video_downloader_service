"""
models.py
=========

Shared enums and small data types for the Video Downloader Service.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DownloadFormat(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class Quality(str, Enum):
    BEST = "best"
    Q1080 = "1080p"
    Q720 = "720p"
    Q480 = "480p"


@dataclass
class DownloadResult:
    title: Optional[str]
    filename: str
    data: bytes
