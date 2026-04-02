# SCBE Formula Inventory — April 2026

## THE CANONICAL ONE (production)

```
H(d, pd) = 1 / (1 + φ·d_H + 2·pd)
```

- Range: (0, 1] — safety score, higher = safer
- Flip for cost: 1/H → [1, ∞)
- Flip for security bits: log₂(1/H) → [0, ∞)
- φ is LINEAR coefficient, NOT exponent
- Spec: docs/specs/LAYER_12_CANONICAL_FORMULA.md
- Code: packages/kernel/src/harmonicScaling.ts (pending phi update)

## THE THEORETICAL ONE (cost modeling)

```
π^(φ·d*)
```

- Range: [1, ∞) — unbounded cost
- NOT retired — was "never implemented" but math is sound
- Each unit step multiplies cost by π^φ ≈ 5.87
- Self-referential: at d=1.0, cost = π^φ ≈ 5.87 (the function references itself)
- Two fundamental constants (π from geometry, φ from tongues), zero arbitrary choices
- Good small-d resolution (unlike R^(d²) which collapses near zero)
- Use for: triangulation bounds, personality drift, progression gating, patent claims

## RETIRED — DO NOT USE

| Formula | Problem |
|---------|---------|
| R^(d²) with R=2 | Numerical collapse — at d=0.1, result is 1.007, indistinguishable from baseline |
| R^(d^φ) | Sensitivity backwards — φ < 2 means LESS aggressive than d² |
| R·π^(φ·d*) | Never implemented, but the π^(φ·d) part was revived |
| 1 + α·tanh(β·d*) | Absorbed — 1/H already provides unbounded growth |

## TRIANGULATION MATH

Multi-view improvement:
```
ε_multi / ε_single = (1 - ρ)^(k-1)
```

With k=4 views: 14% improvement at ρ ≈ 0.049 (95% view independence)
Consistent across chat and code domains = method-level property

## PERSONALITY-CONDITIONED

```
H_eff(d, pd, P) = [1/(1+φ·d_H+2·pd)] × (1 + αR - βO)
```

Trust drift: Δd = γ·(R - O)
Vote weight: w_i = (O_i + (1 - R_i)) / 2
