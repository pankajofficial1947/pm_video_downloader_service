from pathlib import Path

from streamlit.testing.v1 import AppTest

import config
from models import DownloadResult

APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")


def _new_app() -> AppTest:
    return AppTest.from_file(APP_PATH)


def test_renders_title():
    at = _new_app()
    at.run()
    assert not at.exception
    assert any(config.APP_TITLE in t.value for t in at.title)


def test_buttons_are_never_disabled():
    # Regression test: buttons used to be disabled=not url, which relies
    # on a text_input rerun (Enter/blur) happening before the button is
    # clicked. Clicking a button that was still disabled at click-time
    # doesn't register, so pasting a URL and immediately clicking looked
    # like the button was "stuck" disabled. Buttons must stay clickable;
    # an empty URL is handled as a warning after the click instead.
    at = _new_app()
    at.run()
    assert at.button(key="info_button").disabled is False
    assert at.button(key="download_button").disabled is False


def test_get_info_click_with_empty_url_shows_warning():
    at = _new_app()
    at.run()
    at.button(key="info_button").click().run()
    assert not at.exception
    assert any("Enter a video URL" in w.value for w in at.warning)


def test_download_click_with_empty_url_shows_warning():
    at = _new_app()
    at.run()
    at.button(key="download_button").click().run()
    assert not at.exception
    assert any("Enter a video URL" in w.value for w in at.warning)


def test_get_info_renders_video_metadata(monkeypatch):
    monkeypatch.setattr(
        "downloader.fetch_info",
        lambda url: {
            "title": "Cool Video",
            "duration": 65,
            "thumbnail": None,
            "uploader": "Someone",
            "webpage_url": url,
            "extractor": "youtube",
        },
    )
    at = _new_app()
    at.run()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="info_button").click().run()
    assert not at.exception
    assert any("Cool Video" in h.value for h in at.subheader)


def test_get_info_shows_error_on_failure(monkeypatch):
    def boom(url):
        raise ValueError("nope")

    monkeypatch.setattr("downloader.fetch_info", boom)
    at = _new_app()
    at.run()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="info_button").click().run()
    assert any("nope" in e.value for e in at.error)


def test_download_flow_offers_download_button(monkeypatch):
    monkeypatch.setattr(
        "downloader.download",
        lambda url, fmt, quality, progress_callback=None: DownloadResult(
            title="Cool Video", filename="abc.mp4", data=b"data"
        ),
    )
    at = _new_app()
    at.run()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="download_button").click().run()
    assert not at.exception
    assert any("Ready: Cool Video" in s.value for s in at.success)
    assert len(at.download_button) == 1


def test_download_flow_shows_error_on_failure(monkeypatch):
    def boom(url, fmt, quality, progress_callback=None):
        raise ValueError("duration too long")

    monkeypatch.setattr("downloader.download", boom)
    at = _new_app()
    at.run()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="download_button").click().run()
    assert any("duration too long" in e.value for e in at.error)
