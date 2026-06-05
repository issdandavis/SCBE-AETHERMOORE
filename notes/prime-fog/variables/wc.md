---
tags: [variable, blend-weight]
---

# wc (centroid weight)

**Type:** blend formula coefficient
**Formula component:** `score = [[wf]] * frz_z + [[wa]] * |frz_z| + wc * cen_z`

## What it controls

How much the [[centroid_a]] ranker (trained on A=100M-150M, 60% fit) contributes to the final score. Higher wc gives centroid more authority to override frozen gate picks.

## Known per-regime values

| Regime | wc | Interpretation |
| --- | ---: | --- |
| [[dominant]] A-in-sample | 1.5 | centroid moderate |
| [[dominant]] C/E-optimal | 1.0 | centroid mild |
| [[magnitude]] | 2.0 | centroid strong alongside frozen magnitude |
| [[frozen coherent]] | 1.5 | centroid contributing alongside cooperative frozen |

## Tradeoff

Higher wc risks importing the centroid's training distribution (A=100M-150M) into ranges far from A. The centroid generalizes fairly well to B/C/D/E, but shows decay at F (4/231 pure centroid vs frozen's 11/231). The best results use wc to *add coverage* on top of frozen, not replace it.

## Linked solutions

- [[dominant]] — wc = 1.0–2.0 depending on range
- [[magnitude]] — wc = 2.0
- [[frozen coherent]] — wc = 1.5
- [[centroid_a]] — the model that wc scales
