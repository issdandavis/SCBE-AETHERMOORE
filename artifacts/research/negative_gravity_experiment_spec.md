# Negative Gravity Relevance — Experiment Specification

## Principle
Safety emerges from geometry, not enforcement. The center of the Poincare ball is safe not because it's labeled safe, but because leaving costs exponentially more. This is "negative gravity" — the absence of cost at the origin, not the presence of a barrier at the boundary.

## Hypothesis
If the PhaseTunnelGate's transmission coefficient T maps to position in the Poincare ball, then:
- TUNNEL heads (T≈1.0) are near the origin (low cost, high capability)
- COLLAPSE heads (T≈0.0) are near the boundary (high cost, low capability)
- The gradient between them follows H(d,R) = R^(d²) — not linear, not quadratic, but EXPONENTIAL in d²

## Experiment: Gradient Ablation

Instead of binary ablation (all TUNNEL or all COLLAPSE), ablate by TRANSMISSION TIER:

1. Rank all 72 heads by T value (high to low)
2. Ablate in groups of 6 (remove the 6 lowest T, then the next 6, etc.)
3. Measure perplexity at each ablation step
4. Plot: x = number of heads removed (sorted by T), y = perplexity

### Expected Result (if negative gravity holds)
The perplexity curve should NOT be linear. It should follow:
- Removing the bottom 6 (lowest T): small PPL increase
- Removing the next 6: slightly more
- ...
- Removing the top 6 (highest T): CATASTROPHIC increase

The curve shape should approximate R^(n²) where n = depth into the ranking.
This would prove the governance cost gradient is inherent to the learned structure.

### What This Would Mean
The model itself learned negative gravity during training. Gradient descent naturally organized attention heads into a Poincare-like geometry where:
- Important operations cluster near the "origin" (high T, low cost)
- Unimportant operations drift toward the "boundary" (low T, high cost)
- The transition is exponential, not linear

This would be a NEW FINDING: transformer training implicitly creates hyperbolic governance structure.

## Connection to Davis Formula
S(t,i,C,d) = t / (i * C! * (1+d))

The factorial C! maps to the number of competence dimensions (heads).
The (1+d) maps to the transmission coefficient T (d = 1-T).
The exponential cost gradient IS the negative gravity.

## Connection to Apartment Metaphor
- Couch (origin) = TUNNEL heads = zero cost to stay
- Patio (boundary) = COLLAPSE heads = 4-minute walk
- The view better be worth it = the operation must justify the governance cost
- The geometry makes the couch safe by default

## Run on Colab
Same OPT-1.3B model, same WikiText-2 eval. Just change ablation strategy from "all COLLAPSE vs all TUNNEL" to "progressive by T ranking."
