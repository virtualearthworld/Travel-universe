# Travel Universe

**Discover places. Enter worlds. Share the journey.**

Travel Universe is a social travel-discovery product focused on one core experience: upload an ordinary travel video and, when the reconstruction runtime is available, turn it into an explorable 3D destination.

## Repository

- `apps/web`: Next.js, TypeScript and Tailwind browser interface.
- `apps/api`: FastAPI video upload, job status and world-asset delivery API.
- `apps/worker`: Celery video preprocessing worker and reconstruction adapters.
- `packages/viewer`: Three.js / Spark Gaussian Splat viewer foundation.
- `docs`: architecture, API conventions, roadmap and pipeline notes.

## iPad-first Google Colab workflow

The project now documents a no-new-hardware route for manually running reconstruction from an iPad using a temporary Google Colab runtime and private Google Drive storage. Start with [the Google Colab reconstruction guide](docs/GOOGLE_COLAB_WORKFLOW.md). Free GPU availability is not guaranteed, and Colab is not a persistent API/backend; the guide explains the manual workflow and its limits.

## Local development

Requirements: Node.js 20.11+, Docker Compose v2 and Git.

```bash
cp .env.example .env
npm install
docker compose up --build
```

Open the web app at `http://localhost:3000`, upload at `/upload`, API health at `http://localhost:8000/health`, API docs at `http://localhost:8000/docs`, and MinIO console at `http://localhost:9001`.

The upload API accepts MP4, MOV and WebM up to 500 MB. By default, the standard worker validates footage, extracts two frames per second, and stores a reconstruction-input ZIP. To run the full chain, configure COLMAP on the CPU worker and a compatible CUDA/gsplat trainer plus SPZ exporter on the GPU worker, then set `ENABLE_RECONSTRUCTION_PIPELINE=true` in `.env` and start the optional GPU profile. This code path is not enabled or proven on the public GitHub Pages deployment.

## Implementation status (verified)

- Repository foundation, Next.js interface, GitHub Pages deployment, FastAPI upload endpoint, object storage integration, Redis/Celery queue and FFmpeg frame extraction are present.
- An opt-in Celery chain now connects preprocessing → COLMAP on the CPU queue → Gaussian Splat training/export on the dedicated GPU queue. It is disabled by default; the standard worker image still needs a compatible COLMAP executable.
- The Gaussian Splat adapter requires a CUDA-enabled PyTorch/gsplat environment plus externally configured `GSPLAT_TRAIN_COMMAND` and `SPLAT_EXPORT_COMMAND`; those dependencies and commands are not bundled or configured by GitHub Pages.
- The Spark-based browser viewer can load a compatible scene URL. The upload-to-world handoff is being completed; a real scene from a user travel video has not yet been generated and validated.
- Production API/object storage hosting, GPU execution, durable job records, authentication, secrets management, backups and operational monitoring are not configured.

**Truthful completion rule:** a video is not a 3D world just because frames were extracted or a job finished. Travel Universe may show “world ready” only after a non-empty, validated SPZ scene exists and is accessible to the browser viewer.

## Cost and infrastructure boundary

GitHub Pages hosts static frontend files. GitHub Actions runs temporary CI jobs; it is not a persistent API, object store, queue or GPU server. Google Colab can be used as a manually started, temporary reconstruction runner, subject to free-tier resource availability and session limits. It does not automatically receive jobs from the public website. No paid service or new hardware is assumed by this repository.

See [the video pipeline guide](docs/VIDEO_PIPELINE.md) for the existing worker orchestration and [the Colab guide](docs/GOOGLE_COLAB_WORKFLOW.md) for the iPad-first manual workflow.
