# SCBE-AETHERMOORE Repo Surface Map

**Last Updated:** 2026-04-08

## Purpose

This file is the practical map for operating the repository as a solo builder.

Use it to answer:

- where the live system actually is
- which lane to open first
- which areas are noisy, generated, or archival
- what should be cleaned before any repo split

## What This Repo Is

This is a hybrid monorepo with four real system lanes living together:

1. governance core
2. product / MVP runtime
3. operator workflows
4. research and training accumulation

That is why the repo feels bigger than a normal app repo. It is currently doing too many jobs in one place.

## Open These First

If you do not know where to start, use this order:

1. `CANONICAL_SYSTEM_STATE.md`
2. `README.md`
3. `package.json`
4. `src/api/main.py`
5. `api/main.py`
6. `scripts/`

## Active Lanes

### 1. Governance Core

Use this lane when the task is about the 14-layer system, formula behavior, crypto, harmonic logic, or npm package exports.

- `src/index.ts`
- `src/harmonic/`
- `src/crypto/`
- `src/governance/`
- `src/tokenizer/`
- `docs/specs/CANONICAL_FORMULA_REGISTRY.md`

### 2. Product / MVP Runtime

Use this lane when the task is about running a user-facing API, SaaS behavior, search, HYDRA, memory sealing, or newer runtime additions.

- `src/api/main.py` — newer MVP / control-plane lane
- `src/api/search_routes.py`
- `src/api/llm_routes.py`
- `src/api/stripe_billing.py`

### 3. Governance API

Use this lane when the task is about authorization, audit, persistence, agent registration, billing-adjacent governance, or the older stable `/v1/*` surface.

- `api/main.py`
- `api/persistence.py`
- `api/metering.py`

### 4. Operator Surface

Use this lane when the task is about how the system is actually driven locally.

- `scripts/hydra_command_center.ps1`
- `scripts/hydra.ps1`
- `scripts/scbe_terminal_ops.py`
- `scripts/scbe_docker_status.ps1`
- `scripts/scbe_mcp_terminal.ps1`

### 5. Federal Funding / Proposal Surface

Use this lane when the task is about DARPA, SAM.gov, APEX, grant/proposal readiness, submission contacts, or federal go/no-go decisions.

- `docs/operations/DARPA_SAM_GOV_CONTACTS_AND_PROPOSAL_STATUS.md`
- `notes/DARPA_CLARA_Proposal_Master.md`
- `docs/proposals/DARPA_CLARA/`
- `docs/research/DARPA_AI_SECURITY_PROGRAMS_2026.md`
- `docs/research/FUNDING_OPPORTUNITIES_2026.md`

### 6. Document Management Surface

Use this lane when the task is about document authority, note consolidation, repo drift cleanup, or deciding whether a file is canonical, operational, public, exploratory, historical, or generated.

- `docs/operations/DOCUMENT_MANAGEMENT_OPERATING_MODEL.md`
- `docs/operations/REPO_CLEANUP_INVENTORY.md`
- `CANONICAL_SYSTEM_STATE.md`
- `REPO_SURFACE_MAP.md`
- `skills/scbe-document-management/SKILL.md`

## Generated / Noisy Zones

Do not treat these as the main codebase unless the task is explicitly about them.

### Generated outputs

- `dist/`
- `build/`
- `output/`
- `artifacts/`
- `exports/`
- `docs-build-smoke/`

### Training / corpora accumulation

- `training-data/`
- `training/`
- `training-runs/`
- `models/`
- `my-local-model/`

### Local-state / machine-noise

- `node_modules/`
- `.cache/`
- `.pytest_cache/`
- `.hypothesis/`
- `.benchmarks/`
- `.npm-cache/`
- `sealed_blobs/`

### Notes and research accumulation

- `notes/`
- `notebooks/`
- `paper/`
- `references/`
- `articles/`

These are useful, but they should not define the runtime story.

## Quarantine Candidates

These are the first areas that should stop affecting the main repo narrative:

### Candidate A — Generated evidence and outputs

- `artifacts/`
- `dist/`
- `build/`
- `output/`
- `docs-build-smoke/`

### Candidate B — Training accumulation

- `training-data/`
- `training/`
- `training-runs/`
- `models/`

### Candidate C — Research and notes overflow

- `notes/`
- `notebooks/`
- `paper/`
- `references/`

Quarantine here means:

- keep them in the repo for now
- stop treating them as primary
- eventually move or archive them only after the runtime surface is stable

## Safe Cleanup Order

Do this in order.

### Step 1

Protect the live story:

- canonical formula
- current status language
- runtime split

This is already underway.

### Step 2

Protect the main entrypoints:

- `README.md`
- `CANONICAL_SYSTEM_STATE.md`
- `REPO_SURFACE_MAP.md`
- `REPO_BOUNDARY_PLAN.md`

### Step 3

Mark generated and training-heavy directories as non-primary in docs and release workflows.

### Step 4

Decide which of these should be ignored, archived, mirrored, or extracted later.

Do **not** start with repo splitting.

## Commands To Use Next

### TypeScript package lane

```powershell
npm run build
npm run typecheck
npm test
```

### Newer product / control-plane lane

```powershell
python -m uvicorn src.api.main:app --reload --port 8000
```

### Older governance API lane

```powershell
python -m uvicorn api.main:app --reload --port 8080
```

### Quick orientation

```powershell
Get-ChildItem -Name
Get-ChildItem -Name src
Get-ChildItem -Name scripts
Get-Content -Head 120 package.json
```

## Practical Rule

When the repo feels too large:

- stay in `src/`, `api/`, and `scripts/`
- treat everything else as support material unless proven otherwise

That rule alone removes most of the confusion.
