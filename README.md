# Travel Universe

**Discover places. Enter worlds. Share the journey.**

Travel Universe is a social travel-discovery product concept: creators upload ordinary travel videos, the platform prepares footage for 3D reconstruction, and viewers will eventually explore published destinations as immersive environments.

## Repository
- `apps/web`: Next.js, TypeScript, Tailwind CSS and Zustand.
- `apps/api`: FastAPI upload and asynchronous job-status API.
- `apps/worker`: Celery worker for video validation, FFmpeg frame extraction and reconstruction-input packaging.
- `packages/viewer`: Three.js / React Three Fiber viewer foundation.
- `docs`: architecture, API conventions, roadmap and video-pipeline notes.

## Local development
Requirements: Node.js 20.11+, Docker Compose v2 and Git.

```bash
cp .env.example .env
npm install
docker compose up --build
```

Open:
- Web app: http://localhost:3000
- Upload page: http://localhost:3000/upload
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

Use a short MP4, MOV or WebM clip for a first local upload. The upload service currently accepts files up to 500 MB; the worker accepts videos up to 10 minutes, extracts two frames per second, and stores a ZIP containing frames and metadata in the S3-compatible bucket.

## Current implementation status
- Phase 1 repository and CI foundation: merged to `main`.
- Video upload, object storage, Celery job queue, status polling, FFmpeg validation/frame extraction and input-bundle persistence: implemented on the video pipeline feature branch, pending CI/merge.
- Actual CUDA Gaussian-Splatting reconstruction, trained scene optimization, `.spz` export, and production interactive splat rendering: **not yet implemented**.
- Authentication, user profiles, follow graph, feed, likes, comments and moderation: **not yet implemented**.
- Production hosting, GPU infrastructure, secrets, backups and operational monitoring: **not configured**.

The interface must never label extracted frames as a completed 3D world. A world is ready only after a real reconstruction artifact has been generated and validated.
