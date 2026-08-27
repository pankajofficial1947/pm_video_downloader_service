from pathlib import Path

from streamlit.testing.v1 import AppTest

import config
from models import DownloadResult

APP_PATH = str(Path(__file__).resolve().parent.parent / "src" / "app.py")
PASSWORD = "secret123"


def _new_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.secrets[config.PASSWORD_SECRET_KEY] = PASSWORD
    return at


def _authenticated_app() -> AppTest:
    at = _new_app()
    at.run()
    at.text_input(key="password_input").input(PASSWORD).run()
    return at


def test_blocks_access_without_password():
    at = _new_app()
    at.run()
    assert not at.exception
    assert len(at.text_input) == 1
    assert at.text_input[0].label == "Password"
    assert not at.title


def test_rejects_wrong_password():
    at = _new_app()
    at.run()
    at.text_input(key="password_input").input("wrong").run()
    assert any("Incorrect password" in e.value for e in at.error)
    assert not at.title


def test_allows_correct_password_and_renders_app():
    at = _authenticated_app()
    assert not at.exception
    assert any(config.APP_TITLE in t.value for t in at.title)


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
    at = _authenticated_app()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="info_button").click().run()
    assert not at.exception
    assert any("Cool Video" in h.value for h in at.subheader)


def test_get_info_shows_error_on_failure(monkeypatch):
    def boom(url):
        raise ValueError("nope")

    monkeypatch.setattr("downloader.fetch_info", boom)
    at = _authenticated_app()
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
    at = _authenticated_app()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="download_button").click().run()
    assert not at.exception
    assert any("Ready: Cool Video" in s.value for s in at.success)
    assert len(at.download_button) == 1


def test_download_flow_shows_error_on_failure(monkeypatch):
    def boom(url, fmt, quality, progress_callback=None):
        raise ValueError("duration too long")

    monkeypatch.setattr("downloader.download", boom)
    at = _authenticated_app()
    at.text_input(key="url_input").input("https://youtube.com/watch?v=x").run()
    at.button(key="download_button").click().run()
    assert any("duration too long" in e.value for e in at.error)
