# SCBE Canonical Formula Registry

**Version:** 2.0.0
**Updated:** 2026-07-24
**Status:** active

## Purpose

This registry names the mathematical regimes implemented in the repository.
"Canonical" means registered and attributable to a runtime surface. It does
not mean that one formula can be substituted for every other formula called a
harmonic wall, score, or cost.

Every benchmark, receipt, and public technical claim must identify:

1. the runtime profile,
2. the formula regime,
3. its parameters,
4. the dataset or input domain, and
5. the code revision.

## Runtime Profiles

| Profile | Primary implementation | Layer 11 | Layer 12 |
|---|---|---|---|
| `TS_PIPELINE14` | `packages/kernel/src/pipeline14.ts` | normalized quadratic mean | `BOUNDED_SCORE` |
| `PY_REFERENCE14` | `src/scbe_14layer_reference.py` | normalized phi-power mean | `BOUNDED_SCORE` |
| `PY_FULL14` | `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py` | feature-space Euclidean aggregate | `BOUNDED_SCORE` |
| `THEOREM_WALL` | `src/symphonic_cipher/harmonic_scaling_law.py` | caller supplied | `BOUNDED_WALL` |
| `PUBLIC_COST_HELPER` | `src/index.ts`, `src/scbe_aethermoore/__init__.py` | not applicable | `QUADRATIC_EXP_COST` |
| `RESOURCE_COST` | `src/scbe_governance_math.py`, `src/symphonic_cipher/scbe_aethermoore/energy_budget.py` | not applicable | `PI_EXP_COST` |

These profiles are related implementations, not byte-for-byte equivalent
runtimes.

## Geometry

### G1: Poincare-Ball Distance

```text
d_H(u,v) = arcosh(
  1 + 2*||u-v||^2 / ((1-||u||^2)*(1-||v||^2))
)
```

Domain: `||u|| < 1` and `||v|| < 1`.

This is the Layer 5 metric used by the canonical Python and TypeScript
fourteen-layer implementations. Numerical code clamps inputs away from the
unit-ball boundary.

Primary references:

- `packages/kernel/src/hyperbolic.ts`
- `src/scbe_14layer_reference.py`
- `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py`

## Layer 11 Aggregation Regimes

### T1: Normalized Quadratic Mean

```text
d_tri = sqrt(lambda_1*d_1^2 + lambda_2*d_2^2 + lambda_3*d_G^2) / d_scale
```

Used by `TS_PIPELINE14`.

### T2: Normalized Phi-Power Mean

```text
d_tri = (
  lambda_1*d_1^phi + lambda_2*d_2^phi + lambda_3*d_G^phi
)^(1/phi) / d_scale
```

Used by `PY_REFERENCE14`.

### T3: Feature-Space Euclidean Aggregate

```text
d_tri = sqrt(d_H^2 + delta_tau^2 + delta_eta^2 + (1-fidelity))
```

Used by `PY_FULL14`.

No cross-profile Layer 11 parity claim is valid unless these definitions are
explicitly normalized to a shared contract.

## Harmonic Regimes

### H1: `BOUNDED_SCORE`

```text
H_score(d,pd) = 1 / (1 + d + 2*pd)
```

Domain: `d >= 0`, `pd >= 0`. Range: `(0, 1]`.

This is the current Layer 12 safety score in `TS_PIPELINE14`,
`PY_REFERENCE14`, and `PY_FULL14`. It decreases monotonically with distance
and phase deviation. A decision stage may divide risk by this score or consume
distance separately; the exact Layer 13 contract must be named.

Primary references:

- `packages/kernel/src/harmonicScaling.ts`
- `packages/kernel/src/pipeline14.ts`
- `src/scbe_14layer_reference.py`
- `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py`

### H2: `BOUNDED_WALL`

```text
H_wall(d) = 1 + alpha*tanh(beta*d)
```

Domain: `d >= 0`, `alpha > 0`, `beta > 0`. Range: `[1, 1+alpha)`.

This is a bounded risk multiplier in theorem-oriented and standalone Layer 13
modules.

Primary references:

- `src/symphonic_cipher/harmonic_scaling_law.py`
- `src/symphonic_cipher/scbe_aethermoore/layer_13.py`

### H3: `QUADRATIC_EXP_COST`

```text
H_cost(d,R) = R^(d^2)
```

The public helper uses the explicitly phi-scaled member:

```text
H_cost_phi(d) = phi^((phi*d)^2)
```

Domain: `d >= 0`, `R > 1`. Range: `[1, infinity)`.

This is a cost or stress function, not the bounded Layer 12 decision score.
It is exponential in squared distance. It is not a double exponential.

Primary references:

- `src/index.ts`
- `src/scbe_aethermoore/__init__.py`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/symmetry_axiom.py`

### H4: `PI_EXP_COST`

```text
H_pi(d,R) = R*pi^(phi*d)
```

Domain: `d >= 0`, `R > 0`. Range: `[R, infinity)`.

This regime is used by resource, access-cost, and spaceflight-oriented
surfaces. It is not the Layer 12 decision score.

Primary references:

- `src/scbe_governance_math.py`
- `src/governance/decision_envelope_v1.py`
- `src/symphonic_cipher/scbe_aethermoore/energy_budget.py`
- `src/polly_pads_runtime.py`

## AxiomLens Objective

The registered diagnostic overlay objective is:

```text
L_axiom = sum_a lambda_a * L_a
```

where `a` is ordered as:

```text
[unitarity, locality, causality, symmetry, composition]
```

The authoritative output is an `N x 5` residual field with an equally shaped
observation mask. Missing evidence is unobserved, not a zero-residual pass.

Source:
`src/symphonic_cipher/scbe_aethermoore/axiom_grouped/axiom_lens.py`.

## Registry Rules

1. Never write an unqualified `H` formula in an active specification.
2. Never compare metrics from different runtime profiles without a parity test.
3. Never call `R^(d^2)` or `phi^((phi*d)^2)` double exponential.
4. Treat old documents that omit a regime tag as historical until reconciled.
5. Add a formula here before using it as a canonical public claim.
6. A test proves behavior only for its named implementation and input domain.

## Related Authorities

- `docs/CANONICAL_SYSTEM_STATE.md`
- `docs/specs/LAYER_INDEX.md`
- `docs/specs/SCBE_CANONICAL_CONSTANTS.md`
- `docs/CORE_AXIOMS_CANONICAL_INDEX.md`
