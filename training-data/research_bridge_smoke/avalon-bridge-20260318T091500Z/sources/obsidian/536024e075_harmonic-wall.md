# Harmonic Wall

> The cost function that makes boundary-crossing exponentially expensive.

## Two Variants

### 1. Cost Multiplier (Root Package)
```
H(d, R) = R^(d²)
```
- `d` = hyperbolic distance from origin
- `R` = base risk factor (typically 2.0-10.0)
- As d increases, cost grows super-exponentially
- Located: `symphonic_cipher/` (root)

**Behavior**: At d=1, cost = R. At d=2, cost = R^4. At d=3, cost = R^9.
This makes deep traversal into high-risk territory progressively more expensive — a natural "wall" that doesn't hard-block but makes attacks economically infeasible.

### 2. Safety Score (Src Package)
```
H(d, pd) = 1 / (1 + d + 2*pd)
```
- `d` = distance
- `pd` = phase deviation
- Returns bounded [0, 1] safety score
- Located: `src/symphonic_cipher/`

**Behavior**: At d=0, pd=0 → H=1.0 (maximum safety). As distance or deviation increases, safety drops smoothly toward 0. Never reaches 0 — always some residual safety.

## Import Collision Warning

Tests use `_IS_SAFETY_SCORE` flag to detect which variant is loaded, because many test files add `src/` to sys.path causing import resolution to the src/ version.

## Mathematical Properties
- Both are monotonically decreasing in d (further = more cost/less safe)
- Cost variant is unbounded above (allows infinite cost)
- Safety variant is bounded [0, 1] (suitable for probability calculations)
- Cost variant connects to [[Dual Lattice Framework]] via risk amplification

## Cross-References
- [[Grand Unified Statement]] — H appears in the governance decision pipeline
- [[14-Layer Architecture]] — Spans L5 (distance) and L10 (harmonic analysis)
- [[CDDM Framework]] — H maps between physical risk and governance cost domains

## Academic Grounding
- Chladni (1787) "Entdeckungen uber die Natur des Klanges" — original cymatics
- Stillinger & Weber (1984) "Packing Structures and Transitions in Liquids and Solids" — energy landscape metaphor
- The harmonic wall is analogous to potential barriers in quantum mechanics (WKB approximation)
