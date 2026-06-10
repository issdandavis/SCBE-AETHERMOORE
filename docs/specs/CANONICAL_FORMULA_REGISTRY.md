# Canonical Formula Registry

Updated: 2026-05-01
Status: Active

## Purpose

Single authority file for active mathematical formulas referenced by runtime and governance docs.

## Formula Set

### F1: Hyperbolic Distance (Poincare Ball)

`d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))`

- Used by: Layer 5 distance and downstream safety scoring (canonical TS/L5 path; Möbius-invariant)
- References: `src/harmonic/`, `src/scbe_math_reference.py`, `src/video_lattice/poincare_lattice.py`

### F2: Temporal Intent Multiplier

`x_factor = min(3.0, (0.5 + accumulated_intent * 0.25) * (1 + (1 - trust)))`

- Used by: Layer 11 temporal intent aggregation
- References: `src/spiralverse/temporal_intent.py`, `src/scbe_math_reference.py`

### F3: Harmonic Wall (Canonical Runtime Family)

`H(d*, R) = R^((phi * d*)^2)`

- Used by: canonical wall family in governance documentation
- References: `docs/specs/CANONICAL_SYSTEM_STATE.md`, `docs/specs/SCBE_CANONICAL_CONSTANTS.md`
- Distance input note: in the Python `RuntimeGate` (`src/governance/runtime_gate.py`), the `d*`
  fed to this wall is a phi-weighted **Euclidean** drift from a learned centroid
  (`_weighted_centroid_drift`), **not** F1's arcosh d_H. It is a monotone runtime-scoped
  surrogate (fails Möbius-invariance; see `scripts/eval/gate_mobius_invariance.py`), related to
  but not identical with the canonical hyperbolic metric.

### F4: Bounded Safety Scorer (Compatibility / Product Paths)

`score = 1 / (1 + d + 2 * phaseDeviation)`

- Used by: bounded scoring paths in package/runtime compatibility surfaces
- References: `packages/kernel/src/harmonicScaling.ts`
- Status: compatibility/runtime-scoped variant, not a contradiction with F3 when explicitly labeled as bounded scorer

### F5: Triadic Risk Aggregation

`risk = (0.3*I_fast^phi + 0.5*I_memory^phi + 0.2*I_governance^phi)^(1/phi)`

- Used by: temporal risk composition paths
- References: `src/scbe_math_reference.py`

## Registry Rules

1. New formulas must be added here before broad doc adoption.
2. If runtime behavior differs, annotate as `runtime-scoped` or `compatibility`.
3. Deprecated formulas are retained with explicit status, never silently removed.

## Related Authorities

- `docs/specs/CANONICAL_SYSTEM_STATE.md`
- `docs/specs/SCBE_CANONICAL_CONSTANTS.md`
- `docs/specs/SPEC.md`
