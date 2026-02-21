# Langues Weighting System (LWS)

Status: active reference  
Updated: February 19, 2026  
Scope: Layer 3 (Langues metric) + Layer 6 (flux breathing)

---

## Purpose

This document defines the mathematical contract for Langues weighting in SCBE.
It is code-aligned to:

- `packages/kernel/src/languesMetric.ts`
- `src/symphonic_cipher/scbe_aethermoore/cli_toolkit.py` (LWS/PHDM weight profiles)

If this document conflicts with code, code is canonical.

---

## 1. Core Metric

Let:

- `x = (x1..x6)` be current state
- `mu = (mu1..mu6)` be trusted reference state
- `d_l = |x_l - mu_l| >= 0`
- `w_l > 0` be langue weights
- `beta_l > 0` be growth factors
- `omega_l > 0` and `phi_l` be temporal frequency/phase

Canonical metric:

`L(x, t) = sum_{l=1}^6 w_l * exp(beta_l * (d_l + sin(omega_l*t + phi_l)))`

Kernel implementation form takes `d` directly as a 6D point:

`L(d, t) = sum_{l=1}^6 w_l * exp(beta_l * (d_l + sin(omega_l*t + phi_l)))`

---

## 2. Weight Profiles

This repo currently uses two explicit profiles.

### 2.1 LWS-Linear (base operations)

Used in toolkit paths (`cli_toolkit.py`) for base operational weighting:

- KO: 1.000
- AV: 1.125
- RU: 1.250
- CA: 1.333
- UM: 1.500
- DR: 1.667

### 2.2 PHDM-Golden (governance/crisis scaling)

Used in kernel/harmonic paths and crisis-oriented weighting:

- `w_l = phi^(l-1)` for `l = 1..6`
- approximately: `1.000, 1.618, 2.618, 4.236, 6.854, 11.090`

### 2.3 Rule

Always label which profile is active (`lws` or `phdm`) in experiments and claims.
Do not mix profile results without explicit conversion.

---

## 3. Mathematical Properties

Below, assume `w_l > 0`, `beta_l > 0`.

### 3.1 Positivity

`L(x,t) > 0` for all `x,t`.

Reason: each summand is positive (`w_l > 0`, `exp(.) > 0`).

### 3.2 Monotonicity in Deviation

For each dimension:

`dL/dd_l = w_l * beta_l * exp(beta_l * (d_l + sin(...))) > 0`

Any increase in `d_l` increases cost.

### 3.3 Bounded Temporal Breathing

Because `sin(.) in [-1,1]`:

`L_min(x) <= L(x,t) <= L_max(x)`

where:

- `L_min(x) = sum_l w_l * exp(beta_l * (d_l - 1))`
- `L_max(x) = sum_l w_l * exp(beta_l * (d_l + 1))`

### 3.4 Convexity in `d`

For each `d_l`:

`d^2L/dd_l^2 = (beta_l^2) * w_l * exp(beta_l * (d_l + sin(...))) > 0`

So `L` is strictly convex in `d`.

### 3.5 Smoothness Clarification

- In variables `d_l` (distance inputs), `L` is smooth (`C^infinity`).
- In variables `x_l` with `d_l = |x_l - mu_l|`, `L` is not differentiable at `x_l = mu_l` due to absolute value.

This is expected and does not break runtime behavior.

### 3.6 Gradient (distance form)

`nabla_d L = [w_l*beta_l*exp(beta_l*(d_l + sin(...)))]_{l=1..6}`

Steepest descent for alignment is `-nabla_d L`.

---

## 4. Fluxing / Fractional Dimension Extension

Define flux coefficients:

- `nu_l(t) in [0,1]`
- `nu(t) = (nu_1..nu_6)`

Flux metric:

`L_f(x,t) = sum_{l=1}^6 nu_l(t) * w_l * exp(beta_l * (d_l + sin(omega_l*t + phi_l)))`

ODE used by kernel-style implementation:

`dot(nu_l) = kappa_l*(nu_bar_l - nu_l) + sigma_l*sin(Omega_l*t)`

with clipping:

`nu_l <- clip(nu_l, 0, 1)`

Effective dimensionality:

`D_f(t) = sum_{l=1}^6 nu_l(t)`  (range `[0,6]`)

Semantic states (from `getFluxState`):

- Polly: `nu >= 0.9`
- Quasi: `0.5 <= nu < 0.9`
- Demi: `0.1 <= nu < 0.5`
- Collapsed: `nu < 0.1`

---

## 5. Cycle-Averaged Energy (Fixed d)

For one dimension with fixed `d_l`:

`E_l = (1/T) * integral_0^T w_l*exp(beta_l*(d_l + sin(omega_l t + phi_l))) dt`

Over one full sinusoidal cycle:

`E_l = w_l * exp(beta_l*d_l) * I0(beta_l)`

where `I0` is the modified Bessel function of order 0.

Total cycle-averaged energy:

`E = sum_{l=1}^6 w_l * exp(beta_l*d_l) * I0(beta_l)`

---

## 6. Reference Implementation (Python)

```python
import numpy as np

def langues_metric(x, mu, w, beta, omega, phi, t, nu=None):
    d = np.abs(x - mu)
    s = d + np.sin(omega * t + phi)
    nu = np.ones_like(w) if nu is None else nu
    return float(np.sum(nu * w * np.exp(beta * s)))

def flux_update(nu, kappa, nu_bar, sigma, Omega, t, dt, nu_min=1e-6):
    dnu = kappa * (nu_bar - nu) + sigma * np.sin(Omega * t)
    return np.clip(nu + dnu * dt, nu_min, 1.0)
```

---

## 7. Testing Contract

Minimum tests for any LWS changes:

1. Positivity: `L > 0` for random valid inputs.
2. Monotonicity: increasing one `d_l` increases `L`.
3. Flux bounds: `nu_l` remains in `[0,1]`.
4. State classification: thresholds map to Polly/Quasi/Demi/Collapsed.
5. Profile labeling: outputs identify `lws` vs `phdm`.

Existing related test surfaces:

- `tests/harmonic/languesMetric.test.ts`
- `src/symphonic_cipher/tests/test_harmonic_scaling.py`

---

## 8. Integration Notes

- Layer 3: `L` or `L_f` provides weighted geometry cost.
- Layer 6: flux ODE controls breathing intensity via `nu`.
- Layer 12 coupling should declare regime:
  - wall enforcement (`H(d,R)=R^(d^2)` family),
  - bounded scoring (`1/(1+d+2*pd)` family),
  - or another explicit formula.

Do not claim one universal harmonic formula across all modules without regime tags.

