# AI Brain 21D State Conservation Spec - 2026-06-27

Source: Issac's 21D Brain State / Conservation Laws note from 2026-06-27 chat.

Status: canonical candidate, not yet reconciled with current `src/ai_brain/unified-state.ts` layout.

## Canonical candidate vector

`x_t in R^21`

| index | component | range | role |
|---:|---|---|---|
| 0-2 | Poincare position `u` | `||u|| < 1.0` | core thought position in hyperbolic space |
| 3-8 | six tongue phases | `{0,60,120,180,240,300}` degrees | KO/AV/RU/CA/UM/DR phase coherence |
| 9-11 | torus coordinates | `[0, 2pi)` | lattice / quasicrystal navigation |
| 12-14 | trust ring position | `[0.0,0.95]` | security tier / ring state |
| 15-17 | momentum vector `p` | real values | Hamiltonian conjugate momentum |
| 18 | energy `H` | `[0,H_max]` | energy balance / thought path budget |
| 19 | lattice phase `nu_lattice` | `[0,1]` | phason / projection parameter |
| 20 | dimensional flux `nu` | `[0,1]` | breathing state: Polly/Quasi/Demi |

## Conservation laws

1. Containment: `||u|| < 1.0`; correction clamps to safe radius such as `0.95`.
2. Tongue phase coherence: phases snap to the six sacred tongue angles.
3. Hamiltonian energy balance: energy drift is checked/corrected by symplectic logic.
4. Lattice path continuity: adjacent polyhedral path nodes must be connected or repaired with a bridge.
5. Flux normalization: `0 <= nu <= 1.0`; low flux enters emergency posture.

## Derived telemetry

- Dual ternary deltas: primary intent channel and perpendicular constraint channel.
- Mirror discord: normalized difference between parallel and perpendicular ternary channels.
- Multiscale spectral features: participation ratio, spectral entropy, top-3 eigenvalue ratio.
- Zero-gravity state: centered, phase-locked, no drift, full flux, low energy.

## Product interpretation

This should be treated as the canonical candidate for an inspectable AetherDesk brain state. It gives the UI direct widgets: 21D heatmap, Poincare sphere, phase wheel, mirror plot, spectral timeline, violation log, and flux mode.

## Important alignment issue

The current TypeScript `src/ai_brain/unified-state.ts` layout found in the repo appears to use a different 21D decomposition: SCBE context, navigation, cognitive, semantic, and swarm dimensions. That may be useful, but it is not the same vector as this conservation-law spec.

Before public release, choose one of these:

1. Make this conservation-law vector canonical and adapt TypeScript to it.
2. Keep the existing product vector canonical and map this conservation-law vector as a derived diagnostic projection.
3. Support both explicitly with names like `BrainState21Product` and `BrainState21Conservation`, with a tested conversion layer.

Recommendation: option 3 first, then decide later. It avoids breaking current code while preserving the stronger conservation-law semantics.
