"""
config.py
=========

Central configuration for the Video Downloader Service.

Loads environment variables (via .env, see .env.example), defines
project paths, and holds the yt-dlp format selectors and resource
limits used across the app.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# Project Paths
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
STATIC_DIR = SRC_DIR / "static"
DOWNLOAD_DIR = ROOT_DIR / "downloads"
LOG_DIR = ROOT_DIR / "logs"
TEST_DIR = ROOT_DIR / "tests"


# =============================================================================
# App Metadata / Server
# =============================================================================

APP_TITLE = "Video Downloader Service"
APP_VERSION = "0.1.0"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# =============================================================================
# Download Behaviour
# =============================================================================

# How many downloads yt-dlp will run at the same time. Each one is a
# real network + (for video) ffmpeg-merge workload, so this bounds
# both bandwidth and CPU use rather than letting every submitted job
# start immediately.
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))

# Hard cap on source video duration, in seconds. Checked against the
# video's own metadata before the real download starts (see
# downloader._run_job) so an oversized request fails fast instead of
# filling disk with a multi-hour file. 0 disables the check entirely.
MAX_VIDEO_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", "21600"))  # 6 hours

# yt-dlp format selectors per requested quality cap. mp4/m4a streams
# are preferred so ffmpeg can mux the pair without re-encoding; each
# falls back to the best available match (then plain "best") when a
# video doesn't offer that exact combination.
QUALITY_FORMAT_MAP = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p": (
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]"
        "/best[height<=1080][ext=mp4]/best[height<=1080]"
    ),
    "720p": (
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]"
        "/best[height<=720][ext=mp4]/best[height<=720]"
    ),
    "480p": (
        "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]"
        "/best[height<=480][ext=mp4]/best[height<=480]"
    ),
}

AUDIO_CODEC = "mp3"
AUDIO_QUALITY = "192"


# =============================================================================
# Create Required Directories
# =============================================================================

for directory in (DOWNLOAD_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)
