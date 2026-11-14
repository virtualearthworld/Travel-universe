# API conventions

Base path: /api/v1.

## Implemented
- GET /health — service health.
- GET /api/v1 — API identity and version.

## Planned resource groups
- /auth: account lifecycle and sessions.
- /users: profiles and creator settings.
- /videos: upload intents, metadata, processing status.
- /worlds: published scenes and viewer metadata.
- /feed: discovery.
- /social: follows, likes, comments, saves, reports.

Write endpoints must enforce authorization, size/content validation, and ownership. Expensive processing must be submitted as background jobs.
