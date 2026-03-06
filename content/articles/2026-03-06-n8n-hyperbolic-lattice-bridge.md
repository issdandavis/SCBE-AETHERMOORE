# Wiring HyperbolicLattice25D into n8n

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## Summary

`/v1/workflow/lattice25d` is now callable from the n8n bridge, so lane jobs can submit notes, run lattice placement, and retrieve ranked neighbors in one route.

## Route contract

- `notes`: array of note records
- `include_repo_notes`: optional markdown ingestion
- `query_x`, `query_y`, `query_phase`: query anchor
- `query_top_k`: nearest neighbors to return

## Why this is useful

This route turns document ingestion into a live geometry surface. n8n pipelines can branch on lattice density, drift distance, or semantic overlap and route tasks to different model lanes.

## Security posture

- API key gate enforced
- bounded note counts and query parameters
- deterministic response payload shape for downstream validators

## References

- `workflows/n8n/scbe_n8n_bridge.py`
- `tests/test_scbe_n8n_bridge_security.py`
