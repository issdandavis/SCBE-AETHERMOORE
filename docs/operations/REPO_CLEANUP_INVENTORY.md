# Repo Cleanup Inventory

Last updated: 2026-04-08
Status: solo-operator cleanup inventory for keeping the main repo usable without splitting repos yet

## Purpose

This file is the practical cleanup sheet for the current repo.

It answers:

- what stays in the main working surface
- what should be quarantined from the main story
- what should be treated as storage or generated output
- what should be left alone until after proposal work is done

## Current Reality

The worktree contains four different things mixed together:

1. live runtime and package code
2. active docs and proposal material
3. research and future branches
4. storage / generated outputs / machine-local noise

The immediate goal is not to delete everything.

The immediate goal is to stop low-value files from competing with the live system.

## Keep In Main Working Surface

These should stay visible and easy to find:

### Runtime and code

- `src/`
- `api/`
- `python/`
- `agents/`
- `scripts/`
- `tests/`
- `package.json`
- `pyproject.toml`

### Canonical and operational docs

- `CANONICAL_SYSTEM_STATE.md`
- `REPO_SURFACE_MAP.md`
- `REPO_BOUNDARY_PLAN.md`
- `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
- `docs/operations/DOCUMENT_MANAGEMENT_OPERATING_MODEL.md`
- `docs/operations/DARPA_SAM_GOV_CONTACTS_AND_PROPOSAL_STATUS.md`

### Proposal lane

- `docs/proposals/DARPA_CLARA/`
- `notes/DARPA_CLARA_Proposal_Master.md`

## Quarantine From Main Narrative

These are not necessarily bad, but they should stop defining the repo surface:

### Research / future branch

- `notes/`
- `notebooks/`
- `paper/`
- `references/`
- `experimental/`
- `experiments/`
- `phdm-21d-embedding/`
- `physics_sim/`

### Product side projects / secondary apps

- `ai-ide/`
- `conference-app/`
- `kindle-app/`
- `scbe-visual-system/`
- `aether-browser/`
- `aetherbrowse/`

These can stay in the repo for now, but should not be treated as the default entrypoint.

## Treat As Storage / Generated / Local Noise

These should be ignored, quarantined, or treated as gated-channel paths:

- `artifacts/`
- `dist/`
- `build/`
- `output/`
- `exports/`
- `training-runs/`
- `models/`
- `my-local-model/`
- `node_modules/`
- `.cache/`
- `.codex_tmp/`
- `.pytest_cache/`
- `.hypothesis/`
- `.playwright-mcp/`
- `.tmp-build/`
- `backups/`
- `_staging/`

## Proposal-Safe Cleanup Rule

Until the DARPA proposal lane is submitted or paused:

- do not do major repo surgery
- do not split repos
- do not rewrite large research areas
- do not delete historical material unless it is clearly generated noise

Only do:

- authority cleanup
- ignore-rule cleanup
- startup-map cleanup
- generated/noise quarantine

## Immediate Cleanup Actions

### Phase A — Safe now

- extend `.gitignore` for obvious local noise and generated paths
- keep canonical and proposal docs easy to find
- stop screenshot dumps and model-weight lanes from polluting git status

### Phase B — Safe after proposal submission

- move side projects behind a clearer boundary
- demote stale public docs to legacy
- archive overflow notes into a predictable archive path

### Phase C — Later

- extract stable boundaries into separate repos only if they are already clean in practice

## Working Rule

If a path helps:

- run the system,
- explain the current system,
- or submit the proposal,

keep it visible.

If a path mostly stores:

- outputs,
- screenshots,
- local model material,
- browser/session residue,
- or generated corpora,

move it out of the main mental model immediately.
