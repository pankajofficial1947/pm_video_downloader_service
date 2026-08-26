"""
app.py
======

FastAPI application: REST API + static web UI for the Video Downloader
Service.
"""

from contextlib import asynccontextmanager

import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src import config
from src.downloader import fetch_info, job_manager
from src.models import DownloadRequest, JobInfo, JobStatus, UrlRequest, VideoInfo


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    job_manager.shutdown()


app = FastAPI(title=config.APP_TITLE, version=config.APP_VERSION, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(config.STATIC_DIR / "index.html"))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/info", response_model=VideoInfo)
def get_info(payload: UrlRequest) -> dict:
    try:
        return fetch_info(str(payload.url))
    except yt_dlp.utils.DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/download")
def start_download(payload: DownloadRequest) -> dict:
    job_id = job_manager.create_job(str(payload.url), payload.format, payload.quality)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}", response_model=JobInfo)
def job_status(job_id: str) -> JobInfo:
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/file")
def job_file(job_id: str) -> FileResponse:
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409, detail=f"Job is {job.status.value}, not ready for download"
        )
    path = job_manager.get_file_path(job_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Downloaded file not found")
    return FileResponse(path, filename=path.name)
