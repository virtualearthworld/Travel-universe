# Architecture

## Product loop
1. Creator uploads a standard travel video.
2. API stores source media in S3-compatible storage and creates a reconstruction job.
3. Worker extracts frames, estimates camera motion, and trains a 3D Gaussian Splatting scene (Phase 3).
4. Scene artifacts (target delivery format: .spz where supported) are stored in object storage.
5. Browser viewer renders the world through Three.js / React Three Fiber and a compatible Gaussian Splat renderer.
6. Profiles, follows, feed, likes, comments, and sharing support discovery.

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
