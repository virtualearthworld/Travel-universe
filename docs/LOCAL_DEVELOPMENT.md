# Local development (Phase 1)

Travel Universe remains a single monorepo. The public GitHub Pages site is a static frontend preview; the video-to-3D pipeline is designed to run locally.

## Prerequisites

- Docker Desktop (or Docker Engine) with Docker Compose v2
- Node.js 20.11 or newer and npm
- For GPU reconstruction later: a supported NVIDIA GPU, current NVIDIA driver, and NVIDIA Container Toolkit
- Linux is the recommended host for the CUDA worker. The GPU profile is optional; CPU-only development does not require an NVIDIA GPU.

## Start the local stack

From the repository root:

```bash
cp .env.example .env
npm install
docker compose config
docker compose up --build
```

Open the web app at http://localhost:3000 and the API health endpoint at http://localhost:8000/health. MinIO's console is at http://localhost:9001. Change the development credentials in `.env` before using the stack beyond a private local machine.

Stop the stack with:

```bash
docker compose down
```

Remove local database and object-storage data only when intentionally resetting the development environment:

```bash
docker compose down -v
```

## Optional NVIDIA worker

After installing and verifying NVIDIA Container Toolkit on the host:

```bash
docker compose --profile gpu config
docker compose --profile gpu up --build
```

The GPU worker image is only the container foundation. It does not yet mean that COLMAP reconstruction, gsplat training, or SPZ export is implemented. Those are Phase 3 deliverables and require compatible GPU hardware and dependencies.

## Scope and safety

- No Render, Railway, hosted Redis, or paid cloud services are part of this local setup.
- MinIO, Redis, PostgreSQL, and the worker run as local containers.
- Never commit real passwords, access keys, or private video files.
- The public Pages frontend and the local processing stack are separate; a public browser cannot reach localhost on your computer.
