# MASTER SPEC: M4 in Canonical 21D State

## Updated 21D Allocation
- dims 1-3: SCBE context
- dims 4-6: Dual-Lattice perpendicular space
- dims 7-9: PHDM cognitive position
- dims 10-12: Sacred Tongues phase
- dims 13-15: M4 model position (x,y,z)
- dims 16-18: Swarm composite node state
- dims 19-21: HYDRA ordering/meta

## M4 Contract
### Read
- 13-15 model position
- 4-6 perpendicular lift space
- 16-18 swarm/composite state
- 1-3 trust context

### Write
- 13-15 updated model position
- 16-18 composite registry payload

## Invariants
1. Poincare bound: ||m|| < 1
2. Harmonic wall: E = phi^(d_perp^2) < threshold
3. Trust inheritance: composite trust <= min(parent trust)
4. Negative space rule: midpoint ternary region cannot be -1
5. Determinism: same inputs -> same decision

## Pipeline Position
M4 runs after Spiralverse and before Swarm.

## Event Types
- M4_CompositionRequest
- M4_CompositionApproved
- M4_CompositionDenied
- M4_CompositeRegistered

## Reference Implementation
- `prototype/polly_eggs/src/polly_eggs/state21.py`
