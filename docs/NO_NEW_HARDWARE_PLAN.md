# No-new-hardware development plan

## User constraints

- Keep all source code in the existing Travel Universe monorepo.
- Use GitHub and the browser for source review, issue tracking, CI, and the public UI preview.
- Do not purchase a GPU, workstation, server, or other hardware.
- Do not provision Render, Railway, hosted Redis, paid object storage, or another third-party processing service.
- Do not claim that a video has become a 3D world until a real reconstruction artifact has been produced and opened in the viewer.

## What can run without buying hardware

1. Continue frontend, API, job-state, storage-adapter, and worker development in GitHub.
2. Use GitHub Actions for linting, unit tests, API contract tests, and small CPU-only pipeline smoke tests. GitHub-hosted runners are temporary CI machines, not a permanent video-processing service.
3. Keep MinIO, Redis, PostgreSQL, FFmpeg, and the worker available as a local Docker Compose stack. This uses the computer already available to the project owner; it does not imply a new hardware purchase.
4. Keep the NVIDIA worker optional. It must not be required to install dependencies, run the web interface, or test API/queue contracts.

## Honest 3D reconstruction boundary

COLMAP and 3D Gaussian Splatting are computationally demanding. The planned gsplat training path is optimized for CUDA-capable NVIDIA GPUs. Without compatible GPU access, development can still implement and test orchestration, frame extraction, COLMAP invocation contracts, file formats, and viewer loading. A small CPU experiment may be possible, but it is not a promise of practical full-video reconstruction speed or quality.

A GitHub Pages website cannot execute a Python worker or access a user's localhost. GitHub Actions also cannot act as a continuously available backend after a workflow ends. Therefore, with the current no-purchase/no-third-party constraint, the public browser site remains a UI preview; actual processing must run on an already-available computer or wait until an approved compute option exists.

## Development sequence under these constraints

- Phase 1: make Compose and CI reliable; keep GPU optional.
- Phase 2: implement upload/job APIs and MinIO integration; test with local containers and mocked S3 in CI.
- Phase 3: implement FFmpeg extraction and COLMAP/gsplat adapters with CPU-safe tests; mark CUDA training as hardware-gated.
- Phase 4: load a known valid sample splat in the Three.js viewer and show job status honestly.
- Phase 5: end-to-end test on available hardware, without provisioning paid services.

## Never do without explicit approval

- Enable paid hosting or GPU services.
- Add a new repository for the converter.
- Commit credentials, private videos, or generated large media artifacts.
- Label a queued, frame-extracted, or failed job as a completed 3D reconstruction.
