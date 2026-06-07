---
tags: [prime-fog, index, home]
updated_at: 2026-06-04
---

# Prime Fog — Knowledge Graph

P(P(n)) superprime prime gap field search. Known-solution trajectory problem.

Source ring map: `docs/research/prime_fog_known_solution_rings_2026-06-04.md`

> **Capstone:** [[PRIME_FOG_SECOND_LANE_PROGRAM_SUMMARY]] — second-lane search is CLOSED
> (frozen+density is floor-and-ceiling, confirmed from ring-gating AND exact-sequence sides).
> Read that one doc for the whole program.

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
| [[Ring M]] | 700M–750M | 202 | ~~frozen_coherent (regime flip)~~ NO FLIP under count-proxy | consumed — top-20 "coherent won" was scatter-reward; count-proxy: frozen≈coherent, gap is blend wobble (31% random-reweight ≥ coherent) |
| [[Ring N]] | 750M–800M | 180 | ~~frozen_coherent~~ frozen wins robustly (8/8 configs) | consumed — top-20 "coherent won 13/10" was dead metric; count-proxy: frozen wins every config |
| [[Ring O]] | 800M–850M | ? | confirmation-only (flip dissolved); needs a falsifiable prediction before build | **NEXT — UNSEEN; build NOT yet justified (OOM risk)** |

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
| [[inverse prime field]] | ~~ninth controller~~ FALSIFIED | IP=9/union=17 was a density artifact (0.9× null); see [[null floor metric audit]] |
| [[anchor count proxy]] | meta-tool (canonical metric) | NMS-deduped precision; frozen beats null95 on all K–N; use this, NOT top-20-unique |
| [[RR extraction lane]] | ~~residue lane~~ FALSIFIED | rr_sqrt1 = 1.0× null at top-20; at/below null under count-proxy on 3/4 rings |
| [[replacement router audit]] | router audit | density+RR; per-ring α overfit + rr-at-null → needs random-re-ranker null before classifier |
| [[null floor metric audit]] | methodology | top-20-unique is null-saturated; count-proxy survives; null-check every lane |
| [[prime truth oracle]] | verifier | exact `is_prime_u64`, next-prime, segmented-prime, artifact anchor checks |
| [[calibration targeting reframe]] | methodology + exact sequence probe (both forks CLOSED) | hide-and-recover objective. BOTH levers dead on P(P(n)): (1) gap-trajectory geometry — joint multi-feature, density-controlled, adds +0.24% over PNT (caught a flat-baseline trap where log-p density masqueraded as signal); (2) residue-lane ranking — mod 6/30/210 lanes are uniform AND serially independent (conditioning worse held-out); LO–S does NOT transfer to superprimes. (3) long-range/spectral — periodogram flat (no periodicity); only real effect is KNOWN gap-repulsion (lag-1 ACF ~−0.08, present in raw primes too, decays with scale, R²<1% = negligible). **Search cone = density envelope; no sub-density aiming signal. Converges with [[null floor metric audit]]: frozen+density is the floor from both directions.** |
| [[second lane closure]] | decision record | Second-lane targeting search is CLOSED. Row-cache lanes all fail proper nulls; exact-sequence targeting reduces to density; rotated log-frame/Riemann-zero structure is counting structure, not a local targeter. Final windowed spectrum: raw primes show 15.63x zeta-comb localization; `P(P(n))` shows 1.21x inside null, so no detectable superprime comb. |
| [[prime alignment ledger]] | substrate + axis gate | exact per-anchor truth (gaps/ratios/residues/π) + the gate every new axis must clear before becoming a search lane: precision>null_p95 AND \|count_err\|≤30% on EVERY ring. Self-validated: frozen ELIGIBLE, rr REJECTED |
| [[geometric alignment axes]] | diagnostic coordinates | log3/log4 and golden spiral are anti-aligned/dead; gap acceleration's edge is count-inflation (over-predict is 96% scatter not slope — detrend makes it worse; at count-honest threshold precision → null in-sample AND fails K→L/M transfer). |
| [[prime ratio transition graph]] | diagnostic transition graph (FALSIFIED) | ratio_curvature rejected; ratio_graph_resonance's count-honest "9/14 beats null" was a value-shuffle confound (smooth score → shuffle over-predicts clusters); under the count-matched **circular-shift null it beats 0/14**. Dead lane, same disease as gap_acceleration. |
| [[residue wheel axis]] | exact arithmetic axis (FALSIFIED) | residue_wheel_frequency uses `scan_prime mod 210`; below null and count-dishonest on K-N. `pi(p)` remains ledger truth only, not a non-leaking row score. |
| [[numerical emulsion axis]] | factor-pressure collar (FALSIFIED) | numerical_emulsion measures tau pressure around `scan_prime +/- 1..6`; below null and count-dishonest on K-N. Useful substrate metaphor, not a standalone lane. |
| [[prime circuit geometry]] | circle-of-fifths analogue (FALSIFIED) | prime_circuit_geometry folds `scan_prime mod 210` onto a log-radius wheel and scores local bend; weak K/N flicker, but fails L/M precision and over-predicts every ring. |
| [[prime alphabet circuit]] | symbolic compression map | Behavior-derived letters plus 26x26 rotating alphabet circuit. Clears same-inventory shuffle on most encodings, proving order information exists; strongest signal is known modular/wheel structure, so this is visualization/compression, not a targeting lane. |
| [[prime color circuit]] | visualization layer | Colorized prime circuits rendered as SVG panels. Includes discrete residue/gap/wheel colors and floating derivative colors (`gap_ratio`, `log_step`, `ratio_curvature`, `gap_acceleration`). Scouting map only; visible patterns still need null gates. |
| [[mod layers]] | modular gate stack | Exact sieve/wheel cone map. On 100k-1M, layers through 47 keep recall 1.0 and raise precision 7.66%→55.19%; modulus 210 already gets to 2.99 candidates/prime. Roads/closed-bridges map, not a new local targeter. |
| [[circle inscription geometry]] | geometric rotation closure | Radius-p circle boundary recovers Fermat two-squares/mod-4 structure (12 points for p≡1 mod4, 4 for p≡3 mod4); interior count lands on the Gauss-circle square-root discrepancy wall. Known structure, no targeter. |
| [[PRIME_FOG_SECOND_LANE_PROGRAM_SUMMARY]] §5b–5f | address tower + shadow/scaling/circle closure | Prime "address" decomposes in dual log/mod frames and geometric circle frame. Log layers recover Riemann-zero decimals; mod layers recover primorial wheel lanes; scaled seed is constructor-only; scaling trichotomy exhausts divisors; circle inscription recovers Fermat mod-4 + Gauss-circle wall. All peel KNOWN structure to the same incompressible wall. |
| [[geoseed prime seed init]] | constructive handoff | Deterministic GeoSeed/M6 initializer for the scaled prime seed. Maps KO..DR to mod layers 2,3,5,7,11,13 and emits smooth address center + wall window + wheel lanes. Constructor only, not prime selection. Now defaults to a PROVEN Dusart/Rosser-Schoenfeld bracket (guaranteed containment); old sigma window is opt-in `mode="tight"` and not guaranteed. |
| [[prime spacetime atlas]] | truth map (constructor) | `src/geoseed/prime_atlas.py`: per-prime multi-coordinate ADDRESS (value/index/gap/ratio/residues/log/wheel-lane/AP) carrying each coordinate's VERDICT — FACT / KNOWN_STRUCTURE / FALSIFIED_PROJECTION — so hallucinated geometry (curvature, gap-transition graph) is shown not hidden. Green-Tao prime-AP is the straight-line KNOWN_STRUCTURE coordinate. `alignment_vs_null` (circular-shift default) is baked in as the real-vs-hallucinated test. `build_prime_seed_region(index)` now wires the proven seed bracket to exact atlas addresses and nearby survived structures inside the candidate field. Build the map before the pathfinder. |
| [[prime manifold projection]] | atlas view (truthful) | `src/geoseed/prime_manifold.py`: PCA/graph projection of the atlas address space. Refuses FALSIFIED coordinates by default; every axis named via loadings; `alignment_vs_null` gates any visible cluster. Shows the closure: WIDE range → PC1 = SCALE (PC1↔log_value 0.93 beats null); NARROW window → featureless cloud (PC1↔log_value 0.049 ≈ noise floor) = the wall made visible; graph clusters only on known wheel/AP structure. Makes the wall visible, opens no lane. |
| [[row-cache channel re-gate]] | 6 legacy families re-gated under circular-shift null (FALSIFIED) | CMPSSZ/cassette + hyperbolic/topology re-tested on 14 rings @ count-honest, both orientations. **topo_score/asymmetry/confidence 0/14 (stone dead); gravity_score 1/14; cassette best (adj_channel) 5/14@S60 vs 4/14@S40 on DIFFERENT rings = seed-unstable = noise.** No channel clears majority. future_* columns disqualified (leakage). |

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
| [[cascade v6]] | + frozen_dominant (frz_mean>0.45 AND frz_skew>1.0) | FALSIFIED at M and N; trigger right, winner wrong |
| [[cascade v7]] | hypothesis: high-mean / falling-spike exit from frozen_dominant | UNCOMMITTED — 2 points (M/N); corr-only split rejected |

---

## Failures (lessons)

- [[ABC retraining]] — mixing heterogeneous boards kills discriminative signal
- [[G break frz_skew was not enough]] — single-axis threshold insufficient
- [[RRF ensemble]] — rank fusion without orthogonality enforcement fails
- [[frozen_dominant overfit]] — committed on 2 points (K/L, mostly L's fluctuation); falsified at M and N. Same error class as the period-2 alternation. ≥5 points before committing a NEW regime rule.
- [[null floor metric audit]] — top-20-unique-anchor is null-saturated (rewards scatter under 52% density); no controller/lane beats random on it. IP=9 and RR union were artifacts. ALWAYS run a `random.shuffle` null (clear null p95 every ring) before believing a lane. Frozen survives only under the NMS count-proxy.

---

## Game loop

```
old rings → reverse into pre-anchor rule → freeze rule → test on next unseen ring
```

A rule is only real when frozen before the next board. In-sample ceiling is not a score.
