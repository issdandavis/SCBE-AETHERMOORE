---
tags: [prime-fog, solution, inverse-prime, new-lane]
updated_at: 2026-06-04
---

# Inverse Prime Field

## Formalization

```
prime       = sink   (τ(p) = 2, isolated endpoint)
composite   = medium (τ(n) > 2, interference layer)
inverse-prime = source/hub (τ(n) >> 2, highly composite attractor)

Arithmetic laser path:
  source (hub) ──composite medium──> prime anchor (sink)

IP(n) = τ(n)          — source intensity
P(n)  = 1/τ(n)        — sink isolation

hub_gradient(anchor) = τ_hub * exp(-hub_distance / decay)
path_energy(anchor)  = Σ τ(n) * exp(-(p - n) / decay)
```

## Key findings (A–G)

### IP lane anchor_ratio vs existing union

| Ring | union_mean_ratio | ip_unique_mean | gap |
| --- | ---: | ---: | ---: |
| A | +3.46 | +0.68 | **−2.78** |
| B | +1.17 | +2.92 | **+1.75** |
| C | +2.00 | +2.48 | **+0.49** |
| D | +1.94 | +3.89 | **+1.95** |
| E | +3.55 | +2.65 | **−0.90** |
| F | +2.60 | +2.47 | **−0.14** |
| G | +4.16 | +2.83 | **−1.32** |

**IP lane beats the existing union in rings B, C, D.**  
Ring D (magnitude regime) has the strongest beat: +1.95. This is not a coincidence — the magnitude regime is the one where divisor/density structure dominates the signal.

### The G inversion

In rings A–F, quantum anchors have HIGHER hub_gradient than clean anchors.  
In ring G (compressed_frozen), the polarity FLIPS: clean=31.1, quantum=10.6.

**Interpretation:**  
- Classical regime (A–F): strong divisor path → clear single-lane ownership (low U)  
- Compressed-frozen regime (G): the disputed quantum anchors sit at the END of WEAK divisor paths. The "quantum" arises from a different cause — multiple lanes geometrically close to the anchor, NOT from strong divisor field.

This means in G, IP gradient is a CLASSIFIER for ownership type:
- High gradient → clean single-owner anchor
- Low gradient → quantum multi-owner anchor

### The quantum anchor 411142427

- hub_gradient = 10.049 (low — below G clean mean of 31.1)
- hub_τ = 192, hub_dist = 59
- τ(p-1) = 8 (low — p-1 is itself nearly prime-like)
- owners = [centroid, frozen_coherent, magnitude]

τ(p-1) = 8 means p-1 is divisor-sparse. The anchor is at the end of a WEAK path. Its "quantum" character comes from geometry (multiple lanes near it), not from divisor structure.

## Regime correlation

| Regime | IP unique beat | Implication |
| --- | --- | --- |
| dominant (A, B, C, E) | mixed (B, C beat; A, E miss) | IP not regime-correlated |
| **magnitude (D)** | **+1.95 (strong beat)** | **IP aligns with magnitude** |
| frozen_coherent (F) | −0.14 (neutral) | IP near-orthogonal |
| compressed_frozen (G) | −1.32 | IP loses to high-bar union |

The magnitude regime is where divisor structure matters most. IP lane + magnitude controller = natural pair.

## Lane scoring formula (for row-cache integration)

```python
lane_score(row) = (
    α * hub_gradient(ahead_window)         # source → sink path quality
  + β * tau_mean_ratio(scan_zone)          # local composite density
  + γ * lambda_residual(row)               # cross-manifold residual
  + δ * phase_alignment(row)               # phase drift toward anchor
)
```

Calibrate (α, β, γ, δ) on A-G; freeze before Ring I.

## Ring I live result

Ring I was the first live test after the A-G postmortem.

Protocol: score [[cascade v4]] first, then add IP as a ninth controller.

| Method | Unique anchors | New vs cascade v4 |
| --- | ---: | ---: |
| frozen baseline | 6/204 | 5 |
| cascade v4 | 8/204 | 0 |
| inverse-prime lane | 9/204 | 9 |
| cascade v4 OR inverse-prime | **17/204** | **9** |

Result: IP found nine anchors cascade v4 missed:

`502890457, 504981319, 508554341, 517610881, 531287093, 531983927, 541747093, 547155109, 548532323`

This validates IP as a genuinely orthogonal ninth controller on the next unseen ring.

Artifact: `artifacts/ring_i_cascade_v4_ip/RESULTS.md`

## Integration path

1. Add segmented τ sieve to row-cache builder  
2. Compute `hub_gradient` channel per scan row using ahead window  
3. Score candidates, take top-20, compare union coverage  
4. Calibrate weights on A-G, freeze before Ring I  

## Artifact

- `artifacts/inverse_prime_field/field_v1.json`
- Script: `scripts/research/inverse_prime_field.py`

## Related

- [[inverse bridge map]] — partner tool: τ(p-1) low = quantum anchor (G finding)
- [[trajectory gap map]] — magnitude regime prediction for Ring I
- [[Ring I]] — first live test of the IP lane; IP adds 9 disjoint anchors
- [[magnitude]] — the regime where IP aligns most strongly (D: +1.95)
- [[cascade v4]] — if IP lane fires in compressed-frozen, it's a signal for wa activation
