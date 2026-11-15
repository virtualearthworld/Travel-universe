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
from celery import Celery, chain

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
        result = {
            "video_id": video_id,
            "status": manifest["status"],
            "duration_seconds": str(manifest["duration_seconds"]),
            "frame_count": str(frame_count),
            "width": str(video_stream.get("width", "")),
            "height": str(video_stream.get("height", "")),
            "reconstruction_inputs_key": output_key,
            "world_ready": False,
            "next_step": "Frames are prepared. Enable the reconstruction pipeline and configure COLMAP, CUDA, gsplat, and the SPZ exporter to build a 3D world.",
        }
        if os.getenv("ENABLE_RECONSTRUCTION_PIPELINE", "false").lower() in {"1", "true", "yes"}:
            self.update_state(state="STARTED", meta={"stage": "queueing_colmap_reconstruction", "percent": 90})
            workflow = chain(
                estimate_camera_poses.s(video_id, output_key),
                train_gaussian_splats.s().set(queue="gpu"),
            )
            return self.replace(workflow)
        return result


@celery_app.task(bind=True, name="reconstruction.estimate_camera_poses")
def estimate_camera_poses(
    self, video_id: str | dict[str, str], reconstruction_inputs_key: str | None = None
) -> dict[str, str]:
    """Run COLMAP on a previously extracted frame bundle and persist sparse output.

    A chained invocation receives the preprocessing result as its first argument.
    """
    if isinstance(video_id, dict):
        preprocessing = video_id
        video_id = preprocessing.get("video_id", "")
        reconstruction_inputs_key = preprocessing.get("reconstruction_inputs_key")
    if not video_id or not reconstruction_inputs_key:
        raise ValueError("COLMAP stage requires video_id and reconstruction_inputs_key.")
    from colmap_pipeline import ColmapError, run_colmap_sparse_reconstruction

    self.update_state(state="STARTED", meta={"stage": "colmap_feature_extraction", "percent": 10})
    with tempfile.TemporaryDirectory(prefix=f"tu-colmap-{video_id}-") as tmp:
        root = Path(tmp)
        input_zip = root / "inputs.zip"
        client = storage()
        client.download_file(BUCKET, reconstruction_inputs_key, str(input_zip))
        frames = root / "frames"
        frames.mkdir()
        with zipfile.ZipFile(input_zip) as bundle:
            for member in bundle.infolist():
                target = (root / member.filename).resolve()
                if root.resolve() not in target.parents and target != root.resolve():
                    raise ValueError("Unsafe path in reconstruction input archive.")
                if member.filename.startswith("frames/") and not member.is_dir():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(member) as source_file, target.open("wb") as target_file:
                        shutil.copyfileobj(source_file, target_file)
        extracted_frames = root / "frames"
        self.update_state(state="STARTED", meta={"stage": "colmap_pose_estimation", "percent": 35})
        try:
            result = run_colmap_sparse_reconstruction(extracted_frames, root / "colmap")
        except ColmapError as exc:
            raise RuntimeError(str(exc)) from exc
        result["video_id"] = video_id
        self.update_state(state="STARTED", meta={"stage": "saving_sparse_reconstruction", "percent": 80})
        output_zip = root / "colmap-sparse-model.zip"
        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((root / "colmap").rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(root / "colmap").as_posix())
        output_key = f"reconstruction/{video_id}/colmap-sparse-model.zip"
        client.upload_file(str(output_zip), BUCKET, output_key, ExtraArgs={"ContentType": "application/zip"})
        return {
            "video_id": video_id,
            "status": result["status"],
            "sparse_reconstruction_key": output_key,
            "reconstruction_inputs_key": reconstruction_inputs_key,
            "source_image_count": str(result["source_image_count"]),
            "world_ready": False,
            "next_step": "Train and validate a Gaussian Splat scene, then export a real .spz asset.",
        }


@celery_app.task(bind=True, name="reconstruction.train_gaussian_splats")
def train_gaussian_splats(
    self,
    video_id: str | dict[str, str],
    reconstruction_inputs_key: str | None = None,
    sparse_reconstruction_key: str | None = None,
) -> dict[str, str]:
    """Train and export a browser asset from existing frames and COLMAP output.

    A chained invocation receives the COLMAP result as its first argument.
    """
    if isinstance(video_id, dict):
        colmap_result = video_id
        video_id = colmap_result.get("video_id", "")
        reconstruction_inputs_key = colmap_result.get("reconstruction_inputs_key")
        sparse_reconstruction_key = colmap_result.get("sparse_reconstruction_key")
    if not video_id or not reconstruction_inputs_key or not sparse_reconstruction_key:
        raise ValueError("Gaussian Splat stage requires video_id, reconstruction_inputs_key, and sparse_reconstruction_key.")
    from gaussian_splat_pipeline import SplatPipelineError, run_gaussian_splat_pipeline

    self.update_state(state="STARTED", meta={"stage": "preparing_gsplat_inputs", "percent": 5})
    with tempfile.TemporaryDirectory(prefix=f"tu-gsplat-{video_id}-") as tmp:
        root = Path(tmp)
        client = storage()
        input_zip = root / "inputs.zip"
        sparse_zip = root / "sparse.zip"
        client.download_file(BUCKET, reconstruction_inputs_key, str(input_zip))
        client.download_file(BUCKET, sparse_reconstruction_key, str(sparse_zip))
        frames = root / "frames"
        sparse = root / "sparse"
        frames.mkdir()
        sparse.mkdir()
        for archive_path, destination, prefix in (
            (input_zip, frames, "frames/"),
            (sparse_zip, sparse, ""),
        ):
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.infolist():
                    relative = Path(member.filename)
                    if relative.is_absolute() or ".." in relative.parts:
                        raise ValueError("Unsafe path in reconstruction archive.")
                    if member.is_dir() or (prefix and not member.filename.startswith(prefix)):
                        continue
                    name = member.filename[len(prefix):] if prefix else member.filename
                    target = (destination / name).resolve()
                    if destination.resolve() not in target.parents:
                        raise ValueError("Unsafe path in reconstruction archive.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source_file, target.open("wb") as target_file:
                        shutil.copyfileobj(source_file, target_file)
        model_dirs = sorted(path for path in sparse.iterdir() if path.is_dir())
        if not model_dirs:
            raise RuntimeError("Sparse reconstruction archive contains no model directory.")
        model = model_dirs[0]
        self.update_state(state="STARTED", meta={"stage": "training_gaussian_splats", "percent": 20})
        try:
            result = run_gaussian_splat_pipeline(frames, model, root / "output")
        except SplatPipelineError as exc:
            raise RuntimeError(str(exc)) from exc
        self.update_state(state="STARTED", meta={"stage": "publishing_spz_asset", "percent": 90})
        asset_key = f"worlds/{video_id}/scene.spz"
        client.upload_file(
            result["world_asset_path"], BUCKET, asset_key,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )
        return {
            "video_id": video_id,
            "status": "world_ready",
            "world_asset_key": asset_key,
            "world_asset_format": "spz",
            "world_ready": "true",
        }
