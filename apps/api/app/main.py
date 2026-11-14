import os
import uuid
from typing import Any
import boto3
from botocore.exceptions import ClientError
from celery import Celery
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

API_VERSION = "0.2.0"
MAX_VIDEO_BYTES = 500 * 1024 * 1024
ALLOWED_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}
BUCKET = os.getenv("S3_BUCKET", "travel-universe-media")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = FastAPI(title="Travel Universe API", version=API_VERSION, description="Travel content, reconstruction jobs, and social discovery API.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)
celery = Celery("travel_universe_api", broker=REDIS_URL, backend=REDIS_URL)

def storage_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "local_minio_change_me"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )

def ensure_bucket(client: Any) -> None:
    try:
        client.head_bucket(Bucket=BUCKET)
    except ClientError:
        try:
            client.create_bucket(Bucket=BUCKET)
        except ClientError as exc:
            # A concurrent first upload may have created it already.
            try:
                client.head_bucket(Bucket=BUCKET)
            except ClientError:
                raise HTTPException(status_code=503, detail="Media storage is unavailable.") from exc

@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "travel-universe-api"}

@app.get("/api/v1", tags=["meta"])
async def api_root() -> dict[str, str]:
    return {"name": "Travel Universe API", "version": API_VERSION}

@app.post("/api/v1/videos/upload", status_code=202, tags=["videos"])
async def upload_video(file: UploadFile = File(...)) -> dict[str, str]:
    filename = (file.filename or "").strip()
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload an MP4, MOV, or WebM video.")
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size <= 0:
        raise HTTPException(status_code=400, detail="The selected video is empty.")
    if size > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="Video exceeds the 500 MB upload limit.")
    video_id = str(uuid.uuid4())
    object_key = f"uploads/{video_id}{extension}"
    client = storage_client()
    ensure_bucket(client)
    try:
        client.upload_fileobj(file.file, BUCKET, object_key, ExtraArgs={"ContentType": file.content_type})
    except ClientError as exc:
        raise HTTPException(status_code=503, detail="Could not store the video. Please retry.") from exc
    task = celery.send_task(
        "reconstruction.process_video",
        kwargs={"video_id": video_id, "source_object_key": object_key, "original_filename": filename},
    )
    return {"video_id": video_id, "job_id": task.id, "status": "queued", "message": "Video uploaded and queued for processing."}

@app.get("/api/v1/jobs/{job_id}", tags=["reconstruction"])
async def get_job(job_id: str) -> dict[str, Any]:
    result = celery.AsyncResult(job_id)
    payload: dict[str, Any] = {"job_id": job_id, "status": result.state.lower()}
    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = "Processing failed. Check the worker logs and retry the upload."
    elif isinstance(result.info, dict):
        payload["progress"] = result.info
    return payload
