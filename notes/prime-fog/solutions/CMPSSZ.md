---
tags: [solution, scout-lane, orthogonal]
---

# CMPSSZ

**Type:** standalone sensor lane
**Full name:** Cross-Manifold Phase-Shifted Zone scorer
**Feature column:** `cmpssz_log_zone_score`

## What it does

Fourth independent scout lane. Operates in a different geometric space than [[frozen gate]], [[lambda shadow]], and [[graph map]]. Uses phase-shifted zone scoring across the local field manifold.

## Known scores

| Ring | Hits | Overlap with frozen |
| --- | ---: | --- |
| [[Ring B]] | 12/227 | mostly non-overlap |
| [[Ring C]] | 8/256 | mostly non-overlap |
| [[Ring D]] | 11/220 | mostly non-overlap |

CMPSSZ on D (11/220) almost matches frozen (7/220) + dominant blend. This makes it a candidate for D-regime support.

## Range-level aggregate

`cmpssz_density` = mean(`cmpssz_log_zone_score`) across all rows in a range.

| Range | cmpssz_density |
| --- | ---: |
| F | −5.8007 (most negative — this range has the most zone activity?) |

## Related

- [[lambda shadow]] — sibling orthogonal lane
- [[graph map]] — sibling orthogonal lane
- [[answer backprop distiller]] — used to attribute which lane owned which anchor
