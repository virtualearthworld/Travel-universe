# Architecture

## Product loop
1. Creator uploads a standard travel video.
2. API stores source media in S3-compatible storage and creates a reconstruction job.
3. Preprocessing worker validates the video and extracts frames.
4. A CUDA-capable reconstruction worker estimates camera poses and trains a 3D Gaussian Splat scene (Phase 2).
5. A validated scene artifact (target delivery format: .spz) is stored in object storage.
6. Browser viewer loads the real artifact through the Spark Three.js renderer (Phase 3).
7. The creator publishes the destination through the upload-to-world experience (Phase 4).
8. Profiles, follows, feed, likes, comments, and sharing support discovery (Phase 5).

## Boundaries
- apps/web: Next.js App Router, Tailwind, Zustand.
- apps/api: FastAPI metadata, auth, upload orchestration, social APIs.
- apps/worker: Celery + Redis job processing; GPU dependencies remain isolated.
- packages/viewer: browser 3D rendering.
- PostgreSQL: users, videos, worlds, jobs, and social metadata.
- S3-compatible storage: raw video, frames, training artifacts, published splats.

## Engineering rules
- Long-running reconstruction is asynchronous; HTTP requests must not wait for training.
- Job states: pending, validating, extracting, training, packaging, ready, failed.
- Store object keys and metadata in PostgreSQL, not media binaries.
- Treat .spz as a delivery artifact, not the training format.
- Use signed, time-limited URLs for private media.
- Version pipeline metadata for reproducibility.
- A job is world-ready only after a real scene artifact passes validation and can be loaded by the browser viewer.
