# Roadmap

## Phase 1 — Foundation
- [x] Monorepo, service boundaries, local infrastructure and CI scaffold
- [ ] Branch protection and required checks (requires repository administration permission)
- [ ] Verify full container startup and integration tests

## Phase 2 — Authentication, profiles, social feed
- [ ] Authentication and secure sessions
- [ ] User and creator profiles
- [ ] Follow graph and feed baseline
- [ ] Likes, comments, saves, sharing and moderation
- [ ] Database migrations, authorization and API tests

## Phase 3 — Upload and reconstruction
- [x] Multipart video upload and basic format/size validation
- [x] Object storage and asynchronous job queue
- [x] Video metadata validation, frame extraction and input bundle
- [ ] Durable database-backed job state, retries and cancellation
- [ ] Camera/pose estimation and scene preprocessing
- [ ] GPU worker and 3D Gaussian Splatting training
- [ ] Packaging, .spz validation and delivery

## Phase 4 — Interactive world viewer
- [ ] Integrate and validate a production Gaussian Splat renderer
- [ ] First-person and free-roam navigation
- [ ] Look, zoom, movement and mobile controls
- [ ] Loading, streaming and performance budgets

## Phase 5 — Production readiness
- [ ] Threat model, authentication, authorization and rate limits
- [ ] Privacy, retention and deletion workflows
- [ ] Load, security and accessibility tests
- [ ] Backups, monitoring, alerting and disaster recovery
- [ ] Production deployment, GPU capacity and release process
