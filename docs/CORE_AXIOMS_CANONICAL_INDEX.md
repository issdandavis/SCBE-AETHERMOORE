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
