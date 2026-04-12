---
id: AXIOMS001
references: [SPEC001, PHDM001]
feeds_into: [HARMONIC001, AXIOMS001]
governs_layers: [L1, L2, L3, L4, L5, L7, L8, L9, L10, L11, L12, L13, L14]
version_sync: "3.3.0"
mind_map_node: "CoreModules > Governance"
state_dims: 5
---

# Core Axioms Canonical Index

Last updated: February 19, 2026
Purpose: single pointer map to where axioms actually live in code/tests/docs.

## Canonical Source of Truth
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/__init__.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/SPECIFICATION.md`
- `src/symphonic_cipher/scbe_aethermoore/qasi_core.py`
- `src/symphonic_cipher/tests/test_axiom_verification.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/tests/test_axiom_grouped.py`

## Reference Documentation
- `docs/TECHNICAL_REFERENCE.md`
- `config/scbe_core_axioms_v1.yaml` (bridge/index packaging file, not canonical formula source)

## Quantum Axiom Mesh
- Unitarity: Layers 2,4,7
- Locality: Layers 3,8
- Causality: Layers 6,11,13
- Symmetry: Layers 5,9,10,12
- Composition: Layers 1,14

## Rule
If any packaging file disagrees with canonical source modules, canonical source modules win.
