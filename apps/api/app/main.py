import os
import uuid
from typing import Any
import boto3
from botocore.exceptions import ClientError
from celery import Celery
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

API_VERSION = "0.4.0"
MAX_VIDEO_BYTES = 500 * 1024 * 1024
ALLOWED_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}
BUCKET = os.getenv("S3_BUCKET", "travel-universe-media")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DEFAULT_CORS_ORIGINS = "http://localhost:3000,https://virtualearthworld.github.io"
CORS_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",") if origin.strip()]

app = FastAPI(title="Travel Universe API", version=API_VERSION, description="Travel content, reconstruction jobs, and social discovery API.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
    """Create the bucket only when it is genuinely missing; surface auth/outage errors."""
    try:
        client.head_bucket(Bucket=BUCKET)
        return
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code not in {"404", "NoSuchBucket", "NotFound"} and status != 404:
            raise HTTPException(status_code=503, detail="Media storage is unavailable.") from exc

    try:
        client.create_bucket(Bucket=BUCKET)
    except ClientError as exc:
        try:
            client.head_bucket(Bucket=BUCKET)
            return
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

    try:
        task = celery.send_task(
            "reconstruction.process_video",
            kwargs={"video_id": video_id, "source_object_key": object_key, "original_filename": filename},
        )
    except Exception as exc:
        try:
            client.delete_object(Bucket=BUCKET, Key=object_key)
        except ClientError:
            pass
        raise HTTPException(status_code=503, detail="The processing queue is unavailable. Please retry later.") from exc
    return {"video_id": video_id, "job_id": task.id, "status": "queued", "message": "Video uploaded and queued for processing."}


@app.get("/api/v1/jobs/{job_id}", tags=["reconstruction"])
async def get_job(job_id: str) -> dict[str, Any]:
    result = celery.AsyncResult(job_id)
    payload: dict[str, Any] = {"job_id": job_id, "status": result.state.lower()}
    if result.successful():
        outcome = result.result if isinstance(result.result, dict) else {}
        payload["result"] = outcome
        payload["world_ready"] = bool(outcome.get("world_asset_key")) and outcome.get("status") == "world_ready"
    elif result.failed():
        payload["error"] = "Processing failed. Check the worker logs and retry the upload."
        payload["world_ready"] = False
    elif isinstance(result.info, dict):
        payload["progress"] = result.info
        payload["world_ready"] = False
    else:
        payload["world_ready"] = False
    return payload


@app.get("/api/v1/worlds/{video_id}/asset", tags=["worlds"])
async def get_world_asset(video_id: str) -> dict[str, str]:
    """Return a short-lived URL only when the reconstructed SPZ object exists."""
    if not video_id or len(video_id) > 64 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in video_id):
        raise HTTPException(status_code=400, detail="Invalid video ID.")
    client = storage_client()
    object_key = f"worlds/{video_id}/scene.spz"
    try:
        client.head_object(Bucket=BUCKET, Key=object_key)
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": object_key},
            ExpiresIn=900,
        )
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in {"404", "NoSuchKey", "NotFound"} or status == 404:
            raise HTTPException(status_code=404, detail="This destination has not been reconstructed yet.") from exc
        raise HTTPException(status_code=503, detail="World storage is temporarily unavailable.") from exc
    return {"video_id": video_id, "asset_url": url, "format": "spz", "expires_in": 900}
