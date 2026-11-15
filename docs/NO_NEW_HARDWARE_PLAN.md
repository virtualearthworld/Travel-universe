# No-new-hardware development plan

## User constraints

- Keep all source code in the existing Travel Universe monorepo.
- Use GitHub and browser tools from the iPad for source review, issue tracking, CI, Colab control, and the public UI preview.
- Do not purchase a GPU, workstation, server, or other hardware.
- Do not provision paid hosting, hosted Redis, paid object storage, or another paid third-party processing service.
- Do not claim that a video has become a 3D world until a real reconstruction artifact has been produced and opened in the viewer.

## What can run without buying hardware

1. Continue frontend, API, job-state, storage-adapter, and worker development in GitHub.
2. Use GitHub Actions for linting, unit tests, API contract tests, and small CPU-only pipeline smoke tests. GitHub-hosted runners are temporary CI machines, not a permanent video-processing service.
3. Use Google Colab as a manually started, temporary cloud runtime for frame extraction, COLMAP, and CUDA/gsplat experiments when a free GPU is available. Persist source videos, intermediate files, checkpoints, and output assets in private Google Drive storage.
4. Use the iPad browser to manage GitHub, open Colab notebooks, select private video files, and inspect the browser viewer.
5. Keep the existing Docker/Celery GPU worker architecture as the production-shaped path, but do not require it for iPad-only development.

## Colab limits and integration boundary

Google Colab's free GPU access is dynamic and not guaranteed. GPU types, usage limits, idle timeouts, and maximum runtime vary. A Colab notebook is an interactive temporary session, not a continuously available worker API. A runtime can disconnect and its local disk can be lost; persist important files in Drive.

The first Colab milestone is manual end-to-end processing of the same original travel video, ending with a validated SPZ file. The public GitHub Pages site remains static and cannot automatically dispatch work to Colab. The existing FastAPI/Celery pipeline expects persistent object storage, a queue, and a worker; an authenticated automatic app-to-Colab handoff is not implemented. Do not describe manual notebook execution as a live app backend.

## Honest 3D reconstruction boundary

The repository contains a COLMAP adapter and a Gaussian Splat adapter. The latter expects a compatible CUDA/PyTorch/gsplat installation, an actual trainer command, and an SPZ exporter. Installing the gsplat library alone is not enough. Use the documented gsplat COLMAP trainer and SPZ conversion process in the [Google Colab workflow](GOOGLE_COLAB_WORKFLOW.md), and verify every output.

A successful COLMAP sparse model is not a completed 3D world. Only a non-empty, validated SPZ file that opens in the Travel Universe viewer can satisfy the completion rule.

## Development sequence under these constraints

- Phase 1: keep the frontend, API contracts, and CI reliable.
- Phase 2: run the same private source video through Colab frame extraction and COLMAP.
- Phase 3: train Gaussian Splats with gsplat on an available Colab GPU and export SPZ.
- Phase 4: load and inspect that real scene in the existing browser viewer.
- Phase 5: only then design a secure app-to-asset publishing handoff. Do not assume Colab is a permanent API.

## Never do without explicit approval

- Enable paid hosting or GPU services.
- Add a new repository for the converter.
- Commit credentials, private videos, or generated large media artifacts.
- Put Google access tokens or GitHub personal access tokens in notebook source or public GitHub.
- Label a queued, frame-extracted, sparse-only, or failed job as a completed 3D reconstruction.
