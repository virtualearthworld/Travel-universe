# Video upload and reconstruction pipeline

## Current pipeline stages

1. **Upload:** the API accepts MP4, MOV, or WebM files up to 500 MB.
2. **Store:** the original video is saved to S3-compatible object storage.
3. **Queue:** a Celery job is submitted to Redis and a job ID is returned.
4. **Inspect:** the worker uses ffprobe to validate a video stream and a 1–600 second duration.
5. **Prepare:** FFmpeg samples frames at 2 frames per second and creates a metadata manifest.
6. **Package:** the frames and manifest are stored as `reconstruction-inputs/{video_id}/inputs.zip`.
7. **Reconstruct:** COLMAP estimates camera poses and a sparse point cloud; the Gaussian Splat stage then trains and exports a real `.spz` scene when a compatible GPU runtime and configured trainer/exporter are available.
8. **Publish:** validate the generated scene and register a durable world asset for the browser viewer.

The API job response exposes `world_ready`. It remains false for queued, running, failed, or preprocessing-only jobs. A job may be marked world-ready only when a reconstruction worker returns `status: "world_ready"` and a non-empty `world_asset_key` for a validated scene. Extracted frames and sparse camera poses are not a finished 3D world.

## Camera poses and sparse reconstruction (Phase 3)

The worker exposes a separate `reconstruction.estimate_camera_poses` Celery task. It consumes the saved frame ZIP, runs COLMAP feature extraction, sequential matching, and mapping in a deterministic order, validates the sparse model files, and stores a sparse-reconstruction bundle.

This stage requires the external `colmap` executable on the worker PATH. The standard CPU worker image does not install COLMAP automatically; install a compatible COLMAP build in the environment that will execute this task. GitHub CI uses mocked subprocess tests and does not claim to run COLMAP or process a real travel video.

A successful result is `sparse_reconstruction_ready_gsplat_required`, not `world_ready`. Sparse camera poses and points are only the input to CUDA-capable Gaussian Splat training, scene validation, and real `.spz` export.

## Gaussian Splat training and export (Phase 4)

The optional GPU worker exposes `reconstruction.train_gaussian_splats` and a validation adapter. It consumes the original frame archive plus the COLMAP sparse-model archive, checks for PyTorch, gsplat, and CUDA, invokes a configured training entry point (`GSPLAT_TRAIN_COMMAND`), then invokes a configured PLY-to-SPZ converter (`SPLAT_EXPORT_COMMAND`). It validates that both the intermediate PLY and final SPZ are non-empty before uploading the SPZ asset and returning `status: world_ready` with its object key.

The trainer and converter are deployment-provided commands, not bundled implementations. The current GPU image does not install a pinned CUDA/PyTorch/gsplat stack or a converter automatically. Configure compatible dependencies and both commands on a CUDA-capable worker before dispatching this task. CPU CI mocks those boundaries; it does not perform real training or prove a travel-video reconstruction. The existing Spark viewer can load an SPZ URL, but the public site still needs a live API/storage configuration and a real generated asset to display a reconstructed world.

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
- The current preprocessing result is explicitly `frames_extracted_gpu_stage_required`, never `world_ready`.

## Testing and deployment boundary

GitHub Actions can test the API contract, worker code, and Compose configuration. It is not a persistent video-processing server and does not provide a production GPU reconstruction service. GitHub Pages hosts only the static website; it cannot run FastAPI, Redis, MinIO, or the 3D reconstruction worker.

This project is being developed and checked through GitHub, GitHub Actions, and ChatGPT without requiring a hardware purchase, paid hosting, or a separate repository. The full 2D-video-to-3D-world goal remains the target. A compatible reconstruction runtime must execute camera/pose estimation and Gaussian Splat training; this phase does not pretend that stage has already happened.

## Current limits

- Upload maximum: 500 MB.
- Video duration: 1–600 seconds.
- Supported formats: MP4, MOV/QuickTime, WebM.
- No production authentication, user quotas, resumable uploads, malware scanning, persistent relational job records, signed asset URLs, or live public backend yet.
- The viewer is a rendering surface, not a video-to-3D reconstruction engine.
