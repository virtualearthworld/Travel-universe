# Roadmap

The product's core promise is converting an ordinary travel video into a real, explorable 3D destination. The order below prioritizes that end-to-end experience before expanding social features.

## Phase 1 — Foundation
- [x] Monorepo, service boundaries, local infrastructure and CI scaffold
- [x] Initial Next.js experience and GitHub Pages deployment
- [x] Video upload API, object storage, async job queue and frame-extraction worker foundation
- [ ] Verify full local container startup and integration tests

## Phase 2 — 3D reconstruction engine
- [x] Validate uploaded video and extract timestamped source frames
- [x] Persist reconstruction-input bundle and metadata
- [ ] Add durable database-backed job state, retries and cancellation
- [ ] Add camera/pose estimation and scene preprocessing
- [ ] Integrate a CUDA-capable 3D Gaussian Splatting trainer
- [ ] Validate scene quality and package a real .spz output
- [ ] Store the published scene artifact and expose a world-ready API state

**Acceptance gate:** a representative travel video must produce a real, non-empty, valid Gaussian Splat scene artifact. Extracted frames or a demo scene do not count as reconstruction success. GPU training is not yet configured in this repository.

## Phase 3 — Interactive 3D world viewer
- [x] Integrate the Spark Three.js Gaussian Splat renderer foundation
- [ ] Test loading a known-good real scene artifact in the deployed browser
- [ ] Add first-person/free-roam navigation alongside orbit controls
- [ ] Add mobile-friendly look, zoom and movement controls
- [ ] Add loading, error, streaming and performance handling

## Phase 4 — Complete creator-to-world experience
- [x] Initial homepage and upload interface
- [ ] Connect the deployed frontend to a hosted upload/reconstruction API
- [ ] Show reliable queued, processing, failed and world-ready states
- [ ] Link each completed upload to its generated 3D world
- [ ] Add creator publishing and destination metadata

## Phase 5 — Social travel platform
- [ ] Authentication and secure sessions
- [ ] User and creator profiles
- [ ] Follow graph and destination discovery feed
- [ ] Likes, comments, saves, sharing and moderation
- [ ] Database migrations, authorization and API tests

## Final — Testing and production readiness
- [ ] End-to-end tests using representative travel footage
- [ ] Threat model, authentication, authorization and rate limits
- [ ] Privacy, retention and deletion workflows
- [ ] Load, security and accessibility tests
- [ ] Backups, monitoring, alerting and disaster recovery
- [ ] Production deployment, GPU capacity and release process
