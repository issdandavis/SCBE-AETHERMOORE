# Change Notes: Spiral Engine + Five-Lock Gate

Date: 2026-02-20  
Scope: Aethermoor Spiral Engine gameplay/runtime utility improvements

## Summary

This update turns the SCBE formula chain into explicit, inspectable game/runtime mechanics:

- Three Watchers rings are now first-class runtime signals.
- Triadic risk is computed with the canonical weighted-phi formula.
- Final gate remains explicit as a 5-factor Omega product.
- Harmonic wall output now drives a friction/latency multiplier.
- Coherence-shaped voxel discovery and terrain classification are live.
- A standalone CLI diagnostic now reports weakest lock and remediation.

## Added

- `scripts/omega_lock_diagnostic.py`
  - Single-command five-lock diagnostics.
  - Returns lock vector, Omega decision, permission color, and actionable recommendation.

- `tests/test_temporal_lock_diagnostic.py`
  - Validates lock behavior and permission color banding.

## Updated

- `src/spiralverse/temporal_intent.py`
  - Added `OmegaLockVector`.
  - Added `compute_lock_vector(...)`.
  - Preserved backward compatibility for `compute_omega(...)`.
  - Added lock vector into `get_status(...)`.

- `src/spiralverse/aethermoor_spiral_engine.py`
  - Added voxel cell model and deterministic coherence-shaped voxel discovery.
  - Added three watcher ring signals:
    - `I_fast`
    - `I_memory`
    - `I_governance`
  - Added `d_tri = (Σ λ_i * I_i^phi)^(1/phi)` runtime calculation.
  - Added explicit turn-level `omega_factors` output.
  - Added turn fields for:
    - friction/latency
    - permission color
    - weakest lock
    - watcher signals and triadic components

- `tests/test_aethermoor_spiral_engine.py`
  - Expanded checks for watcher ranges, triadic consistency, voxel outputs.
  - Added deterministic assertions for watcher and omega factor projections.

- `docs/research/AETHERMOOR_SPIRAL_ENGINE_MVP.md`
  - Added formula-to-mechanic mapping.
  - Added watcher ring/triadic blend description.
  - Added five-lock diagnostic usage.

## Validation

Executed:

- `python -m pytest -q tests/test_aethermoor_spiral_engine.py tests/test_temporal_lock_diagnostic.py`

Result:

- `8 passed`

