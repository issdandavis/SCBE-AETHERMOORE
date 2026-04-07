# Cymatic Nodal Trim Patterns: Full Mathematical Derivation (2D + 3D)

**Source**: Codex session 2026-04-03
**Status**: Canonical math reference for phi-acoustic router
**Version**: v0.4

---

## Core Equation (2D - existing vacuumAcoustics.ts)

N(x1, x2) = cos(n*pi*x1/L) * cos(m*pi*x2/L) - cos(m*pi*x1/L) * cos(n*pi*x2/L)

Nodes at N = 0. States settling here are stable low-energy equilibria.

## 3D Extension (for multi-agent family simulations)

N(x,y,z) = cos(n*pi*x/Lx) * cos(m*pi*y/Ly) * cos(p*pi*z/Lz)
          - cos(m*pi*x/Lx) * cos(p*pi*y/Ly) * cos(n*pi*z/Lz)

3D resonant frequency:
omega_nmp = c * pi * sqrt((n/Lx)^2 + (m/Ly)^2 + (p/Lz)^2)

## Full Trim Equation

support_i(t+1) = support_i(t) * exp(-(E_i + nu*D) / tau_phi) * 1_{|N_lattice(z)| < delta}

Where:
- E_i = Body/Mind/Spirit energy function with stakeholder costs
- D = Helmholtz/Sethares dissonance on FFT output
- tau_phi = phi-scaled decay constant
- delta = nodal proximity tolerance
- Only states at nodal convergence zones are trimmed

## Trim Pattern Labels
- Perfect fifth (3:2) = safe trim
- Major third (5:4) = convergent state
- Major seventh (7-limit) = stable personality
- Tritone = governance violation
- Bohlen-Pierce tritave consonance = multi-agent family harmony

## Implementation Integration
- audioAxis.ts → FFT projection
- vacuumAcoustics.ts → nodal surface check
- PhiAcousticRouter → convergence mask + trim labeling
- TuningSystem → pluggable (7-limit, Bohlen-Pierce, Pythagorean, 12-TET, phi-Fibonacci)

## Valuation Context (Grok analysis, April 2026)
- Current as-is: $75k-$175k
- 12-month projection (moderate traction): $2M-$8M
- Structure proposed: 15% upfront + 5% performance increments
- Key bottleneck: distribution, not tech (1 star → need outreach)
