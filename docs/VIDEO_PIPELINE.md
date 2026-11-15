# Video upload and reconstruction pipeline

## Current preprocessing flow
1. Start the local stack with `docker compose up --build`.
2. Open `http://localhost:3000/upload`.
3. Select an MP4, MOV or WebM file (maximum 500 MB).
4. The API validates the extension/MIME type and stores the source in MinIO.
5. The API enqueues `reconstruction.process_video` in Redis/Celery and returns a video ID and job ID.
6. The page polls `GET /api/v1/jobs/{job_id}`.
7. The worker uses ffprobe to validate duration (1–600 seconds) and video stream, then FFmpeg samples at 2 frames/second.
8. The worker stores `reconstruction-inputs/{video_id}/inputs.zip` with JPEG frames and metadata.

This is preprocessing only. It does not yet estimate camera poses, train a Gaussian Splat, or create a 3D world.

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

## Phase 2 reconstruction boundary
A separate CUDA-capable worker must run camera/pose estimation and a compatible Gaussian-Splatting training pipeline, optimize and validate the result, package a real `.spz` artifact, and publish a durable world record. Until this exists, job completion means **preprocessing completed**, not **3D world ready**. No GPU trainer is configured in this repository yet. Do not mark a job as world-ready based only on extracted frames or a placeholder artifact.

## Browser world viewer
The `/world` route uses Three.js and `@sparkjsdev/spark` 2.4.x. Spark documents support for `.ply`, `.spz`, `.splat`, `.ksplat`, and `.sog` scene formats. A scene URL must be reachable by the browser and its host must allow cross-origin requests. The viewer currently provides orbit controls; it is a renderer integration, not a reconstruction engine. No generated sample travel world is bundled.

References:
- [Spark package and supported formats](https://www.npmjs.com/package/@sparkjsdev/spark)
- [Spark loading splats documentation](https://sparkjs.dev/docs/loading-splats/)
