"""Video ingest worker. GPU reconstruction is an explicit optional stage.

The worker validates the source and extracts calibrated input frames. A production
Gaussian-Splat training runner must be installed and configured separately; this
task never labels a video as a completed 3D world unless a real .spz artifact exists.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import boto3
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
BUCKET = os.getenv("S3_BUCKET", "travel-universe-media")
celery_app = Celery("travel_universe_worker", broker=REDIS_URL, backend=REDIS_URL)

def storage():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "local_minio_change_me"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )

@celery_app.task(name="reconstruction.healthcheck")
def healthcheck() -> str:
    return "worker-ready"

@celery_app.task(bind=True, name="reconstruction.process_video")
def process_video(self, video_id: str, source_object_key: str, original_filename: str = "upload.mp4") -> dict[str, str]:
    self.update_state(state="STARTED", meta={"stage": "downloading", "percent": 5})
    with tempfile.TemporaryDirectory(prefix=f"tu-{video_id}-") as tmp:
        root = Path(tmp)
        source = root / Path(original_filename).name
        storage().download_file(BUCKET, source_object_key, str(source))
        self.update_state(state="STARTED", meta={"stage": "validating_video", "percent": 15})
        probe = shutil.which("ffprobe")
        if not probe:
            raise RuntimeError("ffprobe is missing from the worker image.")
        checked = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(source)],
            capture_output=True, text=True, check=True, timeout=60,
        )
        import json
        metadata = json.loads(checked.stdout)
        duration = float(metadata.get("format", {}).get("duration", 0))
        if duration <= 0 or duration > 600:
            raise ValueError("Video duration must be between 1 second and 10 minutes.")
        self.update_state(state="STARTED", meta={"stage": "extracting_frames", "percent": 35})
        frames = root / "frames"
        frames.mkdir()
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source), "-vf", "fps=2,scale='min(1600,iw)':-2", "-q:v", "2", str(frames / "frame-%06d.jpg")],
            capture_output=True, text=True, check=True, timeout=600,
        )
        frame_count = len(list(frames.glob("*.jpg")))
        if frame_count < 2:
            raise RuntimeError("Not enough frames could be extracted from this video.")
        self.update_state(state="STARTED", meta={"stage": "awaiting_gpu_reconstruction", "percent": 45})
        # Do not fake a 3D result: this deployment needs a CUDA-enabled Gaussian
        # Splatting trainer and .spz packager before the world can be published.
        return {
            "video_id": video_id,
            "status": "frames_extracted_gpu_stage_required",
            "duration_seconds": str(round(duration, 2)),
            "frame_count": str(frame_count),
            "next_step": "Configure a CUDA Gaussian-Splatting trainer and .spz exporter to publish an explorable world.",
        }
