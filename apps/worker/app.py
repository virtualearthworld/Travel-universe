"""Video ingest worker: validate, extract, and persist reconstruction inputs.

The GPU Gaussian-Splat trainer is an optional deployment component. This task
never marks a video as a published 3D world unless a real .spz artifact exists.
"""
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
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
        client = storage()
        client.download_file(BUCKET, source_object_key, str(source))
        self.update_state(state="STARTED", meta={"stage": "validating_video", "percent": 15})
        probe = shutil.which("ffprobe")
        ffmpeg = shutil.which("ffmpeg")
        if not probe or not ffmpeg:
            raise RuntimeError("ffmpeg and ffprobe must be installed in the worker image.")
        checked = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(source)],
            capture_output=True, text=True, check=True, timeout=60,
        )
        metadata = json.loads(checked.stdout)
        duration = float(metadata.get("format", {}).get("duration", 0))
        if duration <= 0 or duration > 600:
            raise ValueError("Video duration must be between 1 second and 10 minutes.")
        video_stream = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), None)
        if not video_stream:
            raise ValueError("The uploaded file does not contain a video stream.")
        self.update_state(state="STARTED", meta={"stage": "extracting_frames", "percent": 35})
        frames = root / "frames"
        frames.mkdir()
        subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(source), "-map", "0:v:0", "-vf", "fps=2,scale='min(1600,iw)':-2", "-q:v", "2", str(frames / "frame-%06d.jpg")],
            capture_output=True, text=True, check=True, timeout=600,
        )
        frame_count = len(list(frames.glob("*.jpg")))
        if frame_count < 2:
            raise RuntimeError("Not enough frames could be extracted from this video.")
        manifest = {
            "video_id": video_id,
            "duration_seconds": round(duration, 2),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "frame_count": frame_count,
            "sampling_fps": 2,
            "status": "frames_extracted_gpu_stage_required",
        }
        (root / "metadata.json").write_text(json.dumps(manifest, indent=2))
        self.update_state(state="STARTED", meta={"stage": "saving_reconstruction_inputs", "percent": 70})
        archive = root / "reconstruction-inputs.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(root / "metadata.json", "metadata.json")
            for frame in sorted(frames.glob("*.jpg")):
                bundle.write(frame, f"frames/{frame.name}")
        output_key = f"reconstruction-inputs/{video_id}/inputs.zip"
        client.upload_file(str(archive), BUCKET, output_key, ExtraArgs={"ContentType": "application/zip"})
        self.update_state(state="STARTED", meta={"stage": "awaiting_gpu_reconstruction", "percent": 85})
        return {
            "video_id": video_id,
            "status": manifest["status"],
            "duration_seconds": str(manifest["duration_seconds"]),
            "frame_count": str(frame_count),
            "width": str(video_stream.get("width", "")),
            "height": str(video_stream.get("height", "")),
            "reconstruction_inputs_key": output_key,
            "next_step": "Connect a CUDA Gaussian-Splat trainer and .spz exporter to turn these inputs into an explorable world.",
        }
