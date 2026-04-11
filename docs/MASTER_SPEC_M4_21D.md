---
id: SPEC001
references: [HARMONIC001, AXIOMS001, PHDM001]
feeds_into: [TOKENIZER001, TRAINING001]
version_sync: "3.3.0"
mind_map_node: "CoreModules"
state_dims: 21
---

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

## Connections

```yaml
connections:
  id: master-specification-canonical-twenty-one-dimensional-state
  module: canonical-brain-state
  state_dimensions: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
  related:
    - polyhedral-hamiltonian-dynamic-mesh-brain-architecture
    - sacred-tongue-tokenizer-practical-tutorials-and-use-cases
  tests: []
  knowledge_spine_paths:
    - docs/00_MASTER/INDEX.csv
    - docs/00_MASTER/BRAIN_STATE_TWENTY_ONE.schema.json
    - docs/00_MASTER/MINDMAP.mmd
```
