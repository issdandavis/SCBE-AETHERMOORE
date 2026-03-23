# Resonance Gate Spec

**Version:** 1.2.0  
**Date:** 2026-03-15  
**Status:** implemented in kernel, ordered rejection, and GeoSeal  
**Scope:** optional L12 modulation + deterministic L14-adjacent resonance scoring

---

## Summary

The Resonance Gate is a **geometry-aware frequency membrane** layered on top of SCBE's existing bounded Layer 12 score.

It does **not** replace the live bounded wall `1 / (1 + d + 2 * phaseDeviation)`.  
It adds an optional resonance term that can lower safety when geometry is bad and the signal is phase-misaligned.

Current source of truth:

- canonical implementation: `packages/kernel/src/resonanceGate.ts`
- public re-export: `src/harmonic/resonanceGate.ts`
- bounded L12 scorer with optional resonance: `packages/kernel/src/harmonicScaling.ts`
- 14-layer pipeline hook: `packages/kernel/src/pipeline14.ts`
- early rejection hook: `src/api/orderedRejection.ts`
- trust/quarantine hook: `src/geoseal.ts`

Default preset behavior:

- `BASELINE_RESONANCE_CONFIG` is the default deterministic gate
- `EVOLVED_RESONANCE_CONFIG` is opt-in behind config as `preset: 'evolved_v1'`
- `EVOLVED_V2_CONFIG` is opt-in behind config as `preset: 'evolved_v2'`

---

## Core Model

### 1. Static envelope

```text
H_env(d*, R) = R · pi^(phi · d*)
```

Where:

- `d*` = distance-from-safety proxy
- `R` = base scaling constant, default `1.5`
- `phi` = golden ratio

This is the pi-phi mound. It is diagnostic and cost-like, not the final pipeline safety score.

### 2. Tongue superposition

```text
W(t, delta) = sum_l w_l cos(2pi f0 phi^l t + theta_l + delta) / sum_l w_l
waveAlignment = clamp((W + 1) / 2, 0, 1)
```

Where:

- `f0 = 440`
- `l = 0..5` for `KO AV RU CA UM DR`
- `w_l = [1, phi, phi^2, phi^3, phi^4, phi^5]`
- `theta_l = [0, pi/3, 2pi/3, pi, 4pi/3, 5pi/3]`
- `delta` = deterministic phase offset derived from request or agent identity

### 3. Geometry alignment

```text
baselineGeometryAlignment = exp(-phi · d*)
evolvedGeometryAlignment = floor + (1 - floor) · exp(-k · d*)
```

This keeps resonance fail-closed while allowing an opt-in safe-origin softness fix.

Baseline defaults:

- `geometryDecay = phi`
- `geometryFloor = 0`

Evolved preset values:

- `geometryDecay = 0.742`
- `geometryFloor = 0.067`

`evolved_v2` keeps the same geometry as `evolved_v1`.

### 3.5. Phase discrimination strategies

Two phase scoring modes now exist:

- `weighted_wave`
  - legacy path
  - uses the averaged six-tongue oscillation after per-tongue weighting
- `matched_filter`
  - experimental path used by `evolved_v2`
  - cross-correlates the absolute six-tongue contribution pattern against a reference tongue signature
  - preserves tongue-level discrimination instead of washing it out through averaging

### 4. Resonance score

```text
rho = clamp(geometryAlignment · waveAlignment, 0, 1)
barrierCost = H_env / max(rho, 1e-6)
```

Decision thresholds:

- baseline:
  - `rho >= 0.7` -> `PASS`
  - `0.3 <= rho < 0.7` -> `ESCALATE`
  - `rho < 0.3` -> `REJECT`
- evolved_v1:
  - `rho >= 0.300` -> `PASS`
  - `0.213 <= rho < 0.300` -> `ESCALATE`
  - `rho < 0.213` -> `REJECT`

Because `waveAlignment` is mapped into `[0,1]`, there are no negative walls and no raw sine zero-crossing gaps.

---

## Kernel Integration

### Layer 12

The live bounded score remains:

```text
H_score(d, pd) = 1 / (1 + d + 2pd)
```

Resonance is applied as an **optional modulation**:

```text
H_modulated = H_score · ((1 - blend) + blend · rho)
```

Current defaults:

- resonance is **off by default** in the kernel path
- when resonance is enabled, the default preset is `baseline`
- when enabled, `blend` defaults to `0.5`
- default resonance sample time is deterministic: `t = 0`
- the evolved preset is opt-in via `preset: 'evolved_v1'`
- the matched-filter preset is opt-in via `preset: 'evolved_v2'`

This preserves backward compatibility while allowing real L12 experiments through configuration.

### Pipeline 14

`scbe14LayerPipeline()` now accepts:

```ts
resonance?: {
  enabled?: boolean;
  blend?: number;
  timeSec?: number;
  preset?: 'baseline' | 'evolved_v1' | 'evolved_v2';
  phaseStrategy?: 'weighted_wave' | 'matched_filter';
  phaseReferenceOffset?: number;
  signalPhaseOffset?: number;
  weights?: number[];
  geometryDecay?: number;
  wavePower?: number;
  geometryFloor?: number;
  thresholds?: {
    passThreshold?: number;
    rejectThreshold?: number;
  };
  R?: number;
}
```

When disabled, pipeline behavior is unchanged.  
When enabled, `layers.l12_harmonic` is the resonance-modulated safety score.

Recommended rollout:

- keep the baseline gate as the deterministic default
- use `EVOLVED_RESONANCE_CONFIG` or `preset: 'evolved_v1'` only where the safe-origin harshness fix is wanted
- iterate on phase discrimination separately with tongue-specific weighting or matched-filter scoring rather than more global offsets

---

## Ordered Rejection Integration

`OrderedRejectionPipeline` adds:

- `S7_5_RESONANCE_GATE`
- `lastResonance`
- deterministic `resonanceTimeSec` config, default `0`

Important accuracy note:

The ordered rejection pipeline currently executes:

`S0 -> S1 -> S2 -> S3 -> S4 -> S5 -> S7.5`

It does **not** yet run full `S6 -> S7 -> S8 -> S9 -> S10` inside this file.  
So S7.5 is an **early resonance gate**, not a literal insertion into a fully implemented S7/S8 chain.

Phase offset is seeded from:

```text
actorId | actorType | intent | resourceClassification
```

This removes wall-clock-driven randomness from accept/reject decisions.

---

## GeoSeal Integration

`applyResonanceGate()` now:

- derives `d*` from trust
- seeds phase from `agent.id | tongue | phase`
- uses deterministic `t = 0` unless overridden
- applies **decision-weighted trust multipliers**

Current trust multipliers:

- `PASS` -> `0.95 + 0.05 * rho`
- `ESCALATE` -> `0.75 + 0.25 * rho`
- `REJECT` -> `0.25 + 0.25 * rho`

This avoids the broken behavior where trust was multiplied directly by `rho` and could collapse mostly due to phase sample timing.

Auto-quarantine remains:

- `3` consecutive resonance rejects -> quarantine

---

## Frequency Table

| Tongue | Code | Phase | Frequency |
|---|---|---:|---:|
| Kor'aelin | KO | `0` | `440.00` |
| Avali | AV | `pi/3` | `711.93` |
| Runethic | RU | `2pi/3` | `1151.93` |
| Cassisivadan | CA | `pi` | `1863.86` |
| Umbroth | UM | `4pi/3` | `3015.79` |
| Draumric | DR | `5pi/3` | `4879.65` |

These are `440 * phi^l`, not rounded narrative constants.

---

## Determinism Rules

To keep the gate testable and prevent phase-only false positives:

- default runtime sample time is `0`
- phase comes from deterministic seed hashing
- geometry always participates in `rho`
- pure time phase no longer decides outcomes by itself

This is the main bug fix over the earlier draft.

---

## Verification Targets

Regression coverage now exists for:

- geometry-sensitive `rho`
- seeded phase offsets
- optional Layer 12 modulation
- pipeline14 resonance passthrough
- ordered rejection `S7_5_RESONANCE_GATE`
- GeoSeal trust/quarantine behavior

Relevant tests:

- `tests/harmonic/resonanceGate.test.ts`
- `tests/harmonic/harmonicScaling.test.ts`
- `tests/harmonic/pipeline14.test.ts`
- `tests/L2-unit/orderedRejection.unit.test.ts`
- `tests/harmonic/geoseal.test.ts`

---

## Formula Family Map

| Family | Formula | Current role |
|---|---|---|
| bounded kernel score | `1 / (1 + d + 2pd)` | live Layer 12 safety score |
| temporal intent wall | `R^(d^2 · x)` | separate temporal branch |
| pi-phi envelope | `R · pi^(phi · d*)` | resonance static envelope |
| resonance gate | `rho = exp(-phi d*) · waveAlignment` | deterministic resonance score |

The resonance gate is now a **supplementary membrane** over the bounded kernel, not a blanket replacement for every harmonic wall variant in the repo.
