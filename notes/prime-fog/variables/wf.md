---
tags: [variable, blend-weight]
---

# wf (frozen weight)

**Type:** blend formula coefficient
**Formula component:** `score = wf * frz_z + [[wa]] * |frz_z| + [[wc]] * cen_z`
**Range used:** any real number (negative = adversarial, positive = cooperative)

## What it controls

The sign and magnitude of the frozen gate's direct contribution to the blend.

- **wf < 0 (adversarial):** the blend actively penalizes rows the frozen gate likes. Centroid can counteract frozen's picks. Used when frozen gate's opinion is a *contraindication*.
- **wf ≈ 0:** frozen gate contributes only through [[wa]] (magnitude), not direction.
- **wf > 0 (cooperative):** the blend reinforces frozen gate's picks.

## Known per-regime values

| Regime | wf | Interpretation |
| --- | ---: | --- |
| [[dominant]] | -1.5 | adversarial — suppress frozen, let centroid lead |
| [[magnitude]] | +0.5 | cooperative but mild — frozen direction matters |
| [[frozen coherent]] | +1.0 | cooperative — frozen is trusted |
| [[compressed frozen]] (proposed) | TBD (dominant=-1.5 wins empirically) | G break: even cooperative frozen fails |

## Linked solutions

- [[dominant]] — wf = -1.5
- [[magnitude]] — wf = +0.5
- [[frozen coherent]] — wf = +1.0
- [[cascade v2]] — selects wf based on [[frz_skew]] and [[cen_std]]
