---
tags: [solution, baseline, controller]
---

# frozen gate

**ID:** `igct_c4_g5_c0.65_g0.05-0.6_geo0.25_cas0_ch0_fb0_bb0`
**Type:** standalone gate (no blend)
**Artifact:** `artifacts/map_reader_gate/gate_v1.json`

## What it does

A conservative pre-built gate with fixed weights. Scans local field structure around each candidate row and returns a raw score. No learning — pure rule-based structure detection.

## Scores by ring

| Ring | Hits | Total |
| --- | ---: | ---: |
| [[Ring A]] | 8 | 235 |
| [[Ring B]] | 11 | 227 |
| [[Ring C]] | 6 | 256 |
| [[Ring D]] | 7 | 220 |
| [[Ring E]] | 6 | 224 |
| [[Ring F]] | 11 | 231 |
| [[Ring G]] | 10 | 214 |

## Role in the system

The baseline every other solution is measured against. A solution that falls below frozen on any board is a regression.

**Interesting observation:** frozen is strong on B (11/227) and F (11/231), weak on C (6/256) and E (6/224). This variance motivates the regime classifier — different boards call for different controllers.

## Variables it uses

- [[frz_skew]] — its distribution is what the classifier reads
- [[frz_mean]] — g-split signal
- [[frz_std]] — g-split signal
- [[NEG_INF]] — sentinel handling

## Related

- [[dominant]] — blends frozen adversarially with centroid
- [[frozen coherent]] — blends frozen cooperatively with centroid
- [[cascade v2]] — routes which blend to apply per ring
