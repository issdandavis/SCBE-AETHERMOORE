# Distribution Package Map - 2026-05-02

Purpose: define the deployable buckets for SCBE-AETHERMOORE without moving files blindly. This is a packaging contract for repo cleanup, offline bundles, CI, and release planning.

This document is descriptive until wired into automation. The machine-readable companion is `config/distribution_package_map.json`.

## Major System Buckets

| Bucket | Purpose | Typical Paths | Ship Status |
|---|---|---|---|
| Frontend | User-facing apps, demos, shell surfaces, static website | `docs/`, `app/`, `public/`, `scbe-visual-system/`, `space/` | Ship selectively |
| Middleware | Agent routing, GeoSeal, HYDRA, policy, tokenizer bridges, browser/API adapters | `src/agentic/`, `src/coding_spine/`, `src/geoseal*`, `agents/`, `scripts/agents/` | Ship as governed runtime |
| Backend | FastAPI services, API gateways, storage adapters, auth, health checks | `api/`, `src/api/`, `services/`, `scripts/system/*service*` | Ship with deployment profiles |
| Infrastructure | Docker, compose, Kubernetes, Vercel/GitHub workflows, deployment manifests | `deploy/`, `k8s/`, `.github/workflows/`, `Dockerfile*`, `docker-compose*.yml`, `vercel.json` | Ship by environment |
| CLI and Operator Tools | Local operational CLI, bundle builder, smoke checks, agent tools | `scripts/scbe-system-cli.py`, `bin/`, `scripts/system/`, `scripts/benchmark/` | Ship in operator package |
| Training and Evaluation | Datasets, configs, benchmarks, harnesses, runbooks | `config/model_training/`, `training-data/`, `tests/`, `scripts/train*/`, `scripts/benchmark/` | Split public eval vs internal training |
| Documentation and Guides | User guides, operator guides, system guides, architecture specs | `README.md`, `README_INDEX.md`, `docs/`, `docs/ops/`, `docs/specs/` | Ship as curated docs |
| Research and Doctrine | Notion exports, R&D specs, patent-sensitive notes, exploratory notebooks | `docs/research/`, `notes/`, `exports/`, private `SCBE-private` | Private/internal by default |
| Generated and Archive | Build outputs, artifacts, caches, old branches, local run outputs | `artifacts/`, `dist/`, `archive/`, `training/runs/`, `*.cache` | Do not ship unless explicitly packaged |

## Distribution Packages

### 1. Public Website Package

Purpose: public trust surface, demos, docs, offer pages, and lightweight offline help.

Include:

- `docs/`
- `docs/static/`
- `docs/demos/`
- public `README.md`
- public product/support pages

Exclude:

- private Notion exports
- patent workpapers
- generated training runs
- local path inventories
- credentials, environment files, raw connector exports

Verification:

- GitHub Pages build passes
- link/publish surface validator passes where available
- no private file path inventories or secrets

### 2. GeoShell App Package

Purpose: user-facing shell for Polly Pads, GeoSeal, agent routing, visual apps, and local/remote workflow launch.

Include:

- `scbe-visual-system/`
- `app/`
- `public/`
- `space/` frontend clients where applicable
- launcher registry files and app tiles

Exclude:

- direct training datasets
- large generated artifacts
- private business/proposal docs

Verification:

- frontend build/typecheck
- smoke screenshot or static render check
- configured API base works against local or deployed backend

### 3. GeoSeal Middleware Package

Purpose: governed routing layer for tools, agents, tokenizer, HYDRA, and policy decisions.

Include:

- `src/coding_spine/`
- `src/geoseal*`
- `src/agentic/`
- `src/crypto/`
- `agents/`
- `bin/geoseal.cjs`
- focused GeoSeal tests

Exclude:

- exploratory R&D pages unless promoted to specs
- local `.env` files
- raw Notion materials

Verification:

- `npm run verify:geoseal-agent`
- focused Python policy/tool tests
- no secret-dependent live calls in default verification

### 4. Backend API Package

Purpose: deployable API surface for health, routing, browser/agent bridge, auth, storage probes, and public service calls.

Include:

- `api/`
- `src/api/`
- `services/`
- `requirements.txt`
- `pyproject.toml`
- deployment-specific Dockerfile/compose files

Exclude:

- local SQLite state unless explicitly migrated
- generated artifacts
- private connector credentials

Verification:

- `/health` and `/v1/health`
- auth fails closed outside local development
- documented app-to-backend smoke path

### 5. Agent Harness / CLI Operator Package

Purpose: local-first operator and AI-operator surface for coding agents, safe apply, web/search, benchmarks, and offline bundles.

Include:

- `scripts/scbe-system-cli.py`
- `scripts/agents/`
- `scripts/benchmark/`
- `config/offline_bundle_profiles.json`
- `config/distribution_package_map.json`
- `docs/ops/AGENT_BUS_USER_GUIDE.md`
- AI operator guides

Exclude:

- generated benchmark outputs unless attached as release evidence
- local browser profiles
- private API tokens

Verification:

- CLI help loads
- focused CLI tests pass
- offline bundle build/install smoke passes

### 6. Training and Evaluation Package

Purpose: reproducible training, benchmarks, model promotion gates, and eval harnesses.

Include:

- `config/model_training/`
- curated `training-data/` schemas and small public corpora
- `scripts/train*/`
- `scripts/system/geoseal_coding_training_system.py`
- `tests/training/`
- benchmark specs

Split:

- Public eval pack: schemas, benchmark tasks, small examples, provenance rules
- Internal training pack: Notion-derived corpora, proposal-sensitive records, run logs, private model notes

Verification:

- dataset schema validation
- small smoke training/eval command
- promotion gate report

### 7. Infrastructure Package

Purpose: deployment manifests and environment-specific ops.

Include:

- `.github/workflows/`
- `deploy/`
- `k8s/`
- `Dockerfile*`
- `docker-compose*.yml`
- `vercel.json`
- environment templates only

Exclude:

- real secrets
- machine-local service state
- cloud provider private exports

Verification:

- workflow path validation
- Docker/compose config check
- deploy target smoke when credentials exist

### 8. Private Doctrine Package

Purpose: preserve Notion, patent, business, and long-range R&D material without publishing it.

Canonical private location:

- `C:\Users\issda\SCBE-private`

Include:

- Notion doctrine indexes
- fetched full Notion pages
- patent/business pages
- storage cleanup ledgers
- sensitive proposal and evidence packets

Exclude from public repo:

- raw private Notion exports
- local path inventories
- patent claim drafts unless intentionally published
- personal/tax/business identity records

Verification:

- pushed to private GitHub repo
- public repo contains only sanitized summaries or pointers

## Guide Types

| Guide Type | Audience | Destination | Notes |
|---|---|---|---|
| User guide | End users / buyers | `docs/user-guides/` or public docs | How to use the product, no internals required |
| System guide | Maintainers / developers | `docs/specs/`, `docs/architecture/` | Architecture, contracts, APIs, package boundaries |
| AI operator guide | Codex, Cursor, Claude, local agents | `AGENTS.md`, `docs/ops/`, private handoffs | Exact commands, permissions, routing, safety rules |
| Deployment guide | Operators / DevOps | `docs/ops/`, `deploy/`, `k8s/` | Environment variables, service order, health checks |
| Training guide | Model/eval operators | `docs/training/`, `config/model_training/` | Data buckets, promotion gates, run logs |
| Business guide | Internal sales/proposal work | private repo by default | Avoid public claims drift |

## Cleanup Rules

- Do not delete unique local research or business files during package cleanup.
- Move raw private doctrine to `SCBE-private` before public packaging.
- Generated outputs are excluded by default and attached only as release evidence.
- Public packages should be reproducible from source, configs, and documented commands.
- Internal training packages may depend on private doctrine, but public eval packages must not.
- Package manifests must not include secrets, `.env` files, browser profiles, or local machine inventories.

## Current Useful Additions

1. Promote this package map into release planning.
2. Wire `config/distribution_package_map.json` into `scripts/scbe-system-cli.py offline build` after Cursor's active CLI work lands.
3. Add package-specific verification commands:
   - `verify:geoshell`
   - `verify:geoseal-agent`
   - `verify:backend-api`
   - `verify:training-eval`
   - `verify:distribution`
4. Build a private Notion export package from the live Notion connector and keep it out of public git.
