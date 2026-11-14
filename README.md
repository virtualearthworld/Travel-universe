# Travel Universe

Discover places. Enter worlds. Share the journey.

A social travel-discovery platform that turns ordinary travel videos into explorable 3D environments using 3D Gaussian Splatting.

## Monorepo
- apps/web: Next.js, TypeScript, Tailwind CSS, Zustand
- apps/api: FastAPI service
- apps/worker: asynchronous reconstruction worker contract
- packages/viewer: Three.js / React Three Fiber
- docs: architecture, roadmap, API conventions

## Local development
Install Node.js 20.11+ and Docker Compose. Copy `.env.example` to `.env`, run `npm install`, then `docker compose up --build`. Web: http://localhost:3000; API health: http://localhost:8000/health.

Phase 1 foundation only: authentication, production uploads, GPU reconstruction and the final splat viewer are later phases.
