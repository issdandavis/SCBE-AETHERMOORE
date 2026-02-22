# Nightly Change Notes — 2026-02-21

## What Was Finished Tonight

### 1) Contributor Operating Guide
- Added `AGENTS.md` at repo root.
- Captures practical standards for contributors and agents:
  - project layout,
  - build/test commands,
  - style conventions,
  - testing expectations,
  - commit/PR rules,
  - security and local ops guidance.

### 2) Training Pipeline Hardening (already landed on branch)
- Added explicit training track separation: `system`, `governance`, `functions`.
- Added legacy-source controls:
  - `legacy_docstring` tagging,
  - `quality.validated` metadata,
  - merge-time quota gate via `--legacy-max-ratio`.
- Added split output datasets:
  - `training-data/sft_system.jsonl`
  - `training-data/sft_governance.jsonl`
  - `training-data/sft_functions.jsonl`

### 3) Terminal-First Runtime Operations (already landed on branch)
- Docker stack operator script in place: `scripts/scbe_docker_status.ps1`.
- Docker MCP operator script in place: `scripts/scbe_mcp_terminal.ps1`.
- Added npm aliases for Docker and MCP terminal workflows.

## Verification Evidence
- Targeted regressions: physics + metric tests passed (`9 passed`).
- Dataset merge run completed successfully with split-track outputs.
- MCP doctor check succeeded: Docker MCP reachable, servers visible, tools enumerated.

## Current Constraints / Risks
- Branch has heavy unrelated WIP and generated artifacts in working tree.
- Merge should remain scoped to intentional files to avoid accidental repo noise.
- Training corpora are growing quickly; schema and provenance discipline must stay strict.

## Forward Steps Toward Goals

### Immediate (next session)
1. Open PR scoped to intentional commits only (docker ops + training split + AGENTS).
2. Add CI job to validate `track`, `source_type`, and `quality` metadata in training JSONL.
3. Add pre-commit ignore/policy for generated directories (`artifacts/pytest_tmp`, local DBs).

### Short Term (this week)
1. Build a single “nightly wave” command that executes:
   - conversion,
   - merge,
   - split,
   - validation,
   - optional upload.
2. Add dashboard counters for track mix and legacy ratio drift.
3. Lock a canonical branch strategy (`main` stable, `feat/*` isolated).

### Strategic (toward full system)
1. Complete system partitioning by responsibility:
   - `system` (core math/runtime),
   - `governance` (policy/decision control),
   - `functions` (tools/connectors/workflows).
2. Enforce interface contracts between partitions.
3. Promote only partition-validated artifacts to production channels.
