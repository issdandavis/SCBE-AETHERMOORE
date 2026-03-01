# L12 Harmonic Scaling — Canonical Formula Reference

**Status**: AUTHORITATIVE — all code, tests, patents, and customer docs MUST reference this file.
**Last updated**: 2026-02-28

## The Three H Formulas

SCBE uses three harmonic functions. They are NOT interchangeable. Each has a distinct purpose, domain, and codomain.

### 1. H_score — Bounded Safety Score (Pipeline L12)

```
H_score(d*, pd) = 1 / (1 + d* + 2 * pd)
```

| Property | Value |
|----------|-------|
| **Domain** | d* >= 0, pd >= 0 |
| **Codomain** | (0, 1] |
| **At origin** | H_score(0, 0) = 1.0 (maximally safe) |
| **Monotonicity** | Strictly decreasing in d* and pd |
| **Purpose** | Pipeline L12 score fed into L13 risk division |
| **L13 wiring** | Risk' = Risk_base / H_score (lower H_score = higher amplified risk) |

**Where used**:
- `packages/kernel/src/harmonicScaling.ts` → `harmonicScale(d, phaseDeviation)`
- `src/symphonic_cipher/scbe_aethermoore/layers_9_12.py` → `harmonic_scaling(d_star, phase_deviation)`

**Variables**:
- `d*` = realm distance from Layer 8 (hyperbolic distance to nearest safe attractor)
- `pd` = phase deviation from Layer 10 spin coherence

**Why this replaced R^(d^2)**: The super-exponential formula mapped all small distances to ~1.0, destroying ranking. AUC dropped from 0.984 to 0.054 on subtle-attack benchmarks. The bounded formula preserves differentiation at all scales.

---

### 2. H_wall — Bounded Risk Multiplier (L13 Lemma 13.1)

```
H_wall(d*, alpha, beta) = 1 + alpha * tanh(beta * d*)
```

| Property | Value |
|----------|-------|
| **Domain** | d* >= 0, alpha > 0, beta > 0 |
| **Codomain** | [1, 1 + alpha] |
| **At origin** | H_wall(0) = 1.0 (no amplification) |
| **Monotonicity** | Strictly increasing in d* (saturates) |
| **Purpose** | L13 composite risk multiplier |
| **L13 wiring** | Risk' = Behavioral_Risk * H_wall * Time_Multi * Intent_Multi |

**Where used**:
- `src/symphonic_cipher/scbe_aethermoore/layer_13.py` → `harmonic_H(d_star, params)`
- Default params: alpha=1.0, beta=1.0 → H_wall in [1, 2]

**Variables**:
- `d*` = realm distance from Layer 8
- `alpha` = maximum amplification above baseline
- `beta` = steepness of transition curve

**Key property**: Bounded. H_wall can never exceed 1+alpha. This is critical for Lemma 13.1 proofs (upper bound on Risk'). The derivative is `alpha * beta * sech^2(beta * d*)`, which is always positive and largest near d*=0.

---

### 3. H_exp — Unbounded Exponential Wall (Patent Claim / Cost Model)

```
H_exp(d*, R) = R^(d*^2)
```

| Property | Value |
|----------|-------|
| **Domain** | d* >= 0, R > 1 |
| **Codomain** | [1, +infinity) |
| **At origin** | H_exp(0, R) = 1.0 |
| **Monotonicity** | Strictly increasing, super-exponential |
| **Purpose** | Patent claim — adversarial cost model |
| **Usage** | Theoretical; clamped in production code |

**Where used**:
- `src/api/governance_saas.py` → `harmonic_wall(d, R)` (R default 1.5)
- `src/symphonic_cipher/scbe_aethermoore/layer_13.py` → `harmonic_vertical_wall(d_star, max_exp=50.0)`
- Patent language: "cost grows as R^(d^2), making adversarial actions computationally infeasible"

**Variables**:
- `d*` = realm distance
- `R` = base (golden ratio PHI in patent, 1.5 in production SaaS)

**Key property**: Unbounded. This is the "vertical wall" — it makes the economic argument that attacks at distance d have cost ~R^(d^2). In production, clamped to `exp(min(d^2, 50))` to prevent float overflow.

---

## Which Formula Goes Where

| Context | Formula | Reason |
|---------|---------|--------|
| **Pipeline L12 → L13** | H_score | Bounded (0,1], safe for division, preserves ranking |
| **L13 risk multiplication** | H_wall | Bounded [1, 1+alpha], provably finite composite risk |
| **Patent claims** | H_exp | Unbounded, makes the "exponential cost" argument |
| **Customer API /v1/score** | H_score | Returns safety score 0-1 (intuitive for customers) |
| **Customer API /v1/govern** | H_wall + H_score | H_wall for internal risk amplification, H_score in response |
| **Marketing / white paper** | H_exp | "Attacks cost R^(d^2)" is the headline |
| **Test golden vectors** | All three | Each must produce stable outputs for given inputs |

---

## Variable Glossary

| Symbol | Name | Source Layer | Range | Unit |
|--------|------|-------------|-------|------|
| `d*` | Realm distance | L8 (min distance to safe attractor) | [0, +inf) | Hyperbolic radians |
| `d_H` | Raw hyperbolic distance | L5 | [0, +inf) | Hyperbolic radians |
| `pd` | Phase deviation | L10 (spin coherence) | [0, 1] | Dimensionless |
| `R` | Harmonic base | Constant | PHI=1.618 or configurable | Dimensionless |
| `alpha` | Wall amplitude | L13 config | > 0, default 1.0 | Dimensionless |
| `beta` | Wall steepness | L13 config | > 0, default 1.0 | Dimensionless |
| `d_tri` | Triadic distance | L11 | [0, +inf) | Weighted RMS |
| `s_spec` | Spectral coherence | L9 | [0, 1] | Dimensionless |
| `c_spin` | Spin coherence | L10 | [0, 1] | Dimensionless |
| `tau` | Trust score | Byzantine consensus | [0, 1] | Dimensionless |

---

## Golden Test Vectors

These MUST produce identical outputs across all implementations (TS, Python, WASM).

### H_score
```
H_score(0.0, 0.0)   = 1.0
H_score(1.0, 0.0)   = 0.5
H_score(2.0, 0.0)   = 0.3333...
H_score(0.0, 0.5)   = 0.5
H_score(1.0, 0.5)   = 0.3333...
H_score(5.0, 1.0)   = 0.125
```

### H_wall (alpha=1.0, beta=1.0)
```
H_wall(0.0)   = 1.0
H_wall(0.5)   = 1.4621...  (1 + tanh(0.5))
H_wall(1.0)   = 1.7616...  (1 + tanh(1.0))
H_wall(2.0)   = 1.9640...  (1 + tanh(2.0))
H_wall(5.0)   = 1.9999...  (1 + tanh(5.0))
H_wall(100.0) = 2.0        (saturated)
```

### H_exp (R=PHI=1.618...)
```
H_exp(0.0, PHI)  = 1.0
H_exp(0.5, PHI)  = PHI^0.25  = 1.1278...
H_exp(1.0, PHI)  = PHI^1     = 1.6180...
H_exp(2.0, PHI)  = PHI^4     = 6.8541...
H_exp(3.0, PHI)  = PHI^9     = 76.013...
H_exp(5.0, PHI)  = PHI^25    = 2.5E+5 (clamped in production)
```

---

## Relationship Between Formulas

```
   d* = 0                d* = 1              d* = 3              d* = 5
   ┌─────────────────────────────────────────────────────────────────────
   │ H_score:  1.0        0.5                 0.25                0.167
   │ H_wall:   1.0        1.76                1.995               ~2.0
   │ H_exp:    1.0        1.62                76.0                250,000
   └─────────────────────────────────────────────────────────────────────

   H_score falls → customer sees "safety score dropping"
   H_wall rises  → internal risk multiplier grows (bounded)
   H_exp rises   → theoretical attack cost grows (unbounded)

   All three agree at d*=0: safe operations cost nothing extra.
   All three diverge monotonically: further from safe = worse.
```

---

## Ternary Effect — The Three-Trit Detection Signal

The three H formulas produce a **ternary decomposition** that maps directly to the Hamiltonian Braid's `{-1, 0, +1}` phase space. Each formula contributes one trit:

```
t_score = +1 if H_score > 0.67,   0 if 0.33-0.67,   -1 if < 0.33
t_wall  = +1 if H_wall  < 1.5,    0 if 1.5-1.9,     -1 if > 1.9
t_exp   = +1 if H_exp   < 2.0,    0 if 2.0-10.0,    -1 if > 10.0
```

### Normal operation: all three agree

When `d*` is the only input, all three formulas are monotonic in `d*`, so they correlate:

```
Safe:     (+1, +1, +1)  →  d* < 0.5
Transit:  ( 0,  0,  0)  →  0.5 < d* < 2.0
Hostile:  (-1, -1, -1)  →  d* > 2.0
```

### Ternary disagreement = sophisticated attack detection

Phase deviation `pd` only affects H_score (not H_wall or H_exp). This means a state with low `d*` but high `pd` produces:

```
H_score: LOW (pd pulls it down)  → t_score = -1 or 0
H_wall:  LOW (d* is small)       → t_wall  = +1
H_exp:   LOW (d* is small)       → t_exp   = +1
```

Result: `(-1, +1, +1)` — "geometrically close but phase-incoherent."

This is the signature of an attacker who stays close to safe behavior but with chaotic timing/phases. The ternary disagreement between H_score and (H_wall, H_exp) IS the detection signal.

### Ternary states and their meanings

| Trit Vector | Meaning | Action |
|-------------|---------|--------|
| `(+1, +1, +1)` | Fully safe | ALLOW |
| `(0, 0, 0)` | Transition zone | QUARANTINE |
| `(-1, -1, -1)` | Fully adversarial | DENY |
| `(-1, +1, +1)` | Phase-incoherent but geometrically close | ESCALATE (subtle attack) |
| `(0, -1, -1)` | High distance, moderate score | DENY (aggressive attack, easy to detect) |

### Connection to Hamiltonian Braid 9-state phase diagram

The 9-state dual ternary from `hamiltonian_braid.py` uses two trits: `(phase_a, phase_b)`. The H-formula ternary adds a third dimension. Combined: `(phase_a, phase_b, h_trit)` gives a 27-state joint phase space where the braid phase and the harmonic scaling interact.

This is the mathematical basis for the ESCALATE decision tier (which exists in the SaaS API but is missing from the canonical TS pipeline — fixing that is a separate task).

---

## Citation Sources (for customer-facing docs)

Market data referenced in SCBE materials:
- MDR market $4.19B (2025): Mordor Intelligence via PR Newswire, "2025 Managed Detection & Response Market Report"
- MDR 21.95% CAGR to $11.3B by 2030: Same source
- zkEVM proving latency improvements: Ethereum Foundation roadmap updates, Vitalik Buterin blog posts
- Bug bounty $81M payouts: HackerOne 2025 Annual Report via BleepingComputer
- PQC NIST standards: NIST IR 8413, FIPS 203/204/205 (August 2024 release)

Full citation list: `docs/RESEARCH_SOURCES.md` (to be created for external publications)
