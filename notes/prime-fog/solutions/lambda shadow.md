---
tags: [solution, scout-lane, orthogonal]
---

# lambda shadow

**Type:** standalone sensor lane
**Formula:** PNT/von-Mangoldt based flashlight
**Feature column:** `lambda_gradient_channel`

## What it does

A scouting lane independent of [[frozen gate]] and [[centroid_a]]. Detects structure based on prime counting function / von-Mangoldt weighting in the local field window.

## Known scores

| Ring | Hits | Overlap with frozen |
| --- | ---: | --- |
| [[Ring B]] | 10/227 | zero overlap with frozen's B anchors |

Zero overlap with frozen means lambda shadow is finding completely different rows. This is the scout lane's value — orthogonal evidence.

## Variables it uses

- [[corr_frz_cen]] analogy — lambda shadow is anti-correlated with frozen by design
- `lambda_slope` — the range-level aggregate of this lane

## Limitation

Not yet combined with frozen + centroid into a net-positive ensemble. Standalone it finds real anchors but the quota selector lost frozen hits when lambda was included.

## Related

- [[frozen gate]] — what lambda shadow is orthogonal to
- [[graph map]] — another orthogonal scout lane
- [[CMPSSZ]] — third scout lane
- [[answer backprop distiller]] — attributed which lanes drove which anchors
