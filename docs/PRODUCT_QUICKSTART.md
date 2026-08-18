# Product Quickstart

Users send agent traffic through SCBE. SCBE PQC-seals it, gates it, writes a receipt, and bills provider cost + 2%.

See `RELEASE.md` at the repo root. That is the product door. This file is the short run path.

## Official First-Run Lane

```powershell
python -m uvicorn src.api.main:app --port 8000
```

- API: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- Health: `GET /v1/health`
- Billing: `/billing` (Stripe checkout + webhooks from `src/api/stripe_billing.py`)

Fee rule: `billed_cents = provider_cost_cents + ceil(provider_cost_cents * 0.02)`.

Crypto on this path: ML-KEM-768 (session), ML-DSA-65 (receipts).

## Optional clients

- AetherDesk (separate repo): `npm run aetherdesk` → `http://127.0.0.1:5717`
- AetherBrowse (in this repo, later): `src/browser/`

## Prerequisites

- Python 3.11+
- Node.js 18+ if you run AetherDesk or the TypeScript package
- Stripe keys only if you are testing checkout (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`)

## Prove it

```powershell
pytest tests/api/test_provider_pass_through_fee.py -q
```

The AetherBrowser local service (`npm run aetherbrowser:service:start`) is a client lane, not the product API.

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
