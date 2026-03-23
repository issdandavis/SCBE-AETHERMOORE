# 14-Layer Architecture

> Canonical reference math surface: `src/scbe_14layer_reference.py`

This note replaces older mixed layer maps that drifted across browser, swarm, crypto, and lore abstractions.

## Current canonical reference pipeline

| Layer | Name | Purpose |
|-------|------|---------|
| L1 | Complex State | build complex-valued state |
| L2 | Realification | map complex state into real coordinates |
| L3 | Weighted Transform | apply SPD / golden-ratio weighting |
| L4 | Poincare Embedding | place state inside the bounded hyperbolic ball |
| L5 | Hyperbolic Distance | measure geometric drift |
| L6 | Breathing Transform | bounded radial rescaling |
| L7 | Phase Transform | Moebius/phase isometry layer |
| L8 | Realm Distance | nearest trusted center / well proximity |
| L9 | Spectral Coherence | signal stability check |
| L10 | Spin Coherence | phase alignment / resonance check |
| L11 | Triadic Temporal Distance | recent + mid + global temporal aggregation |
| L12 | Harmonic Scaling / Score | bounded Layer 12 score in the reference pipeline |
| L13 | Risk Decision | ALLOW / QUARANTINE / DENY |
| L14 | Audio Axis | waveform-level telemetry |

## Critical Layer 12 split

Two Layer 12 traditions coexist in the repo.
Do not treat them as the same theorem target.

### Reference pipeline score

In `src/scbe_14layer_reference.py`:

`H_score = 1 / (1 + d + 2*phase_deviation)`

Properties:

- bounded
- monotone
- range `(0, 1]`
- used directly by the current reference pipeline risk decision path

### Legacy wall law

In modules such as `src/symphonic_cipher/qasi_core.py` and other theorem/patent-aligned surfaces:

`H(d,R) = R^(d^2)`

Properties:

- superexponential
- legacy theorem and patent language still points here
- still valid as a separate family of modules and tests

## What changed on 2026-03-17

The repo now documents and tests this split explicitly instead of pretending one Layer 12 formula replaced every other implementation.

Useful verification files:

- `tests/industry_standard/test_theoretical_axioms.py`
- `tests/industry_standard/test_formal_axioms_reference.py`
- `docs/AXIOM_CROSS_REFERENCE.md`

## Operational overlays that wrap the 14 layers

These are not new layers. They are product/ops surfaces built on top of the stack:

- AetherBrowser browser mesh
- cross-talk relay and goal-race packets
- phone/tablet device shell
- audio gate spectrum reporting
- training and publishing loops

## Practical reading rule

When you need clean math, start from `src/scbe_14layer_reference.py`.
When you need theorem history, patent language, or older wall-law behavior, follow the legacy harmonic scaling modules separately.
