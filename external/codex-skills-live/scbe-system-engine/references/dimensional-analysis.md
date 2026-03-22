# Dimensional Analysis

## Core Rules

1. Require unit compatibility for addition and subtraction.
2. Require multiplicative unit propagation for products and ratios.
3. Require arguments of `log`, `exp`, `sin`, `cos`, and related transforms to be dimensionless.
4. Require explicit declaration of matrix entry units before determinant use.
5. Require scaling analysis versus graph size or state size when determinant or spectral terms appear.

## Laplacian Determinant Notes

For graph Laplacian-based formulas:

1. Unweighted graph Laplacian entries are dimensionless.
2. Full Laplacian determinant for connected graphs is zero because one eigenvalue is zero.
3. Reduced Laplacian determinant equals the number of spanning trees (Kirchhoff), which is dimensionless and can grow rapidly with graph size.
4. Determinant-derived terms may introduce graph-size-driven amplification even when units are valid.

## Common Error #5: Graph Scaling Trap in stiffness proposals

For complete graph prototypes, `det(L_reduced) = N^(N-2)`.
So `log(1 + det(L_reduced)) = (N-2)·log(N)` creates size-driven blow-up.
Do not accept this form as a final stiffness term unless the graph-size term is normalized by an explicit and justified factor.

## Formula Review Checklist

1. Confirm unit validity.
2. Confirm dimensionless transform arguments.
3. Compare with baseline formula under fixed units.
4. Evaluate monotonicity and boundedness.
5. Evaluate graph-size sensitivity and asymptotics.
6. Recommend accept, quarantine, or deny with rationale.

## Example: `kappa_eff = (E/N) * log(1 + det(L))`

1. Unit check:
   - If `E/N` is dimensionless and `det(L)` is dimensionless, dimensional form is valid.
2. Behavior check:
   - `det(L)` can scale aggressively with graph size, so `log(1 + det(L))` can encode topology-size effects rather than physical stiffness alone.
3. Verdict pattern:
   - Mark as dimensionally admissible but behaviorally risky without normalization or size correction.
