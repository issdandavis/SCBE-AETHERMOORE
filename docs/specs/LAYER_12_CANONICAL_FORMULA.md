# Layer 12: Canonical Harmonic Scaling Formula

Status: canonical (March 31, 2026)
Supersedes: all previous Layer 12 formula variants

## The One Formula

```
H(d, pd) = 1 / (1 + phi * d_H + 2 * pd)
```

Where:
- `d_H` = hyperbolic distance from Layer 5
- `pd` = phase deviation from Layer 9 (spectral coherence)
- `phi` = golden ratio = (1 + sqrt(5)) / 2 = 1.6180339...

## Three Readings of One Formula

| Reading | Expression | Range | Purpose |
|---------|-----------|-------|---------|
| **Safety Score** | H(d, pd) | (0, 1] | How safe is this? Higher = safer |
| **Risk Wall** | 1/H(d, pd) | [1, inf) | How much risk amplification? |
| **Security Bits** | log2(1/H) | [0, inf) | Effective security bit gain |

## Why phi

phi is a LINEAR COEFFICIENT on distance, NOT an exponent.

phi enters because:
- phi^0 through phi^5 are the Sacred Tongue weights (Kor'aelin through Draumric)
- phi is the unique fixed point of x^2 = x + 1
- It provides self-similar spacing between governance thresholds
- It makes the formula steeper than linear (more sensitive to drift) without the instability of quadratic

## Behavior

| d_H | pd | H (score) | 1/H (wall) | Governance |
|-----|-----|-----------|------------|------------|
| 0.0 | 0.0 | 1.000 | 1.000 | ALLOW |
| 0.3 | 0.1 | 0.593 | 1.685 | ALLOW |
| 0.5 | 0.1 | 0.498 | 2.009 | ALLOW |
| 1.0 | 0.1 | 0.355 | 2.818 | QUARANTINE |
| 2.0 | 0.2 | 0.204 | 4.908 | ESCALATE |
| 5.0 | 0.5 | 0.094 | 10.618 | DENY |

## Retired Formulas (DO NOT USE)

| Formula | Where It Was | Why Retired |
|---------|-------------|-------------|
| `R^(d^2)` | symphonic_cipher/core | Numerical collapse: small d all map to ~1.0 |
| `R * pi^(phi * d*)` | docs/blog, docs/ide | Never implemented in code |
| `1 + alpha * tanh(beta * d*)` | symphonic_cipher/harmonic_scaling_law.py | Absorbed: 1/H already provides unbounded growth |
| `R^(d^phi)` | Proposed by external review | Sensitivity backwards: phi < 2 means LESS aggressive than d^2 |

## Non-Equivalence Statement

The formulation `R^(d^phi)` is NOT equivalent to `1/(1+phi*d+2*pd)` and should
NOT be used. They are structurally different functions with different sensitivity
profiles. The canonical formula uses phi as a linear coefficient, not an exponent.

## Production Implementation

The canonical formula is implemented in:
- `packages/kernel/src/harmonicScaling.ts` (TypeScript, production)

The production code currently uses `1/(1+d+2*pd)` WITHOUT phi.
Adding phi as `1/(1+phi*d+2*pd)` is a pending code update.

## How Layer 13 Uses It

```
Risk_adjusted = Behavioral_Risk / H(d, pd)

if Risk_adjusted < 0.3:  ALLOW
if Risk_adjusted < 0.7:  QUARANTINE
if Risk_adjusted < 0.9:  ESCALATE
else:                     DENY
```
