# Cross-Stitch Lattice Bridge Formulas — First-Principles Derivation

## Per-Bridge Coherence

Bridge(i,j) = phi^|i-j| * cos(theta_ij) * (IR_i*IR_j + Vis_i*Vis_j + UV_i*UV_j)

## Total Lattice Coherence (Quorum Score)

LatticeCoherence = sum over all 15 pairs (i < j) of Bridge(i,j)

## Integration with Harmonic Cost

H_consent = pi^(phi * d*) * max(0, 1 - LatticeCoherence)

## Tongue Weights

- Kor'aelin (KO): phi^0 = 1.000
- Avali (AV): phi^1 = 1.618
- Runethic (RU): phi^2 = 2.618
- Cassisivadan (CA): phi^3 = 4.236
- Umbroth (UM): phi^4 = 6.854
- Draumric (DR): phi^5 = 11.090

## Key Properties

- 15 bridges form complete graph K_6
- Trichromatic dot product uses all 3 bands (IR/Visible/UV)
- Only Visible band observable to attacker
- phi^|i-j| weighting makes high-distance bridges dominant
- Torsion attacks collapse multiple cos(theta) terms simultaneously
- Honeypot: 0.01 deviation on UM amplifies to 0.069 via phi^4

Derived March 30, 2026. Validated against 73.5% blind detection results.
