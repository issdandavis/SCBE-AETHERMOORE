# Product Quickstart

This is the shortest real path from clone to a working SCBE-AETHERMOORE product surface.

Use this file when the question is:

- what should I run first
- what is the actual product lane
- how do I prove the repo is working without reading the full theory stack

## Official First-Run Lane

The current product-first lane is the AetherBrowser local service path:

- backend service on `127.0.0.1:8002`
- Chrome DevTools Protocol on `127.0.0.1:9222`
- verification script that proves both surfaces are alive

This is the cleanest operational surface because it already has:

- one start command
- one verify command
- one stop command

## Prerequisites

- Node.js `18+`
- Python available as `python`
- Google Chrome installed
- repo dependencies installed with `npm install`

## Fast Path

From the repo root:

```powershell
npm install
npm run aetherbrowser:service:start
npm run aetherbrowser:service:verify
```

## Profile-Driven Launch (Phase 0/1 Contract)

The restructure lane now uses one command family with explicit profile blast radius.

```powershell
npm run scbe:launch:dev-min
```

Available profiles:

- `npm run scbe:launch:dev-min`
- `npm run scbe:launch:browser`
- `npm run scbe:launch:training`
- `npm run scbe:launch:contracts`
- `npm run scbe:launch:full-local`

Run the stabilization gates before path moves:

```powershell
npm run scbe:phase01:gates
```

What those do:

- `aetherbrowser:service:start`
  - starts the backend service and Chrome debug session
- `aetherbrowser:service:verify`
  - checks backend health
  - checks Chrome CDP
  - writes a report under `artifacts/smokes/`

## Expected Proof

The lane is considered working when:

- `http://127.0.0.1:8002/health` responds
- `http://127.0.0.1:9222/json/list` responds
- the verify script emits a report under:
  - `artifacts/smokes/aetherbrowser-service-verify-*/service_verify_report.json`

## Stop

```powershell
npm run aetherbrowser:service:stop
```

## Secondary Public Surfaces

If you are evaluating package or API surfaces after the browser lane proves out, use these next.

### TypeScript package lane

```powershell
npm run build
npm run typecheck
npm test
```

### Python governance API lane

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8080
```

### Newer control-plane API lane

```powershell
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Those are real lanes, but they are not the official first-run path for a new reviewer. The browser-and-local-service loop is the current top-level product entry.

## Open These After The Quickstart

Once the service loop is up, the next useful files are:

1. `README.md`
2. `START_HERE.md`
3. `docs/REPO_SURFACE_MAP.md`
4. `docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md`
5. `CANONICAL_SYSTEM_STATE.md`

## Boundary

Do not treat the following as required for first-run success:

- `training/`
- `training-data/`
- `notes/`
- `notebooks/`
- `archive/`
- proposal packets
- historical screenshots or generated reports

Those stay useful, but they are not the product quickstart.
