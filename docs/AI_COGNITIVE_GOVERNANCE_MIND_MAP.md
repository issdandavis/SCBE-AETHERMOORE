# AI Cognitive Governance Mind Map

Geometric AI alignment through topological constraints, not fixed business rules.

## 1) Canvas: Poincaré Ball Embedding
- The mind lives in a Poincaré ball.
- Boundary cost approaches infinity (adversarial or unstable trajectories become expensive).
- Distance:
  - `d_H = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))`
- Center = aligned intent, edge = highest-risk region.

Reference: `src/ai_brain/unified-state.ts` (Poincaré embedding) and `agents/browser/phdm_brain.py`.

## 2) Nodes: 16-Shape Polyhedral Lattice (PHDM)
- Platonic solids = fundamental truths.
- Archimedean solids = complex reasoning transitions.
- Kepler-Poinsot/Toroidal = abstract or high-risk transitions.
- Quasicrystal ordering = periodicity is avoided while preserving structure.

Reference: `src/harmonic/phdm.ts` and `src/harmonic/phdm_module.py` compatibility shim.

## 3) Connections: Six Sacred Tongues
### Tongue map
- KO (Korah): weight `1.00`, phase `0°`
- AV (Aelin): weight `2.31`, phase `60°`
- RU (Runis): weight `3.77`, phase `120°`
- CA (Caelis): weight `5.44`, phase `180°`
- UM (Umbral): weight `7.68`, phase `240°`
- DR (Draumric): weight `11.09`, phase `300°`

Reference: `src/crypto/sacred_tongues.py` and `src/symphonic_cipher/scbe_aethermoore/sacred_tongues.py`.

## 4) Fluxing Dimensions (Attention Mechanism)
- POLLY / FULL: `ν ≈ 1.0`
- QUASI: `0.5 < ν < 1.0`
- DEMI: `ν < 0.5`
- `ν` is used operationally as dynamic containment posture and attention gating.

Reference: `agents/browser/phdm_brain.py` and `src/harmonic/phdm.ts` flux families.

## 5) Voice: Harmonic Frequency Channel
- Map conlang token IDs to frequencies.
- Frequency formula:
  - `f = f0 + v_i' * Δf`
  - `f0 = 440 Hz`, `Δf = 30 Hz`
- FFT / spectral checks can be used as a governance signal.

Reference: `src/crypto/sacred_tongues.py` (harmonic fingerprints) and `src/crypto/pqc.ts`.

## Invisible Wall as Governance Primitive
Selective dimensional permeability is expressed as a containment manifold:
- A wall can exist in one dimension while absent in another.
- In practical terms, the same actor can be blocked under one tongue/axis/state and permitted under another if geometry allows.

This is implementation-ready behavior, not a hardcoded rule list.

Reference concept: use PHDM decision surfaces (`agents/browser/phdm_brain.py` + `src/harmonic/phdm.ts`) and action classifiers.

## 54-Face State Model (3 × 3 × 6)
- Valence (`+1`, `0`, `-1`)
- Spatial manifold (`x, y, z` within Poincaré ball)
- Sacred Tongue (`KO`, `AV`, `RU`, `CA`, `UM`, `DR`)
- Total faces: `3 × 3 × 6 = 54`

## Fit-to-Current System
The map aligns with existing implementation in:
- `src/harmonic/phdm.ts` (Layer 8 manifold + flux + Hamiltonian path)
- `src/crypto/sacred_tongues.py` (Layer 1-2 encoding primitives)
- `agents/browser/phdm_brain.py` + `agents/browser/action_validator.py` (runtime governance bridge)
- `src/pqc.ts` and `src/scbe_aethermoore_kyber_v2.1.py` (Layer 13 post-quantum hooks)

## Notes for tomorrow
1. Treat this document as the canonical governance model artifact for training data ingestion.
2. Keep implementation truth in code references above; treat prose as intent, not runtime exceptions.
3. Wire action and context traces into audit envelopes as structured data (`decision`, `deviation`, `risk_score`, tongue/phase) for closed-loop tuning.
