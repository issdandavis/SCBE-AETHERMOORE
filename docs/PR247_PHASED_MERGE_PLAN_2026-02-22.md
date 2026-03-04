# PR #247 Phased Merge Plan (Conflict-Safe)

PR: `issdandavis/SCBE-AETHERMOORE#247`  
Current status: `OPEN`, `CONFLICTING`

## Objective
Merge feature work without dragging generated noise or unstable cross-cut changes into `main`.

## Phase Order

### Phase 1 — Stability + Ops
Cherry-pick:
- `db9a0617` `fix(physics): ...`
- `18b1acca` `chore(docker): ...`
- `6ad27e1c` `feat(training): split SFT tracks ...`
- `3a10dbbb` `docs(repo): AGENTS + nightly handoff`
- `e279bb2d` `docs(plan): access audit + roadmap`

Gate:
- `pytest tests/test_physics_bug_regressions.py tests/test_state21_product_metric.py -q`
- `npm run mcp:doctor`

### Phase 2 — Code Prism Foundation
Cherry-pick:
- `8a1ce7d5` `feat(code-prism): scaffold IR-based polyglot builder with tests`

Gate:
- `pytest tests/code_prism/test_matrix.py tests/code_prism/test_builder.py -q`
- `python scripts/code_prism_build.py --input artifacts/code_prism/sample_input.py --source-lang python --targets typescript go --module-name sample_math --out-dir artifacts/code_prism`

### Phase 3 — Large Experimental Feature Batch
Deferred from fast merge path:
- `d3370278`, `7593a500`, plus broad generated artifacts and training blobs.

Gate:
- split into dedicated PR(s) by domain (`mcp`, `training-data`, `visual-system`, `concept-blocks`)
- require CI green before merge.

## Conflict Handling
1. Create phase branches from `main` (`phase1-pr247`, `phase2-pr247`).
2. Cherry-pick only scoped commits.
3. Resolve conflicts in favor of `main` for workflows unless change is required and tested.
4. Open separate PR per phase to keep rollback and review clean.

