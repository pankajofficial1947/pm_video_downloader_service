"""
config.py
=========

Central configuration for the Video Downloader Service (Streamlit app).

Holds project paths, the yt-dlp format/quality maps, and resource
limits.
"""

from pathlib import Path

import imageio_ffmpeg


# =============================================================================
# Project Paths
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"


# =============================================================================
# App Metadata
# =============================================================================

APP_TITLE = "Video Downloader Service"
APP_ICON = "🎬"


# =============================================================================
# ffmpeg
# =============================================================================

# yt-dlp needs ffmpeg to merge separate video/audio streams and to
# extract audio-only downloads. imageio-ffmpeg ships a static ffmpeg
# binary as a plain pip dependency (no Homebrew/apt install, no admin
# rights needed) and works identically on a local machine and on
# Streamlit Community Cloud's container - so yt-dlp is always pointed
# at this binary explicitly rather than relying on a system install.
FFMPEG_LOCATION = imageio_ffmpeg.get_ffmpeg_exe()


# =============================================================================
# Download Behaviour
# =============================================================================

# Hard cap on source video duration, in seconds. Checked against the
# video's own metadata before the real download starts (see
# downloader.download()) so an oversized request fails fast instead of
# running for hours on shared hosting. 0 disables the check.
MAX_VIDEO_DURATION_SECONDS = 21600  # 6 hours

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
