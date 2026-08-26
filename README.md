# video_downloader_service
# 🎬 Video Downloader Service

A self-hosted FastAPI service (plus a small built-in web UI) that downloads videos or audio from YouTube and hundreds of other sites, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp). Paste a URL, pick a format/quality, and track progress until the file is ready to save.

---

# Table of Contents

* [Overview](#overview)
* [Legal Notice](#legal-notice)
* [Features](#features)
* [Technology Stack](#technology-stack)
* [Project Structure](#project-structure)
* [Getting Started](#getting-started)
* [Configuration](#configuration)
* [Running the Application](#running-the-application)
* [API Reference](#api-reference)
* [Docker](#docker)
* [Testing](#testing)
* [Security](#security)
* [Future Enhancements](#future-enhancements)
* [License](#license)

---

# Overview

This service wraps `yt-dlp` behind a small REST API and web UI so you can submit a video URL, optionally preview its title/thumbnail/duration first, choose a video quality cap (or audio-only extraction), and download it - as a background job you can poll for progress rather than a blocking request.

It supports every site `yt-dlp` supports (YouTube plus [~1800 others](https://github.com/yt-dlp/yt-dlp/blob/master/supported_sites.md)) since it uses `yt-dlp`'s own extractors directly, rather than reimplementing per-site scraping.

---

# Legal Notice

Only download videos you own, that are in the public domain, or that you are otherwise authorized to save a copy of (e.g. a platform's own "download" feature, Creative Commons content, your own uploads). Downloading copyrighted content without permission can violate a platform's Terms of Service and/or copyright law in your jurisdiction - that responsibility is the operator's/user's, not something this codebase checks for or grants permission for. See [LICENSE](LICENSE)'s "Usage responsibility" section.

---

# Features

* **Any yt-dlp-supported site** - not hardcoded to YouTube.
* **Video or audio-only** - video downloads mux to `.mp4`; audio downloads extract to `.mp3` via ffmpeg.
* **Quality caps** - Best / 1080p / 720p / 480p, each with a sane fallback chain if a video doesn't offer that exact combination.
* **Metadata preview** - fetch title/thumbnail/duration/uploader before committing to a download.
* **Background jobs with live progress** - downloads run on a background thread pool; the UI polls job status once a second and shows a progress bar.
* **Duration guard** - rejects videos longer than `MAX_VIDEO_DURATION_SECONDS` (default 6 hours) before downloading, so one oversized request can't fill the disk unbounded.
* **No playlists by accident** - `noplaylist` is always on, so a channel/playlist URL downloads just the one linked video.
* **Docker-ready** - a `Dockerfile`/`docker-compose.yml` bundle ffmpeg, so there's no separate host-level install step when run this way.

---

# Technology Stack

* **Backend**: Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
* **Download engine**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) + system [ffmpeg](https://ffmpeg.org/) (stream muxing / audio extraction)
* **Frontend**: plain HTML/CSS/JS (no build step) served as static files by FastAPI
* **Testing**: pytest, pytest-cov, FastAPI's `TestClient` (httpx)

---

# Project Structure

```
video_downloader_service/
├── src/
│   ├── app.py            # FastAPI routes + static file mounting
│   ├── config.py         # Env vars, paths, format/quality maps
│   ├── downloader.py     # yt-dlp wrapper + background JobManager
│   ├── models.py         # Pydantic request/response schemas
│   └── static/           # index.html / app.js / style.css (web UI)
├── tests/
│   ├── conftest.py
│   ├── test_downloader.py
│   └── test_app.py
├── downloads/             # Downloaded files land here (gitignored)
├── logs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── setup.sh
└── pytest.ini
```

---

# Getting Started

## 1. Requirements

* Python 3.10+
* **ffmpeg** on `PATH` - required by yt-dlp to merge separate video/audio streams and to extract audio-only downloads. `setup.sh` checks for it and prints install instructions if missing (or use [Docker](#docker), which bundles it).

## 2. Clone the repository

```bash
git clone https://github.com/pankajofficial1947/video_downloader_service.git
cd video_downloader_service
```

## 3. Run the setup script

```bash
chmod +x setup.sh
./setup.sh
```

This creates a virtual environment (`.venv/`), installs `requirements.txt`, creates the `downloads/`/`logs/` folders, copies `.env.example` to `.env` if missing, and checks for ffmpeg.

## 4. Launch the app

```bash
source .venv/bin/activate
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** - paste a video URL, pick format/quality, and download.

---

# Configuration

All settings are read from environment variables (see `.env.example`), loaded via `python-dotenv`:

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Interface uvicorn binds to |
| `PORT` | `8000` | Port uvicorn binds to |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MAX_CONCURRENT_DOWNLOADS` | `2` | Thread pool size for background downloads |
| `MAX_VIDEO_DURATION_SECONDS` | `21600` (6h) | Reject videos longer than this before downloading; `0` disables the check |

---

# Running the Application

```bash
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

`--reload` is for local development only - drop it in production (see [Docker](#docker) for a production-style run).

---

# API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/api/health` | Liveness check |
| `POST` | `/api/info` | Fetch metadata for a URL without downloading |
| `POST` | `/api/download` | Start a download job, returns a `job_id` |
| `GET` | `/api/jobs/{job_id}` | Poll job status/progress |
| `GET` | `/api/jobs/{job_id}/file` | Download the finished file (404 until `status == "completed"`) |

### Fetch metadata

```bash
curl -X POST http://localhost:8000/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Start a download

`format` is `"video"` (default) or `"audio"`. `quality` is `"best"` (default), `"1080p"`, `"720p"`, or `"480p"` (ignored for audio).

```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "video", "quality": "720p"}'
# => {"job_id": "…"}
```

### Poll status, then fetch the file

```bash
curl http://localhost:8000/api/jobs/<job_id>
curl -OJ http://localhost:8000/api/jobs/<job_id>/file
```

`status` is one of `pending`, `downloading`, `completed`, `failed`.

---

# Docker

Bundles ffmpeg, so there's no host-level dependency to install:

```bash
docker compose up --build
```

Then open **http://localhost:8000**. Downloaded files land in `./downloads` on the host (bind-mounted into the container). Configure via the `environment:` block in `docker-compose.yml`.

---

# Testing

```bash
source .venv/bin/activate
pytest
```

`yt_dlp.YoutubeDL` is mocked in `tests/test_downloader.py` (a fake standing in for it writes a placeholder file and simulates progress hooks) - the test suite never makes a real network request or requires ffmpeg to be installed. Coverage reports via `pytest-cov` (`pytest.ini`).

---

# Security

* **No authentication** - this service is meant to run locally or on a trusted network. If you expose it beyond `localhost`, put it behind your own auth (reverse proxy with basic auth, VPN, etc.) - anyone who can reach it can submit downloads.
* **SSRF-adjacent risk**: `yt-dlp`'s generic extractor will attempt to fetch whatever URL it's given, including internal/private addresses, if no site-specific extractor claims it first. Don't expose this service to untrusted users on a network where that matters (e.g. one with a cloud metadata endpoint or internal-only services reachable from the host).
* **Resource limits**: `MAX_CONCURRENT_DOWNLOADS` bounds parallel bandwidth/CPU use; `MAX_VIDEO_DURATION_SECONDS` bounds how large a single download can get. Neither is a hard disk-space quota - monitor `downloads/` if running long-term.

---

# Future Enhancements

* Persistent job store (SQLite) instead of in-memory, so jobs survive a restart
* WebSocket-based progress instead of 1s polling
* Optional playlist support (currently always disabled)
* Automatic cleanup of old files in `downloads/`
* Simple API key / auth middleware for non-local deployments

---

# License

See [LICENSE](LICENSE). Third-party dependencies (yt-dlp, FastAPI, Uvicorn, Pydantic, ffmpeg) are governed by their own licenses, listed there.
