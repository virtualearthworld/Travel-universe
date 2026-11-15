# Video upload and reconstruction pipeline

## Current pipeline stages

1. **Upload:** the API accepts MP4, MOV, or WebM files up to 500 MB.
2. **Store:** the original video is saved to S3-compatible object storage.
3. **Queue:** a Celery job is submitted to Redis and a job ID is returned.
4. **Inspect:** the worker uses ffprobe to validate a video stream and a 1–600 second duration.
5. **Prepare:** FFmpeg samples frames at 2 frames per second and creates a metadata manifest.
6. **Package:** the frames and manifest are stored as `reconstruction-inputs/{video_id}/inputs.zip`.
7. **Reconstruct (not yet implemented):** camera pose estimation / structure-from-motion, Gaussian Splat training, optimization, and real `.spz` export.
8. **Publish (not yet implemented):** validate the generated scene and register a durable world asset for the browser viewer.

The API job response now exposes `world_ready`. It remains false for queued, running, failed, or preprocessing-only jobs. A job may be marked world-ready only when a future reconstruction worker returns `status: "world_ready"` and a non-empty `world_asset_key` for a validated scene. Extracted frames are not a 3D world.

## API routes

- `GET /health`: API process health.
- `GET /api/v1`: API name and version.
- `POST /api/v1/videos/upload`: multipart field `file`; returns HTTP 202 with `video_id`, `job_id`, and queue status.
- `GET /api/v1/jobs/{job_id}`: Celery state, progress metadata, terminal result, and explicit `world_ready` boolean.

## Reliability safeguards

- Compose waits for PostgreSQL, Redis, and MinIO health before starting the API/worker.
- Bucket creation is attempted only when the bucket is reported missing. Permission errors and storage outages are surfaced as service-unavailable errors instead of being mistaken for a missing bucket.
- If queue submission fails after upload, the API attempts to delete the orphaned source object.
- The worker uses a temporary workspace and stores its input archive under a video-specific key.
- The current worker result is explicitly `frames_extracted_gpu_stage_required`, never `world_ready`.

## Testing and deployment boundary

GitHub Actions can test the API contract, worker code, and Compose configuration. It is not a persistent video-processing server and does not provide a production GPU reconstruction service. GitHub Pages hosts only the static website; it cannot run FastAPI, Redis, MinIO, or the 3D reconstruction worker.

This project is being developed and checked through GitHub, GitHub Actions, and ChatGPT without requiring a hardware purchase, paid hosting, or a separate repository. The full 2D-video-to-3D-world goal remains the target. A compatible reconstruction runtime must eventually execute camera/pose estimation and Gaussian Splat training; this phase does not pretend that stage has already happened.

## Current limits

- Upload maximum: 500 MB.
- Video duration: 1–600 seconds.
- Supported formats: MP4, MOV/QuickTime, WebM.
- No production authentication, user quotas, resumable uploads, malware scanning, persistent relational job records, signed asset URLs, or live public backend yet.
- The viewer is a rendering surface, not a video-to-3D reconstruction engine.
