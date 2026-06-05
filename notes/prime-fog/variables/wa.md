---
tags: [variable, blend-weight]
---

# wa (frozen absolute magnitude weight)

**Type:** blend formula coefficient
**Formula component:** `score = [[wf]] * frz_z + wa * |frz_z| + [[wc]] * cen_z`
**Range used:** ≥ 0 (magnitude reward, always positive)

## What it controls

Rewards rows where the frozen gate has *strong opinion in either direction* — high absolute z-score regardless of sign. When wa > 0, rows that the frozen gate is strongly positive OR strongly negative about get a boost.

## Known per-regime values

| Regime | wa | Interpretation |
| --- | ---: | --- |
| [[dominant]] | 0.0 | pure directional — magnitude doesn't add |
| [[magnitude]] | 2.0 | strong magnitude reward — the D-anomaly key |
| [[frozen coherent]] | 0.0 | direction only, no magnitude reward |
| [[compressed frozen]] (proposed) | TBD | |

## The D-anomaly insight

D is the only range where wa > 0 is beneficial. On D, the frozen gate's absolute z-score contains information the direction alone doesn't — rows where frozen is strongly negative are still anchor-adjacent in D. This is what makes D anomalous: the *certainty* of frozen's wrong-direction picks is a signal.

## Linked solutions

- [[magnitude]] — the only regime where wa contributes
- [[dominant]], [[frozen coherent]] — wa = 0
