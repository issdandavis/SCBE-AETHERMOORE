# Instrument Family for Geometric Claims

> **Every instrument must ship with its own null hypothesis.**
> Without the null, these are metaphors. With the null, they are instruments.

A geometric claim is not "interesting structure." It is a measurement that survives
a stack of falsification gates. Each tool below states the condition under which it
is *not* useful — and you run them **in order**, stopping at the first failure.

| Instrument | Purpose | Pass condition | Null / failure gate |
|---|---|---|---|
| Ruler | Measure distance/structure | Stable measurement | Different rulers disagree |
| Level | Test frame invariance | Same result under reframing | Frame-dependent drift |
| Caliper | Compare ratios/scales | Relative structure preserved | Ratio instability |
| Calibration Standard | Verify against known truths | Known cases pass | Known cases fail |
| Congruence Test | Check geometric legitimacy | Möbius invariance | Coordinate dependence |

Code: `scripts/research/` — `nature_ruler_tool.py` (ruler/caliper/zoom), `nature_ruler.py`
(level), `calibrate_ruler.py` (calibration), `hyperbolic_ruler.py` (congruence). All
self-checking; all verified the dates below.

---

## 1. Ruler — measurement
Lay quantities on one line; read each as a ratio off a seed. Pass: the reading is
stable and reproducible. Null: two valid rulers (e.g. two seeds, two scales) disagree
on the same relationship → there is no measurement, only an artifact of the choice.

## 2. Level — invariance
Re-read the same thing under a transformation of the tool. Pass: same result. Null:
the result drifts with how you held the tool. *A carpenter's level doesn't prove
gravity exists; it proves the measurement is independent of how you hold it.*

## 3. Caliper — ratio
Compare scales/ratios, not absolutes. Pass: relative structure is preserved under
rescaling. Null: the ratio is unstable → you were reading units, not structure. The
caliper also reports a **trust**: a snapped ratio (3:2) without its residual is a
decimal in disguise. φ never trusts shallow — its zoom is all-ones, worst-approximable.

## 4. Calibration Standard — known truths
Fine-tune against exact, independently-verifiable references, **validating on a
held-out set** so it is calibration not overfit. Pass: known cases pass; the device
earns a *certified tolerance*. Null: known cases fail → the instrument is uncalibrated.
Demonstrated: primes as the standard (exact, infinite ladder); calibrating the
offset-ruler dropped held-out prime-prediction error 4.5% → 1.1% (±2.4% certified).

## 5. Congruence Test — geometric legitimacy
Apply the space's isometries (Möbius, in the Poincaré ball) and measure with the true
metric vs a naive one. Pass: the true metric is invariant. Null: coordinate dependence.

**The Hyperbolic Level (run 2026-06-09).** Points in the ball → 6 Möbius reframes →
measure with `d_H = arcosh(...)` vs Euclidean:
- hyperbolic drift ≈ **1.78e-15** (invariant)
- euclidean drift ≈ **5.7e-1** (frame-dependent)

Interpretation: `d_H` measures something geometric; the Euclidean reading measures a
coordinate artifact. That is exactly what a level does.

## 6. Inner-Dimension Gate — earn the curvature
The most important gate. **Invariance proves the metric, not the necessity of the
space.** A perfect hyperbolic ruler can still be useless: if the data is fundamentally
flat, a Euclidean embedding works and the curved one adds only empty volume. So require
*evidence the curvature pays*: better compression, lower distortion, hierarchy recovery,
improved routing/prediction. If none appears, **Curvature Benefit ≈ 0** and the geometry
is decorative. This gate kills almost every "everything is hyperbolic" failure mode.

## 7. SCBE Diagnostic Example — confirmed on the live gate
The production gate's `_harmonic_cost` in `src/governance/runtime_gate.py` is a
**phi-weighted Euclidean centroid distance**, not `arcosh` `d_H`:

```text
weighted_dist = sqrt(sum_k phi^k * (coords_k - centroid_k)^2)
cost = pi^(phi * min(weighted_dist, 5.0))
```

That diagnostic is now empirically confirmed against the live function, not just
inferred from docs. A direct test was added in
`tests/governance/test_patent_math_support.py`:

- true `d_H` between a centroid-point pair stays invariant under 6 Möbius reframes
  to machine precision (`< 1e-12`)
- the live gate's `_harmonic_cost` over the same reframed pair drifts by about `1.17`
- independently reproduced in 6-D by `scripts/eval/gate_mobius_invariance.py` (calls the
  live `_harmonic_cost`, fidelity-checked to <1e-9): true d_H drift `4.4e-16`, gate metric
  drift `0.40`, live gate **cost drift 52%** under isometries that leave d_H invariant.
  Two independent Möbius implementations (2-D complex + 6-D gyrovector), same verdict.

So the gate cost is a real, monotone surrogate score, but it is **not** Möbius-invariant
hyperbolic distance. In the language of this suite:

- true `d_H` → passes congruence
- runtime `_harmonic_cost` → fails congruence

That does not make the gate useless. It means the gate should be described honestly as a
weighted centroid-drift cost, not as a frame-free hyperbolic metric.

## 8. Negative Results and Failed Geometries
Logged cases where these gates (or their null-test ancestors) killed a geometry that
looked load-bearing. Kept so the suite is not graded only on its wins:
- **Spin-voxel** — magnetic structure was decorative for cost; shuffle and scalar nulls
  reproduced the ratio. (Fails: stability/ratio.)
- **Corridor-ranker** — reduced to goal-token overlap; the realized safety came from a
  hard next-step filter, not the score. (Fails: the score had no invariant content.)
- **Gate `d_H`** — phi-weighted-Euclidean surrogate, not the invariant arcosh metric.
  (Fails: congruence — see §7.)
- **Prime-fog "top-20-unique"** — density-saturated; IP and RR lanes ≈ null. (Fails:
  the measurement was an artifact of a crowded line, not structure.)
- **Prime-rationing (lengths/radices/couplings)** — decorative across four tools;
  reduces to coprimality, or the work is done by nonlinear dynamics. Primes pay
  ONLY for (a) Fermat angles/constructibility and (b) coprime-residue exact
  computation (CRT/RNS/NTT). Full synthesis: `prime_structure_load_bearing_map.md`.

The pattern in every failure: a feature that looked geometric was reproduced by a
null that destroyed the supposed structure. The gates are these nulls, made standing.

## 9. Rules for Future Geometry Claims
Run the gates **in order**; stop at the first failure.
1. **Measurement** — can the thing be measured at all? If not, stop.
2. **Stability** — does the measurement survive repetition / different valid tools? If not, stop.
3. **Ratio** — do relationships survive rescaling? If not, stop.
4. **Calibration** — does it pass known examples, held-out? If not, stop.
5. **Congruence** — does it survive reframing (isometry-invariant)? If not, stop.
6. **Earn the curvature** — only *now* ask if the structure is useful (compression,
   hierarchy, prediction). No benefit ⇒ decorative.

Most speculative geometry starts at step 6. The discipline is forcing 1–5 first.
And the rule that makes it all hold: **every instrument ships with its own null.**
