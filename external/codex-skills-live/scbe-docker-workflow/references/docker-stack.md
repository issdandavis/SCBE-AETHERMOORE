# SCBE Docker Stack Reference

## Service Files and Intent

- `Dockerfile`
  - Multi-stage build for TypeScript + Python + liboqs PQC runtime
  - Exposes `8080`, defaults command `uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}`
- `docker-compose.yml`
  - `scbe-app`: main app stack (ports `3000:3000`, `8000:8000`)
  - `scbe-demo`: nginx static demo on `8080:80`
- `docker-compose.api.yml`
  - API-only service on `8080:8080`
  - Health endpoint: `GET /v1/health`
- `docker-compose.unified.yml`
  - `scbe-core` (port `8000`), `scbe-gateway` (port `8080`)
  - `redis` and metrics services (`prometheus`/`grafana`) for larger deployments

## Ports and Health Endpoints

- Core API (most repos): `8000`
  - Primary health check: `/v1/health`
- Unified gateway: `8080`
  - Health check: `/health`
- Demo host bridge: `8080` mapped to demo web server in default stack

## Build and Run Playbook

1. Build:
   - `docker build -t scbe-aethermoore:latest .`
2. Validate image:
   - `docker images scbe-aethermoore`
3. Run:
   - `docker run -it -p 8000:8000 scbe-aethermoore:latest`
4. Verify:
   - `curl http://localhost:8000/v1/health`

## Stack Startup Recipes

- Baseline compose:
  - `docker-compose up -d`
- API-only compose:
  - `docker-compose -f docker-compose.api.yml up -d`
  - `curl http://localhost:8080/v1/health`
- Unified compose:
  - `docker-compose -f docker-compose.unified.yml up -d`
  - Validate `scbe-core` + `scbe-gateway` health endpoints

## Troubleshooting Matrix

- Build fails at `apt` or `cmake` steps:
  - Retry with `--no-cache`, ensure outbound network access for package downloads and GitHub tarball pulls.
- Compose service keeps restarting:
  - `docker-compose logs -f <service>`
  - Confirm mapped ports are not occupied on host
  - Confirm env variables loaded from `.env` or inline environment in compose file
- Healthcheck never reports healthy:
  - Confirm endpoint path for selected stack (`/v1/health` vs `/health`)
  - Check command dependencies and runtime init timeouts
- Need a clean restart:
  - `docker-compose -f <file> down --volumes --remove-orphans`
  - `docker container prune`
  - `docker image prune`

## Useful Repo Commands

- `npm run docker:build`
- `npm run docker:compose`
- `npm run docker:run`
