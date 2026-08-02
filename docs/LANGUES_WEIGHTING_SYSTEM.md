---
id: LANGUES001
references: [SPEC001, TOKENIZER001]
feeds_into: [HARMONIC001]
implements: 'Profiled Langues Cost and Fractional-Dimension Breathing'
version_sync: '4.3.1'
mind_map_node: 'BrainState21D > Profiled Tongue Energies'
state_dims: 6
---

# Langues Weighting System

Status: active, corrected reference  
Updated: July 27, 2026  
Scope: Layer 3 cost profiles, Layer 6 fractional-dimension breathing, and
LWS/PHDM weight selection

## Canonical rule

There is no unqualified, universal "LWS number." Every output must name both:

1. the **weight profile** (`lws-linear` or `phdm-golden`); and
2. the **cost profile** (`kernel-v1`, `spacetor-v1`, `python-axiom-v1`, or
   the historical `notebook-2026-01`).

Do not compare, merge, or reproduce results across profiles without an
explicit conversion.

The complete equations, theorem conditions, numerical receipts, and
polytonic limitations are in:

- [`specs/LANGUES_WEIGHTING_SYSTEM_CORRECTED.md`](specs/LANGUES_WEIGHTING_SYSTEM_CORRECTED.md)
- [`specs/langues_weighting_system_profiles.json`](specs/langues_weighting_system_profiles.json)

## Weight profiles

### `lws-linear`

Base-operation and tokenizer paths use:

```text
KO  1.000       AV  1.125       RU  1.250
CA  1.333       UM  1.500       DR  1.667
```

These values approximate the just-intonation ratios
\((1,9/8,5/4,4/3,3/2,5/3)\). They are not powers of the golden ratio.

Evidence:

- `src/symphonic_cipher/scbe_aethermoore/cli_toolkit.py`
- `src/crypto/aetherlex-seed.ts`
- `src/spaceTor/trust-manager.ts`

### `phdm-golden`

Kernel, harmonic, and governance-cost paths use:

\[
w_l=\phi^l,\qquad l=0,\ldots,5,
\]

or approximately:

```text
1.000, 1.618, 2.618, 4.236, 6.854, 11.090
```

Evidence:

- `packages/kernel/src/languesMetric.ts`
- `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/langues_metric.py`
- `src/symphonic_cipher/harmonic_scaling_law.py`

## General cost family

\[
C(x,t)=\sum_{l=0}^{5}\nu_l(t)w_l
\exp\left(\beta_l[d_l(x)+a\sin(\omega_lt+\varphi_l)]\right).
\]

The symbols do not select their own parameters. The named cost profile fixes
\(d_l,w_l,\beta_l,a,\omega_l,\varphi_l\), clamping, and flux behavior.

The scalar \(C\) is a cost functional, not by itself a mathematical distance.
The separate weighted `langues_distance` function supplies a two-point metric.

## Correct theorem boundary

- Positivity is strict only when at least one dimension is active.
- Strict monotonicity and convexity hold for active deviations before any
  numerical clamp saturates.
- Temporal bounds use the profile's phase amplitude \(a\), which is `1.0` in
  the kernel and notebook profiles but `0.1` in the Python axiom profile.
- The absolute-deviation profiles are smooth in \(d\), continuous and
  piecewise smooth in \(x\), and nondifferentiable at \(x_l=\mu_l\).
- A time-varying gradient flow needs to account for
  \(\partial C/\partial t\); fixed-time descent alone is not a global
  Lyapunov proof.
- Integer modes and just-intonation ratios are rationally dependent, so the
  current runtimes do not satisfy a maximal-polytonic
  rational-independence condition.

## Regression contract

Any change must preserve:

1. explicit profile labels;
2. exact weight and frequency tables;
3. positivity and active-coordinate monotonicity;
4. fractional participation within `[0,1]`;
5. the ideal-point zero-subgradient convention in `python-axiom-v1`;
6. the deterministic notebook and Monte Carlo receipts in
   `tests/specs/test_langues_weighting_system_spec.py`.

If this page conflicts with executable behavior, treat the conflict as a bug
and update the code, profile registry, tests, and this document together.
