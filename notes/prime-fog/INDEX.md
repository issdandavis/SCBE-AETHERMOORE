---
tags: [prime-fog, index, home]
updated_at: 2026-06-04
---

# Prime Fog — Knowledge Graph

P(P(n)) superprime prime gap field search. Known-solution trajectory problem.

Source ring map: `docs/research/prime_fog_known_solution_rings_2026-06-04.md`

---

## Rings (verifier boards)

| Ring | Range | Anchors | Regime | Status |
| --- | --- | ---: | --- | --- |
| [[Ring A]] | 100M–150M | 235 | [[dominant]] | calibration |
| [[Ring B]] | 150M–200M | 227 | [[dominant]] | consumed |
| [[Ring C]] | 200M–250M | 256 | [[dominant]] | consumed |
| [[Ring D]] | 250M–300M | 220 | [[magnitude]] | consumed |
| [[Ring E]] | 300M–350M | 224 | [[dominant]] | consumed |
| [[Ring F]] | 350M–400M | 231 | [[frozen coherent]] | consumed |
| [[Ring G]] | 400M–450M | 214 | [[compressed frozen]] | consumed |
| [[Ring H]] | 450M–500M | 221 | [[magnitude]] (late compressed) | consumed — v3 FAILED |
| [[Ring I]] | 500M–550M | 204 | [[compressed_frozen_late]] | consumed — v4 partial, IP union 17 |
| [[Ring J]] | 550M–600M | 206 | [[magnitude]] (v4 + v5) | consumed — v4 CORRECT, v5 VALIDATED |
| [[Ring K]] | 600M–650M | 179 | [[frozen_dominant]] (new regime) | consumed — v5 PASS; frozen wins outright (+1) |
| [[Ring L]] | 650M–700M | 178 | [[frozen_dominant]] | consumed — frozen wins +8; v6 CONFIRMED 2/2; alternation FALSIFIED |
| [[Ring M]] | 700M–750M | ? | [[frozen_dominant]] projected | **NEXT — UNSEEN; manifold projection only** |

---

## Solutions (controllers)

| Solution | Regime | Key variable |
| --- | --- | --- |
| [[frozen gate]] | baseline | — |
| [[dominant]] | default | [[frz_skew]] < threshold |
| [[magnitude]] | D-anomaly | [[cen_std]] < 0.97974 |
| [[frozen coherent]] | high-skew, normal dist | [[frz_skew]] > 0.4495 |
| [[compressed frozen]] | high-skew, compressed dist | [[frz_mean]] > 0.15 AND [[frz_std]] < 0.95 |
| [[centroid_a]] | learned model | [[corr_frz_cen]] |
| [[lambda shadow]] | scout lane | orthogonal to frozen |
| [[CMPSSZ]] | scout lane | orthogonal to frozen |
| [[answer backprop distiller]] | diagnostic only | calibration |
| [[trajectory gap map]] | meta-tool | measures off-course error in weight space |
| [[manifold navigator]] | meta-tool | embeds A-L feature geometry and reads next-ring direction |
| [[inverse bridge map]] | meta-tool | inverse Heisenberg — maps trajectory uncertainty backward from known anchors |
| [[inverse prime field]] | ninth controller | τ-based hub-to-prime path energy; Ring I IP=9 and v4 OR IP union=17 |
| [[prime truth oracle]] | verifier | exact `is_prime_u64`, next-prime, segmented-prime, artifact anchor checks |

---

## Variables (gravity wells)

Distribution shape:
- [[frz_skew]] — frozen right-tail asymmetry — regime axis 2
- [[frz_mean]] — frozen distribution shift — G-split
- [[frz_std]] — frozen distribution width — G-split
- [[cen_std]] — centroid distribution width — regime axis 1
- [[corr_frz_cen]] — frozen/centroid anti-correlation
- [[NEG_INF]] — sentinel handling

Blend weights:
- [[wf]] — frozen direction weight (negative = adversarial)
- [[wa]] — frozen magnitude weight (D-anomaly only)
- [[wc]] — centroid weight

---

## Cascades

| Version | Regimes | Status |
| --- | --- | --- |
| [[cascade v2]] | dominant / magnitude / frozen_coherent | active, fails on G |
| [[cascade v3]] | + compressed_frozen | FAILED on H (wa=0 miss) |
| [[cascade v4]] | + compressed_frozen_late (magnitude) | PARTIAL: beats frozen, misses dominant win in I |
| [[cascade v5]] | + frz_kurt < 0.80 joint condition | kurt THRESHOLD 3/3 (H/I/J); superseded by v6 once skew>1.0 |
| [[cascade v6]] | + frozen_dominant (frz_mean>0.45 AND frz_skew>1.0) | PRE-REGISTERED, blind PASS at L (+8); 5/5 total |

---

## Failures (lessons)

- [[ABC retraining]] — mixing heterogeneous boards kills discriminative signal
- [[G break frz_skew was not enough]] — single-axis threshold insufficient
- [[RRF ensemble]] — rank fusion without orthogonality enforcement fails

---

## Game loop

```
old rings → reverse into pre-anchor rule → freeze rule → test on next unseen ring
```

A rule is only real when frozen before the next board. In-sample ceiling is not a score.
