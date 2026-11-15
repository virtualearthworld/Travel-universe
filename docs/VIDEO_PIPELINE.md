# Video upload and reconstruction pipeline

## Current preprocessing flow
1. Start the local stack with `docker compose up --build`.
2. Open `http://localhost:3000/upload`.
3. Select an MP4, MOV or WebM file (maximum 500 MB).
4. The API validates the extension/MIME type and stores the source in S3-compatible storage.
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

## Connect the hosted website
The GitHub Pages frontend is static, so the API must run as a separate public HTTPS service. Configure the GitHub repository variable `NEXT_PUBLIC_API_URL` with the API's public base URL (no trailing slash), then rerun the **Deploy Travel Universe website** workflow so the URL is embedded in the frontend build.

Configure the API service with:
- `CORS_ORIGINS=https://virtualearthworld.github.io`
- `REDIS_URL` pointing to a reachable Redis service
- `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `S3_REGION` pointing to durable S3-compatible object storage
- `MAX_VIDEO_BYTES` is currently fixed at 500 MB in the API code

Run the same worker image as a separate always-on background service with the same `REDIS_URL` and S3 settings. The API alone cannot process queued videos. The public API URL must support HTTPS, multipart requests up to 500 MB, and the `/health` and `/api/v1` routes.

Do not expose the local MinIO or Redis ports to the public internet. Use private service networking or authenticated managed services. Set strong unique credentials; never commit secrets to GitHub. GitHub Pages cannot host FastAPI, Redis, object storage, or a background worker.

**Deployment boundary:** the repository now passes the API URL into the static frontend build and permits the GitHub Pages origin in API CORS. A live backend is not provisioned by this repository change; it still requires a hosting provider, durable object storage, Redis, and deployment credentials. Until those services exist and pass an end-to-end upload test, public uploads remain unavailable.

## Limits and deployment notes
- API upload limit: 500 MB.
- Worker clip duration limit: 10 minutes.
- Supported extensions/MIME types: MP4, MOV/QuickTime, WebM.
- The current local Compose credentials are development-only and must be replaced before exposure to the internet.
- Add authentication, per-user quotas, malware/content scanning, durable database records, resumable uploads and signed download URLs before production use.

## Phase 2 reconstruction boundary
A separate CUDA-capable worker must run camera/pose estimation and a compatible Gaussian-Splatting training pipeline, optimize and validate the result, package a real `.spz` artifact, and publish a durable world record. Until this exists, job completion means **preprocessing completed**, not **3D world ready**. No GPU trainer is configured in this repository yet. Do not mark a job as world-ready based only on extracted frames or a placeholder artifact.

## Browser world viewer
The `/world` route uses Three.js and `@sparkjsdev/spark` 2.4.x. Spark supports `.ply`, `.spz`, `.splat`, `.ksplat`, and `.sog` scene formats. A scene URL must be reachable by the browser and its host must allow cross-origin requests. The viewer currently provides orbit controls; it is a renderer integration, not a reconstruction engine. No generated sample travel world is bundled.
