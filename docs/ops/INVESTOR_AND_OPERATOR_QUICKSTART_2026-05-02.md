# Investor and Operator Quickstart - 2026-05-02

Purpose: give a reviewer, investor, buyer, or new technical operator a short path through the repo without getting lost.

This repo is not a single small app. It contains product surfaces, middleware, backend services, training/evaluation lanes, infrastructure, research, and private/internal doctrine pointers. Use the paths below instead of browsing root folders at random.

## What This Repository Is

SCBE-AETHERMOORE is a governed AI and agent workflow system. The current practical product lanes are:

- GeoSeal: governed routing, tokenizer, policy, and agent tool surface.
- GeoShell: visual/operator shell for apps, demos, and workflow launch.
- Agent harness: CLI and service layer for coding agents, browser agents, training/evaluation, and safe tool execution.
- Training/evaluation system: datasets, benchmark ladders, and model promotion gates.

## Fast Evaluation Path

For a first review, use this order:

1. `README.md`
2. `START_HERE.md`
3. `README_INDEX.md`
4. `docs/ops/DISTRIBUTION_PACKAGE_MAP_2026-05-02.md`
5. `docs/map-room/RELEASE_READINESS_TRACKER_2026-04-23.md`
6. `docs/ops/AGENT_BUS_USER_GUIDE.md`

If you only want the packaging contract, read:

- `docs/ops/DISTRIBUTION_PACKAGE_MAP_2026-05-02.md`
- `config/distribution_package_map.json`
- `config/offline_bundle_profiles.json`

## What To Run First

From the repo root:

```powershell
npm install
npm run build
npm run typecheck
```

For the GeoSeal agent path:

```powershell
npm run verify:geoseal-agent
```

For Python tests, prefer focused tests first. The full suite can be broad and slow:

```powershell
python -m pytest tests/agents tests/api tests/coding_spine -q
```

For the offline package builder:

```powershell
python scripts/scbe-system-cli.py layout plan --json
python scripts/scbe-system-cli.py offline build --profile cli-offline-core --output artifacts/offline_kits/cli-core-smoke --json
```

## Package Buckets

| Package | What It Is | Primary Paths |
|---|---|---|
| Public website | Public docs, demos, offer pages | `docs/`, `docs/static/`, `docs/demos/` |
| GeoShell app | Visual shell and app launcher | `scbe-visual-system/`, `app/`, `public/`, `space/` |
| GeoSeal middleware | Agent routing, tokenizer, policy, HYDRA/GeoSeal bridge | `src/coding_spine/`, `src/agentic/`, `src/crypto/`, `agents/`, `bin/` |
| Backend API | FastAPI/services/auth/health/storage probes | `api/`, `src/api/`, `services/` |
| Agent harness CLI | Local AI-operator commands, safe apply, benchmarks, offline kits | `scripts/scbe-system-cli.py`, `scripts/agents/`, `scripts/benchmark/` |
| Training/evaluation | Model configs, schemas, eval harnesses, benchmarks | `config/model_training/`, `training-data/`, `tests/`, `scripts/train*/` |
| Infrastructure | CI, Docker, Kubernetes, Vercel, deploy manifests | `.github/workflows/`, `deploy/`, `k8s/`, `Dockerfile*`, `docker-compose*.yml` |
| Private doctrine | Notion, patent, business, storage ledgers | private repo `issdandavis/SCBE-private` |

## What Not To Judge The Product By

Do not judge the product by generated folders or old research branches:

- `artifacts/`
- `dist/`
- `archive/`
- `training/runs/`
- cache folders
- private Notion-derived doctrine

Those are evidence, build outputs, or research inputs. The product should be judged by runtime code, package manifests, verification commands, release trackers, and focused tests.

## Distribution Readiness Checklist

Before showing a package externally:

- The package has a named bucket in `config/distribution_package_map.json`.
- The package excludes secrets, local path inventories, browser profiles, raw connector exports, and private Notion material.
- The package has at least one smoke command that passes on a clean checkout.
- The package has a short user or operator guide.
- Generated artifacts are attached only as evidence, not as source of truth.
- Private business/patent/proposal material stays in `SCBE-private` unless explicitly sanitized.

## Current Useful Next Steps

1. Wire `config/distribution_package_map.json` into `scripts/scbe-system-cli.py offline build` after the active Cursor CLI work lands.
2. Add one `verify:*` command per package bucket.
3. Keep `SCBE-private` as the doctrine and sensitive-document source.
4. Promote only implementation-backed Notion ideas into public docs/specs.
5. Add a release issue template that asks for package bucket, included paths, excluded paths, and smoke evidence.
