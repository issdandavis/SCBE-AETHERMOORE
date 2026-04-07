# Phi-Acoustic Router Specification

**Source**: Codex session 2026-04-03
**Status**: Architecture spec v0.2 — extends L14 audio axis
**Depends on**: PHDM, personality scaffold, audioAxis.ts, vacuumAcoustics.ts

## Core Concept

Layer the personality scaffold onto L14's existing audio axis infrastructure. Personality states settle at acoustic convergence zones (standing wave nodes). Dissonance = high energy = automatic pruning. Consonance = harmonic attunement = stable personality.

## Key Formulas

### Harmonic Wave Propagation
```
psi_ij(t) = A * sin(2*pi*f_phi*t + phi_phase) * exp(-gamma*t)
```
Where f_phi = golden-ratio-scaled frequency, gamma = stakeholder-cost-governed damping.

### Acoustic Energy Function
```
E_phi_acoustic(z, u | p) = E_cross_lattice(z, u | p) + nu * D(F(psi_dual(z)))
```
Where F = Fourier transform, D = musical dissonance metric (Helmholtz/Sethares).

### Harmonic-Attuned Support Decay
```
support_i(t+1) = support_i(t) * exp(-(E_i + D_i) / tau_phi) * 1_{convergence_zone}
```
Only trim in convergence zones. Fully auditable via spectrograms.

## Tuning Systems (Pluggable)

| System | Best For | SCBE Use |
|---|---|---|
| Just 5-limit | Pure thirds, human warmth | Relational dialogues (Izack-Polly arcs) |
| Pythagorean | Stacked fifths, self-similar | Default phi-lattice |
| 12-TET | Library compatibility | Baseline comparison |
| Phi-Fibonacci | Maximum self-similarity | Strongest inductive bias |
| 7-limit Just | Extended harmonics | Richer convergence zones |
| Bohlen-Pierce | Non-octave (tritave 3:1) | Finer personality gradations |
| Adaptive | Dynamic epsilon per cost | Governance-audible |

## L14 Integration Points

- `audioAxis.ts` → Add phi-scaled frequency ratios to FFT analysis
- `vacuumAcoustics.ts` → Personality states settle at cymatic nodal lines
- `AudioAxisProcessor.computeDFT()` → Feed output to dissonance detector
- `nodalSurface()` → Personality equilibrium = standing wave zeros

## Trim Pattern Verification

Musical chords as trim signatures:
- Perfect fifth (3:2) = safe trim
- Major third (5:4) = convergent state
- Tritone (dissonant) = governance violation
- Every trim exports spectrogram + chord label

## Ablation Variants

| # | Variant | Tests |
|---|---|---|
| 11 | Phi-lattice only (no acoustic) | Is wave propagation enough? |
| 12 | Acoustic dissonance only (flat lattice) | Is dissonance detection enough? |
| 13 | Full phi-acoustic ternary-dual | Combined effect |
| 14 | Pythagorean tuning | Comma accumulation effect |
| 15 | Just 5-limit tuning | Purity vs symmetry |
| 16 | 12-TET tuning | Baseline temperament |
| 17 | Phi-Fibonacci tuning | Maximum self-similarity |
| 18 | Adaptive tuning | Dynamic governance |
