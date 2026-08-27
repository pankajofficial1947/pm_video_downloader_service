"""
app.py
======

Streamlit entrypoint for the Video Downloader Service.
"""

from typing import Optional

import streamlit as st

import config
from downloader import download, fetch_info
from models import DownloadFormat, Quality


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


st.set_page_config(page_title=config.APP_TITLE, page_icon=config.APP_ICON)

st.title(f"{config.APP_ICON} {config.APP_TITLE}")
st.caption(
    "Paste a video URL (YouTube and hundreds of other sites via "
    "[yt-dlp](https://github.com/yt-dlp/yt-dlp)). Only download content "
    "you own or are authorized to."
)

url = st.text_input(
    "Video URL", placeholder="https://www.youtube.com/watch?v=...", key="url_input"
)

col1, col2 = st.columns(2)
with col1:
    format_label = st.selectbox(
        "Format", ["Video (mp4)", "Audio only (mp3)"], key="format_select"
    )
with col2:
    quality_label = st.selectbox(
        "Quality",
        ["Best", "1080p", "720p", "480p"],
        disabled=format_label.startswith("Audio"),
        key="quality_select",
    )

selected_format = DownloadFormat.AUDIO if format_label.startswith("Audio") else DownloadFormat.VIDEO
selected_quality = (
    Quality.BEST if selected_format == DownloadFormat.AUDIO else Quality(quality_label.lower())
)

info_col, download_col = st.columns(2)
get_info_clicked = info_col.button(
    "Get Info", use_container_width=True, disabled=not url, key="info_button"
)
download_clicked = download_col.button(
    "Download",
    type="primary",
    use_container_width=True,
    disabled=not url,
    key="download_button",
)

if get_info_clicked:
    with st.spinner("Fetching info..."):
        try:
            info = fetch_info(url)
        except Exception as exc:
            st.error(str(exc))
            st.session_state.pop("last_info", None)
        else:
            st.session_state["last_info"] = info

if "last_info" in st.session_state:
    info = st.session_state["last_info"]
    thumb_col, meta_col = st.columns([1, 3])
    if info.get("thumbnail"):
        thumb_col.image(info["thumbnail"])
    with meta_col:
        st.subheader(info.get("title") or "Untitled")
        meta = " · ".join(
            part
            for part in [info.get("uploader"), format_duration(info.get("duration"))]
            if part
        )
        if meta:
            st.caption(meta)

if download_clicked:
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def on_progress(pct: float, status: str) -> None:
        progress_bar.progress(min(pct, 100.0) / 100.0)
        status_text.text(f"{status.capitalize()}... {pct:.0f}%")

    try:
        result = download(url, selected_format, selected_quality, progress_callback=on_progress)
    except Exception as exc:
        status_text.empty()
        progress_bar.empty()
        st.error(str(exc))
        st.session_state.pop("last_result", None)
    else:
        status_text.text("Done!")
        st.session_state["last_result"] = result

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    st.success(f"Ready: {result.title or result.filename}")
    st.download_button(
        "Save file",
        data=result.data,
        file_name=result.filename,
        use_container_width=True,
        key="save_file_button",
    )
