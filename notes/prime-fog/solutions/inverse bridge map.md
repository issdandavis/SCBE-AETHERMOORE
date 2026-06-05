---
tags: [prime-fog, solution, inverse-heisenberg, bridge-map]
updated_at: 2026-06-04
---

# Inverse Bridge Map

## Formalization

```
Normal Heisenberg: cannot know position + momentum simultaneously.
Inverse version:   target position (anchor) is KNOWN.
                   Uncertainty moves backward: which projection fired it?

U(anchor) = entropy(p(c|a)) where p(c|a) ∝ rank_score(c, a)
bridge(c, a) = rank_score(c, a) / U(anchor)

Low U  = clean trajectory, one lane owns the anchor
High U = quantum anchor, multiple lanes dispute it
```

## Key findings (A–G)

### Ring entropy is near-maximum (H ≈ 2.94–2.98 bits)

All rings have nearly uniform hit distribution across 8 controllers. No single lane dominates globally. G is slightly lower (2.84) — the frozen distribution compression starts to collapse the entropy.

### Clean vs quantum breakdown (top-20 union anchors)

| Ring | clean% | quantum% | mean_U | correct_lane |
| --- | ---: | ---: | ---: | --- |
| A | 77.8% | 22.2% | 0.041 | [[dominant]] |
| B | 75.6% | 24.4% | 0.063 | [[dominant]] |
| C | 68.9% | 31.1% | 0.062 | [[dominant]] |
| D | 70.3% | 29.7% | 0.069 | [[magnitude]] |
| E | 69.2% | 30.8% | 0.057 | [[dominant]] |
| F | 81.4% | 18.6% | 0.043 | [[frozen coherent]] |
| G | 81.4% | 18.6% | 0.043 | [[dominant]] |

F and G have the fewest quantum anchors — the distribution is more polarized at higher frz_mean/skew values.

### Controller exclusivity (anchors exclusively owned per ring)

| Controller | A | B | C | D | E | F | G | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **lambda** | 5 | 8 | 8 | 6 | 6 | 8 | **10** | **51** |
| dominant | 6 | 6 | 8 | 7 | 6 | 3 | 6 | 42 |
| frozen | 6 | 9 | 4 | 4 | 2 | 7 | 7 | 39 |
| graph | 5 | 5 | 2 | 6 | 4 | 6 | 6 | 34 |
| cmpssz | 3 | 2 | 2 | 2 | 6 | 4 | 4 | 23 |
| centroid | 1 | 2 | 3 | 0 | 1 | 3 | 0 | 10 |
| magnitude | 1 | 1 | 3 | 1 | 1 | 2 | 2 | 11 |
| frozen_coherent | 1 | 1 | 1 | 0 | 1 | 2 | 0 | 6 |

**Lambda owns the most exclusively** — fires clean, low-U arcs across all rings.  
**Magnitude owns very few exclusively** — its power is in the quantum cluster (shared disputed targets).

### Bridge score totals

| Controller | total bridge |
| --- | ---: |
| **lambda** | **202.2** |
| dominant | 175.5 |
| frozen | 157.0 |
| graph | 129.3 |
| cmpssz | 105.3 |
| centroid | 36.4 |
| **magnitude** | **43.6** |
| frozen_coherent | 25.5 |

Lambda is the canonical-path controller (low-U, clean arcs). Magnitude is the phase-transition controller (fires at compressed-distribution anchors other lanes miss at frz_mean > 0.27).

### The regime controller vs bridge leader split

The cascade picks the controller with the most HITS per ring. But the bridge leader (highest bridge score) is often different:

| Ring | cascade controller | bridge leader | bridge ratio |
| --- | --- | --- | ---: |
| A | dominant | dominant | CONFIDENT |
| B | dominant | frozen (beats dominant 36 vs 18) | WEAK |
| C | dominant | dominant | CONFIDENT |
| D | magnitude | dominant/lambda (beats magnitude 29 vs 8) | WEAK |
| E | dominant | dominant | CONFIDENT |
| F | frozen_coherent | frozen (beats 31 vs 8) | WEAK |
| G | dominant | lambda (beats dominant 43 vs 25) | WEAK |

**Pattern**: the regime controller fires the most hits, but is often not the cleanest firing arc. The bridge map reveals the "cleanest path" separately from the "most productive path."

## The quantum cluster at anchor 411142427

This is the specific anchor the user identified:  
- centroid rank 1  
- graph near (rank 1 in top-50)  
- frozen_coherent also sees it  
- magnitude also sees it

U=1.566 — three lanes partially claim it. Classic inverse Heisenberg: position known, trajectory uncertain.

This anchor sits at a "node" in the prime distribution where multiple projection geometries align. It appears in the G quantum cluster, suggesting it's in a regime transition zone.

## Implications for Ring I

- Feature trajectory: frz_mean≈0.44, frz_std≈0.81 (laser-straight trend, r²=0.998)
- Lambda expected bridge score: ~43 (similar to G)
- Magnitude expected bridge score: ~6 (similar to G)
- BUT: magnitude is the HITS winner for I (trajectory gap map predicts wf=-0.24, wa=+2.46)

**Resolution of the tension**: lambda fires MORE clean arcs overall, but magnitude hits the specific family of anchors that the compressed-frozen distribution reveals. At frz_mean=0.44, the magnitude signal becomes the dominant discriminator for hits.

## Artifact

`artifacts/inverse_bridge_map/bridge_map.json`  
Script: `scripts/research/inverse_bridge_map.py`

## Related

- [[trajectory gap map]] — source of ring I weight prediction
- [[frz_mean]] — the core drift axis (r²=0.998)
- [[wa]] — the weight that needs to activate at frz_mean > 0.27
- [[Ring I]] — uncertainty boundary
- [[cascade v4]] — frozen rule update that closes the gap before Ring I truth is checked
