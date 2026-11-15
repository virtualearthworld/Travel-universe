# Roadmap

The product's core promise is converting an ordinary travel video into a real, explorable 3D destination. The milestones below prioritize that end-to-end experience before social features.

## Phase 1 — Foundation
- [x] Monorepo, service boundaries, local infrastructure and CI scaffold
- [x] Initial Next.js experience and GitHub Pages deployment
- [x] Video upload API, object storage, async job queue and frame-extraction worker foundation
- [ ] Verify full local container startup and integration tests

## Phase 2 — Video-to-3D reconstruction engine
- [x] Validate uploaded video and extract source frames
- [x] Persist reconstruction-input bundle and metadata
- [x] Add COLMAP sparse-reconstruction adapter
- [x] Add Gaussian Splat training/export adapter with explicit CUDA and exporter validation
- [ ] Install and pin a compatible COLMAP runtime in the worker environment
- [ ] Install and pin a compatible CUDA/PyTorch/gsplat runtime and verified SPZ exporter
- [x] Add opt-in Celery orchestration from preprocessing → COLMAP → GPU Gaussian Splat training → SPZ publication
- [ ] Validate reconstruction quality on representative travel footage
- [ ] Persist durable job state, retries and cancellation

**Acceptance gate:** orchestration code is implemented and CPU-tested, but a representative travel video must still produce a real, non-empty, valid Gaussian Splat scene artifact before reconstruction is considered complete. Extracted frames, sparse points, adapter code, or a demo scene do not count as reconstruction success.

## Phase 3 — Interactive 3D world viewer
- [x] Integrate the Spark Three.js Gaussian Splat renderer foundation
- [x] Add API delivery endpoint for short-lived URLs to published SPZ assets
- [x] Add upload-to-world browser handoff
- [ ] Test loading a real reconstructed travel scene in the deployed browser
- [ ] Add first-person/free-roam navigation alongside orbit controls
- [ ] Add mobile-friendly look, zoom and movement controls
- [ ] Add streaming, performance and accessibility tests

## Phase 4 — Complete creator-to-world experience
- [x] Initial homepage and upload interface
- [x] Upload status polling and explicit distinction between prepared footage and a published world
- [x] Link a world-ready upload to its generated browser destination
- [ ] Connect the deployed frontend to a publicly hosted API and object storage
- [ ] Show reliable queued, processing, failed and world-ready states against a live backend
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
- [ ] Production deployment and a sustainable reconstruction compute runtime
