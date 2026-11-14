# Video upload and preprocessing

## Local flow
1. Start the stack with `docker compose up --build`.
2. Open `http://localhost:3000/upload`.
3. Select an MP4, MOV or WebM file (maximum 500 MB).
4. The API validates the extension/MIME type and stores the source in MinIO.
5. The API enqueues `reconstruction.process_video` in Redis/Celery and returns a video ID and job ID.
6. The page polls `GET /api/v1/jobs/{job_id}`.
7. The worker uses ffprobe to validate duration (1–600 seconds) and video stream, then FFmpeg samples at 2 frames/second.
8. The worker stores `reconstruction-inputs/{video_id}/inputs.zip` with JPEG frames and metadata.

## API
- `GET /health`: service health.
- `GET /api/v1`: API identity/version.
- `POST /api/v1/videos/upload`: multipart field `file`; returns HTTP 202 with `video_id`, `job_id`, and queue status.
- `GET /api/v1/jobs/{job_id}`: Celery state, progress metadata, and terminal result/error.

## Limits and deployment notes
- API upload limit: 500 MB.
- Worker clip duration limit: 10 minutes.
- Supported extensions/MIME types: MP4, MOV/QuickTime, WebM.
- Configure `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`, and `REDIS_URL` for deployment.
- The current local Compose credentials are development-only and must be replaced before exposure to the internet.
- Add authentication, per-user quotas, malware/content scanning, durable database records, resumable uploads and signed download URLs before production use.

## Reconstruction boundary
Frame extraction is only input preparation. A separate CUDA-capable worker must run camera/pose estimation and a compatible Gaussian-Splatting training pipeline, optimize/validate the result, package a real `.spz` artifact, and publish a durable world record. Until this exists, job completion means **preprocessing completed**, not **3D world ready**. No GPU trainer is configured in this repository yet.

## Browser world viewer
The web app has an `/world` route backed by the Three.js Gaussian Splat viewer package. Paste a browser-accessible scene URL ending in `.ply`, `.splat`, or `.ksplat`. The viewer uses its built-in orbit controls. The selected renderer does **not** load `.spz` directly; convert SPZ output to a supported PLY/KSPLAT format before serving it. The scene host must allow cross-origin browser requests. This is a viewer integration, not a generated scene; no sample 3D world is bundled.
