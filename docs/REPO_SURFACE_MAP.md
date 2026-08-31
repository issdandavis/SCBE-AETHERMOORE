# SCBE-AETHERMOORE Repo Surface Map

**Last Updated:** 2026-08-26

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

1. `START_HERE.md`
2. `README.md`
3. `docs/PRODUCT_QUICKSTART.md`
4. `docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md`
5. `CANONICAL_SYSTEM_STATE.md`
6. `package.json`
7. `scripts/system/start_aetherbrowser_extension_service.mjs`
8. `scripts/verify_aetherbrowser_extension_service.py`
9. `src/api/main.py`
10. `api/main.py`

## Product surface classification

| Class | Current contents | Operator rule |
|---|---|---|
| Active product | AetherBrowser (`src/aetherbrowser/`, `src/extension/`) and AetherDesk (`aetherdesk/`) | Start here; release through `npm run product:release-gate` |
| Shared platform | governance, crypto, tokenizer, Python/TypeScript package and API layers | Product dependencies, not competing apps |
| Experimental | research, eval, proposal, and exploratory operator lanes | Opt-in; do not place in first-run instructions |
| Archived/noisy | generated artifacts, corpora, models, notebooks, caches, historical captures | Preserve as needed, but keep out of the product path |

The active app is a shared human+AI workspace, not every executable in the
monorepo. Its layout and authority boundaries are defined in
`docs/product/AETHER_WORKSPACE_ARCHITECTURE.md`.

## Active Lanes

### 1. Governance Core

Use this lane when the task is about the 14-layer system, formula behavior, crypto, harmonic logic, or npm package exports.

- `src/index.ts`
- `src/harmonic/`
- `src/crypto/`
- `src/governance/`
- `src/tokenizer/`
- `docs/specs/SCBE_CANONICAL_CONSTANTS.md`

### Evidence Surface

Use this lane when the task is about sealed-blind proof points, reviewer-facing empirical claims, or the shortest path to the current 24/24 result.

- `docs/evidence/EVIDENCE_24_24.md`
- `docs/specs/SCBE_TECHNICAL_PACKET_v1.md`
- `artifacts/collab/dava_blind_v1/RESULT.md`
- `artifacts/collab/dava_blind_v1/permutation_test_report.json`
- `artifacts/collab/dava_blind_v1/kl_capacity_ci_report.json`

### 2. Active Product — AetherBrowser + AetherDesk

Use this lane for the installable local-first workspace.

- `src/aetherbrowser/` — browser, agent, and model-provider runtime
- `src/extension/` — managed browser surface
- `aetherdesk/` — operator UI, allowlisted tools, provider status, and receipts
- `scripts/system/product_surface_release_gate.py` — start/verify/receipt release proof
- `docs/PRODUCT_QUICKSTART.md` — supported install and run story
- `docs/product/AETHER_WORKSPACE_ARCHITECTURE.md` — UI and authority map

The newer APIs under `src/api/` and stable governance APIs under `api/` are
shared platform surfaces. They are not alternate first-run products.

### Product-First Monorepo Boundary

Use this lane when the task is about making the repository clone experience clearer, reducing root confusion, or deciding what belongs in product, platform, research, or archive.

- `docs/PRODUCT_QUICKSTART.md`
- `docs/specs/MONOREPO_CONSOLIDATION_AUTHORITY.md`
- `config/repo_consolidation_inventory.json`
- `README.md`
- `START_HERE.md`

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

Use this lane when the task is about DARPA, SAM.gov, DIBBS, DLA supplier access, APEX, grant/proposal readiness, submission contacts, or federal go/no-go decisions.

- `docs/ops/DIBBS_DLA_OPERATING_MODEL.md`
- `docs/ops/DIBBS_REGISTRATION_AND_FOLLOW_UP.md`
- `docs/business/DIBBS_MONETIZATION_MAP.md`
- `docs/legal/SAM_GOV_REGISTRATION_RECORD.md`
- `notes/federal/DARPA_CLARA_Proposal_Master.md`
- `docs/proposals/DARPA_CLARA/`
- `docs/proposals/DARPA_MATHBAC/sam_gov_attachments/`
- `docs/proposals/DARPA_MATHBAC/proposers_day_playbook.md`

### 6. Document Management Surface

Use this lane when the task is about document authority, note consolidation, repo drift cleanup, or deciding whether a file is canonical, operational, public, exploratory, historical, or generated.

- `START_HERE.md`
- `CANONICAL_SYSTEM_STATE.md`
- `docs/README_INDEX.md`
- `docs/archive/cleanup_notes.md`
- `docs/REPO_SURFACE_MAP.md`
- `docs/ops/DOCUMENT_MANAGEMENT_OPERATING_MODEL.md`
- `skills/scbe-document-management/SKILL.md`

### 7. Internal Agent Coordination Surface

Use this lane when the task is about internal-only agent updates, non-secret handoff notes, back-of-house website changes, or guardrails meant for future agents rather than operators.

- `.agents/back_of_house/README.md`
- `.agents/back_of_house/AGENT_CHANGE_LOG.md`
- `.agents/back_of_house/updates.jsonl`
- `.agents/plugins/plugins/aetherbrowse/skills/scbe-ops-manager/references/cross-talk-packet-templates.md`

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

### Product quickstart

```powershell
npm install
npm run product:release-gate
```

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
