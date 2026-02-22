# 21D State Manifold: Canonical Fixed Schema (v1)

Status: Canonical schema for SCBE-AETHERMOORE runtime state
Updated: 2026-02-21

## Decision

Schema mode: **Option 1 (exact named fields)**.

Rationale:
- Stable audit semantics
- Deterministic telemetry parsing
- Safer downstream governance contracts

## 1. Canonical 21D Layout (6 + 6 + 9)

State vector `s in R^21` (0-based indexing):

### Hyperbolic tongue position (6)
- `s[0]`  `u_ko`
- `s[1]`  `u_av`
- `s[2]`  `u_ru`
- `s[3]`  `u_ca`
- `s[4]`  `u_um`
- `s[5]`  `u_dr`

Interpretation: point `u in B_c^6` (Poincare ball)

### Tongue phase alignment (6)
- `s[6]`   `theta_ko`
- `s[7]`   `theta_av`
- `s[8]`   `theta_ru`
- `s[9]`   `theta_ca`
- `s[10]`  `theta_um`
- `s[11]`  `theta_dr`

Interpretation: periodic angles (torus `T^6`)

### Governance telemetry (9)
- `s[12]`  `flux_breath`
- `s[13]`  `flux_rate`
- `s[14]`  `coherence_spectral`
- `s[15]`  `coherence_spin`
- `s[16]`  `coherence_triadic`
- `s[17]`  `d_star`
- `s[18]`  `h_eff`
- `s[19]`  `risk_score`
- `s[20]`  `trust_score`

## 2. Manifold Structure

Canonical runtime manifold:

`M = B_c^6 x T^6 x R^9`

Where:
- `B_c^6`: hyperbolic tongue embedding
- `T^6`: phase alignment angles
- `R^9`: governance telemetry channel

## 3. Product Metric

For states `a,b`:

`d_M^2 = w_h d_hyp(u_a,u_b)^2 + w_t d_torus(theta_a,theta_b)^2 + (z_a-z_b)^T W_z (z_a-z_b)`

- `u = s[0:6]`
- `theta = s[6:12]`
- `z = s[12:21]`
- `W_z`: positive diagonal matrix for telemetry weighting

`d_M = sqrt(d_M^2)`.

### 3.1 Hyperbolic term

`d_hyp(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))`

Constraint: `||u|| < 1`.

### 3.2 Torus term

For each phase axis `i`:

`delta_i = atan2(sin(theta_a_i - theta_b_i), cos(theta_a_i - theta_b_i))`

`d_torus = sqrt(sum_i delta_i^2)`

## 4. Validation Constraints

Required checks per snapshot:
- `len(s) == 21`
- `||u|| < 1`
- telemetry ranges:
  - `coherence_* in [0,1]`
  - `risk_score in [0,1]`
  - `trust_score in [0,1]`
  - `d_star >= 0`
  - `h_eff >= 0`

`flux_breath` and `flux_rate` are real-valued channels (implementation-normalized by policy).

## 5. Harmonic Wall Convention

Harmonic wall uses tongue subspace dimension only:

`H(d,R) = R^(d^2), d = 6`

If `u` is in Poincare ball with `r = ||u||`, map to effective wall radius:

`R = 1/(1-r)`

## 6. Versioning Rule

Schema is versioned as `state_schema_version = "state21_v1"`.

Any field changes require:
- new version id (e.g. `state21_v2`)
- explicit migration map
- side-by-side reader support during transition window

## 7. Reference Implementation

Reference utilities:
- `src/harmonic/state21_product_metric.py`

This module implements:
- fixed slot parsing
- manifold validation
- product-metric distance
