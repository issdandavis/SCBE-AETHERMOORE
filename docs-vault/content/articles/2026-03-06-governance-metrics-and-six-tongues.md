# Governance Metrics and Six Tongues in Practical Routing

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## Framing

Six Tongues are not decorative labels. They are weighted routing signals used to score intent and collision risk across flows.

## Working metric model

- tongue weight baseline
- authority class
- intent similarity
- local density
- cyclic phase delta

Combined scores determine whether a packet stays in-lane, requests separator logic, or escalates to higher-governance review.

## Why weighted tongues help

Flat tags lose priority context. Tongue weighting keeps semantic differences explicit while still allowing deterministic math across routes.

## Implementation note

Lattice records preserve both raw vectors and metric tags so training and runtime can share the same decision surface.

## References

- `hydra/lattice25d_ops.py`
- `workflows/n8n/scbe_n8n_bridge.py`
