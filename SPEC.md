# SCBE Specification (Canonical)

This file is the canonical specification entrypoint for SCBE.

## Scope
SCBE (Spectral Context Bound Encryption) defines deterministic transcript handling, governance-gated execution policy, and integrity boundaries for model-assisted systems.

## Normative references
- `CONCEPTS.md` for implementation-aligned term definitions.
- `docs/core-theorems/SACRED_EGGS_GENESIS_BOOTSTRAP_AUTHORIZATION.md` for genesis/bootstrap authorization theorems.
- release-tagged code and tests for executable behavior.

## Authority
Only materials explicitly linked from this file are authoritative.
All files under `experimental/` are non-authoritative and provided for research/reference only.

## Versioning
Canonical spec updates must be released with a version tag and changelog entry.


## Canonical Documentation Index

The following documents establish authoritative specifications. All other materials
are experimental or aspirational until linked here.

- **14-Layer Pipeline**: `LAYER_INDEX.md` -> `packages/kernel/src/pipeline14.ts` (TS canonical), `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py` (Python reference)
- **HYDRA Swarm Governance**: `docs/HYDRA_SPEC.md` -> `hydra/` modules + `docs/hydra_index.json`
- **Flux State / Breathing / Phase-Lock**: `packages/kernel/src/fluxState.ts`
- **Aether Browser**: `docs/AETHER_BROWSER.md` -> `hydra/swarm_browser.py` + `hydra/browsers.py`

## Canonical theorem surfaces
- `docs/core-theorems/SACRED_EGGS_GENESIS_BOOTSTRAP_AUTHORIZATION.md`
