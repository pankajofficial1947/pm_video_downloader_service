import pytest

from src import config


@pytest.fixture(autouse=True)
def isolated_download_dir(tmp_path, monkeypatch):
    """Point config.DOWNLOAD_DIR at a scratch dir so tests never touch downloads/."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    monkeypatch.setattr(config, "DOWNLOAD_DIR", download_dir)
    yield download_dir
