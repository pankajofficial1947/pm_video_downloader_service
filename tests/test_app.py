import yt_dlp
from fastapi.testclient import TestClient

from src.app import app
from src.models import DownloadFormat, JobInfo, JobStatus, Quality

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_serves_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_info_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        "src.app.fetch_info",
        lambda url: {
            "title": "T",
            "duration": 5,
            "thumbnail": None,
            "uploader": "U",
            "webpage_url": url,
            "extractor": "youtube",
        },
    )
    resp = client.post("/api/info", json={"url": "https://youtube.com/watch?v=x"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "T"


def test_info_endpoint_invalid_url_rejected_before_fetch():
    resp = client.post("/api/info", json={"url": "not-a-url"})
    assert resp.status_code == 422


def test_info_endpoint_download_error_returns_400(monkeypatch):
    def boom(url):
        raise yt_dlp.utils.DownloadError("bad url")

    monkeypatch.setattr("src.app.fetch_info", boom)
    resp = client.post("/api/info", json={"url": "https://youtube.com/watch?v=x"})
    assert resp.status_code == 400


def test_download_endpoint_creates_job(monkeypatch):
    captured = {}

    def fake_create_job(url, fmt, quality):
        captured["args"] = (url, fmt, quality)
        return "fixed-job-id"

    monkeypatch.setattr("src.app.job_manager.create_job", fake_create_job)
    resp = client.post(
        "/api/download",
        json={"url": "https://youtube.com/watch?v=x", "format": "audio", "quality": "720p"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"job_id": "fixed-job-id"}
    assert captured["args"] == (
        "https://youtube.com/watch?v=x",
        DownloadFormat.AUDIO,
        Quality.Q720,
    )


def test_job_status_not_found():
    resp = client.get("/api/jobs/unknown")
    assert resp.status_code == 404


def test_job_status_found(monkeypatch):
    fake_job = JobInfo(
        job_id="abc",
        url="https://x",
        format=DownloadFormat.VIDEO,
        quality=Quality.BEST,
        status=JobStatus.DOWNLOADING,
        progress=50.0,
    )
    monkeypatch.setattr("src.app.job_manager.get_job", lambda job_id: fake_job)
    resp = client.get("/api/jobs/abc")
    assert resp.status_code == 200
    assert resp.json()["progress"] == 50.0


def test_job_file_job_not_found():
    resp = client.get("/api/jobs/unknown/file")
    assert resp.status_code == 404


def test_job_file_not_ready_returns_409(monkeypatch):
    fake_job = JobInfo(
        job_id="abc",
        url="https://x",
        format=DownloadFormat.VIDEO,
        quality=Quality.BEST,
        status=JobStatus.DOWNLOADING,
        progress=10.0,
    )
    monkeypatch.setattr("src.app.job_manager.get_job", lambda job_id: fake_job)
    resp = client.get("/api/jobs/abc/file")
    assert resp.status_code == 409


def test_job_file_missing_on_disk_returns_404(monkeypatch):
    fake_job = JobInfo(
        job_id="abc",
        url="https://x",
        format=DownloadFormat.VIDEO,
        quality=Quality.BEST,
        status=JobStatus.COMPLETED,
        progress=100.0,
        filename="abc.mp4",
    )
    monkeypatch.setattr("src.app.job_manager.get_job", lambda job_id: fake_job)
    monkeypatch.setattr("src.app.job_manager.get_file_path", lambda job_id: None)
    resp = client.get("/api/jobs/abc/file")
    assert resp.status_code == 404


def test_job_file_completed_serves_file(monkeypatch, isolated_download_dir):
    media_file = isolated_download_dir / "abc.mp4"
    media_file.write_bytes(b"data")
    fake_job = JobInfo(
        job_id="abc",
        url="https://x",
        format=DownloadFormat.VIDEO,
        quality=Quality.BEST,
        status=JobStatus.COMPLETED,
        progress=100.0,
        filename="abc.mp4",
    )
    monkeypatch.setattr("src.app.job_manager.get_job", lambda job_id: fake_job)
    resp = client.get("/api/jobs/abc/file")
    assert resp.status_code == 200
    assert resp.content == b"data"
