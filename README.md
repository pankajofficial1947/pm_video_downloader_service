# pm_video_downloader_service
# 🎬 Video Downloader Service

A [Streamlit](https://streamlit.io/) app that downloads videos or audio from YouTube and hundreds of other sites, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp). Paste a URL, preview its title/thumbnail, pick a format/quality, and save the file - runs locally or free on Streamlit Community Cloud so it's reachable from your phone too.

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
* [Deploying to Streamlit Community Cloud](#deploying-to-streamlit-community-cloud)
* [Known Limitations](#known-limitations)
* [Testing](#testing)
* [Security](#security)
* [Future Enhancements](#future-enhancements)
* [License](#license)

---

# Overview

Paste a video URL, optionally hit **Get Info** to preview its title/thumbnail/duration, then pick **Video (mp4)** with a quality cap or **Audio only (mp3)** and hit **Download**. The file downloads to a scratch temp directory, is read into memory, and offered back via a `st.download_button` - nothing is left sitting on disk, which matters on Streamlit Community Cloud's ephemeral filesystem.

It supports every site `yt-dlp` supports (YouTube plus [~1800 others](https://github.com/yt-dlp/yt-dlp/blob/master/supported_sites.md)) since it uses `yt-dlp`'s own extractors directly.

---

# Legal Notice

Only download videos you own, that are in the public domain, or that you are otherwise authorized to save a copy of. Downloading copyrighted content without permission can violate a platform's Terms of Service and/or copyright law in your jurisdiction - that responsibility is the operator's/user's, not something this codebase checks for or grants permission for. See [LICENSE](LICENSE)'s "Usage responsibility" section.

**Note:** this app has no access control (see [Security](#security)) - if deployed to Streamlit Community Cloud, anyone with the URL can use it. Keep the deployed link private if you don't want that.

---

# Features

* **Any yt-dlp-supported site** - not hardcoded to YouTube.
* **Video or audio-only** - video downloads mux to `.mp4`; audio downloads extract to `.mp3`.
* **Quality caps** - Best / 1080p / 720p / 480p, each with a sane fallback chain if a video doesn't offer that exact combination.
* **Metadata preview** - fetch title/thumbnail/duration/uploader before committing to a download.
* **Live progress bar** during download/merge.
* **Duration guard** - rejects videos longer than `MAX_VIDEO_DURATION_SECONDS` (default 6 hours), checked before downloading.
* **No playlists by accident** - `noplaylist` is always on, so a channel/playlist URL downloads just the one linked video.
* **No system ffmpeg install** - bundled via the `imageio-ffmpeg` pip package, so it works the same on your laptop and on Streamlit Community Cloud with no Homebrew/apt step.

---

# Technology Stack

* **App framework**: [Streamlit](https://streamlit.io/)
* **Download engine**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) (bundled static ffmpeg binary - stream muxing / audio extraction)
* **Testing**: pytest, pytest-cov, Streamlit's own [`AppTest`](https://docs.streamlit.io/develop/api-reference/app-testing) framework

---

# Project Structure

```
pm_video_downloader_service/
├── .streamlit/
│   └── config.toml       # Theme
├── src/
│   ├── app.py              # Streamlit entrypoint (UI)
│   ├── config.py            # Paths, ffmpeg location, format/quality maps
│   ├── downloader.py         # yt-dlp wrapper: fetch_info() / download()
│   └── models.py              # DownloadFormat/Quality enums, DownloadResult
├── tests/
│   ├── test_downloader.py
│   └── test_app.py
├── requirements.txt
├── setup.sh
└── pytest.ini
```

---

# Getting Started

## 1. Requirements

* Python 3.10+
* That's it - `imageio-ffmpeg` provides ffmpeg as a plain pip dependency, no separate system install.

## 2. Clone the repository

```bash
git clone https://github.com/pankajofficial1947/pm_video_downloader_service.git
cd pm_video_downloader_service
```

## 3. Run the setup script

```bash
chmod +x setup.sh
./setup.sh
```

This creates a virtual environment (`.venv/`) and installs `requirements.txt`.

## 4. Launch the app

```bash
source .venv/bin/activate
streamlit run src/app.py
```

Open **http://localhost:8501** and go.

---

# Configuration

| Setting | Where | Description |
|---|---|---|
| `MAX_VIDEO_DURATION_SECONDS` | `src/config.py` | Reject videos longer than this before downloading; `0` disables the check. Default 21600 (6h). |
| `QUALITY_FORMAT_MAP` / `AUDIO_CODEC` / `AUDIO_QUALITY` | `src/config.py` | yt-dlp format selectors per quality option. |

---

# Running the Application

```bash
streamlit run src/app.py
```

Streamlit also prints a **Network URL** (e.g. `http://192.168.1.23:8501`) alongside the local one - open that from your phone on the same Wi-Fi to test without deploying anywhere.

---

# Deploying to Streamlit Community Cloud

This gets you a stable HTTPS URL reachable from any device, for free:

1. **Push this repo to GitHub** (Streamlit Community Cloud deploys from a GitHub repo):
   ```bash
   gh repo create pm_video_downloader_service --private --source=. --push
   ```
   (or create the repo on github.com and `git push` yourself).
2. Go to **[share.streamlit.io](https://share.streamlit.io)**, sign in, and click **New app**.
3. Pick this repo/branch and set the main file path to `src/app.py`.
4. Deploy. You'll get a `https://<something>.streamlit.app` URL - bookmark it on your phone.

No `packages.txt`/apt step is needed for ffmpeg - `imageio-ffmpeg` (in `requirements.txt`) handles that identically to your local machine.

**Remember:** there is no login on this app (see [Security](#security)) - that URL works for anyone who has it.

---

# Known Limitations

**YouTube downloads can fail on Streamlit Community Cloud specifically, with an error like "the source returned no video/audio data".** This happens because Streamlit Community Cloud runs on Google Cloud Platform, and YouTube's anti-bot system is known to block/throttle requests for actual video/audio bytes from datacenter IP ranges (AWS/GCP/Azure) even when metadata lookups (title, thumbnail, duration) succeed fine - a limitation of YouTube's own infrastructure, not a bug in this app. It's a widely reported issue across yt-dlp-based tools hosted this way, not specific to this codebase.

Mitigations already in place (`src/downloader.py`):
* Requests an alternate YouTube "player client" (`android`, falling back to `web`) - a commonly effective workaround, though not guaranteed as YouTube's countermeasures change over time.
* Retries fragment/network failures automatically.
* Surfaces a clear explanation instead of yt-dlp's raw internal error text when this happens.

If it still fails: try again (some blocking is intermittent), try a different video, or run the app locally (`streamlit run src/app.py`) - this issue does not occur on a normal home/residential IP.

---

# Testing

```bash
source .venv/bin/activate
pytest
```

* `tests/test_downloader.py` mocks `yt_dlp.YoutubeDL` directly - no real network requests, no ffmpeg required to run the suite.
* `tests/test_app.py` uses Streamlit's own `AppTest` framework to drive the actual `src/app.py` script headlessly (info preview, download flow), mocking `downloader.fetch_info`/`download`.

---

# Security

* **No access control** - anyone who has the deployed URL can use the app. Keep the link private, or put it behind your own access layer (e.g. a reverse proxy with auth, or Streamlit Cloud's private-app viewer allowlist) if that matters to you.
* **SSRF-adjacent risk**: `yt-dlp`'s generic extractor will attempt to fetch whatever URL it's given, including internal/private addresses, if no site-specific extractor claims it first. Worth keeping in mind if you ever do add access control and are relying on it for more than convenience.
* **Resource limits**: `MAX_VIDEO_DURATION_SECONDS` bounds how large a single download can get; there's no persistent disk quota to worry about since files are held in memory only for the duration of one download/serve cycle, not written to permanent storage.

---

# Future Enhancements

* Optional playlist support (currently always disabled)
* Optional access control (password or otherwise) for deployments where that matters
* Download history / re-download without re-entering a URL
* Simple rate limiting per session

---

# License

See [LICENSE](LICENSE). Third-party dependencies (yt-dlp, Streamlit, imageio-ffmpeg/ffmpeg) are governed by their own licenses, listed there.
