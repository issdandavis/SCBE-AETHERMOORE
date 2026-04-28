# ACV Continuous-Margin Diagnostics — v1

**Solicitation:** DARPA-PA-26-05 (MATHBAC), Technical Area 1
**Performer:** SCBE AetherMoore (UEI J4NXHM6N5F59, CAGE 1EXD5)
**Date:** 2026-04-27
**Parent artifact:** `proposer_metrics_specs_v1.md` §3.2 (ACV) and §5 (open follow-up)
**Status:** Internal supplement to ACV. Held for triage during Phase I tuning. **Not part of the rubric ACV** that is evaluated against the rubric.

---

## 0. Why this exists (and why it is not the rubric)

`proposer_metrics_specs_v1.md` §3.2 declares ACV as a binary 14×5 (layer × axiom) compliance matrix. The Limits paragraph there is explicit:

> "ACV as a binary matrix does not graduate severity: a Locality near-miss at L3 and a Composition catastrophic failure at L14 both count as one cell failure. Where severity matters (e.g. for triage during Phase I tuning), the proposal supplements ACV with the per-axiom continuous-margin diagnostics held internally; those are not part of the rubric ACV."

This artifact is that supplement. It exists to answer one question: *when an ACV cell fails, by how much did it fail?* Answering that is essential for tuning during Phase I (where to put effort) and for the M0–M4 Living Metric narrative (improvement direction). It is **not** essential for promotion: rubric ACV is binary by design (`feedback_asymmetric_weighting.md` — safety/structural gates weight as binary; severity weights as continuous components *inside* the gate), and this artifact does not change that.

Two consistency rules govern this artifact:

1. **It cannot soften the rubric.** A passing continuous margin does not promote a binary fail to a binary pass. The binary cell remains the rubric.
2. **It cannot inflate the rubric.** A continuous-margin near-miss does not get rolled up into the rubric ACV scalar. The rubric ACV scalar is the fraction of bound (layer, axiom) pairs whose binary cell passes.

The continuous margins are reported alongside ACV at each Living Metric milestone, in a separate diagnostic table.

---

## 1. The five-axiom mesh and its bindings

Per `CLAUDE.md` and `proposer_metrics_specs_v1.md` §3.2, the five-axiom mesh binds across the canonical 14-layer pipeline as follows. (This is the same Table 3.1 referenced by the ACV mechanism; reprinted here so the diagnostic schema is self-contained.)

| Axiom | Bound layers | Property under test |
|---|---|---|
| Unitarity | L2, L4, L7 | Norm preservation across the layer transform |
| Locality | L3, L8 | Spatial bound (e.g. Poincaré-ball containment, well-region containment) |
| Causality | L6, L11, L13 | Time-ordering / monotone phase advance |
| Symmetry | L5, L9, L10, L12 | Gauge / group-equivariance under declared symmetries |
| Composition | L1, L14 | End-to-end pipeline integrity (entry encoding ↔ exit decoding) |

Cells outside this binding table are **N/A** in both the rubric ACV and this diagnostic. They do not have a continuous margin; they are not evaluated.

---

## 2. The eight-field specification

Carrying the same rigor standard as `proposer_metrics_specs_v1.md` §3.

### 2.1 ACV-CM (Axiom Compliance Vector — Continuous Margin)

**Name.** ACV-CM — per-cell continuous margin supplement to the rubric ACV.

**Definition.** For each bound (layer, axiom) cell, ACV-CM is a scalar **m ∈ [0, 1]** where `m = 1.0` corresponds to perfect compliance under floating-point tolerance and `m → 0` corresponds to a catastrophic violation. The per-axiom formulas are in §3.

**Mechanism.** The cell's continuous margin is computed during the same evaluation pass that produces the binary ACV cell, on the same sealed test corpus, with the same pre-registered thresholds. The binary cell is `pass` iff `m ≥ 1 − τ_axiom` where `τ_axiom` is the per-axiom rubric tolerance (declared at M0 and frozen for the program). Margins below `1 − τ_axiom` are binned by severity (§4) for triage but the binary cell remains a fail.

**Inputs.** Identical to ACV: sealed test corpus of N ≥ 500 protocol exchanges with ground-truth admit/reject labels, PRNG seed locked at M0.

**Outputs.** The 14 × 5 continuous-margin matrix (with N/A cells preserved) plus the binary 14 × 5 ACV matrix recovered from it via thresholding. The continuous matrix is logged; only the binary matrix and its rolled-up scalar are reported in the rubric.

**Test.** Pre-registered: the rubric tolerance `τ_axiom` per axiom is locked at M0. The continuous margin is recomputed on every sealed-blind evaluation pass and the diagnostic table refreshed. The diagnostic table is shown alongside the rubric ACV at every Living Metric milestone.

**Falsifier.** ACV-CM does not have an *additional* falsifier beyond the rubric ACV: the rubric ACV cell-fail falsifier in §3.2 is the program-level falsifier. ACV-CM has an *internal* tuning falsifier: if an axiom's continuous margin worsens monotonically from M0 → M1 → M2 across consecutive evaluations on the same sealed corpus, the tuning loop is moving in the wrong direction and the loop must be paused for review. This is a *process* falsifier, not a rubric falsifier.

**Scope.** ACV-CM is defined for the canonical 14-layer pipeline and the five-axiom mesh per the binding table in §1. It applies only to *bound* (layer, axiom) cells. It is not portable across pipelines that omit a layer or rebind an axiom. The continuous-margin formulas in §3 are *axiom-specific*; replacing a per-axiom formula requires an amendment to this artifact.

**Limits.** The continuous margin is a *floating-point* quantity bounded in `[0, 1]` after clipping; numerical underflow at the upper bound (margin = 1.0 exactly) is not distinguishable from `1.0 − ε` and the binary cell rules in §4 are written to not depend on that distinction. The margin **does not promote a binary fail to a binary pass**; it does not enter the rubric ACV scalar; it does not affect Phase I → Phase II promotion. A high continuous margin on an axiom whose corpus distribution drifts at M2/M3 is a *process* warning, not a rubric finding — the corpus, not the substrate, may be the source of drift, and the diagnostic table flags this with a separate corpus-drift indicator.

---

## 3. Per-axiom margin formulas

Each formula is a deterministic scalar in `[0, 1]` after clipping. All formulas use a common floating-point epsilon `ε = 1e-12` for division and sign protection.

### 3.1 Unitarity (L2, L4, L7) — norm preservation

Let `x_in` be the input vector at the layer boundary and `x_out` the output. The unitarity layer claim is `‖x_out‖ = ‖x_in‖` up to floating-point.

```
m_unitarity = 1 − min(1, |‖x_out‖² − ‖x_in‖²| / max(‖x_in‖², ε))
```

- `m = 1.0`: `‖x_out‖² = ‖x_in‖²` exactly (under floating-point).
- `m = 0.5`: relative norm error 50 % of input energy.
- `m = 0`: total energy collapse or doubling beyond the input.

For L4 (the Poincaré exponential map), the unitarity check is on the local-tangent norm against the lifted hyperbolic norm, with the conformal factor `λ_p = 2/(1 − ‖p‖²)` applied: the formula is the same with `‖x_out‖ → λ_p^{-1}·d_H(p, exp_p(x_in))` and `‖x_in‖ → ‖x_in‖`. The 12-decimal CDPTI fixture for `exponential_map.v1.json` is the reference test of this formulation.

### 3.2 Locality (L3, L8) — spatial bound

The locality claim is that the layer's output remains in a declared region: for L3, the φ-weighted real-valued bound; for L8, the well-region of the active multi-well realm.

Let `x_out` be the layer output and `B` the declared region with characteristic radius `r_B`. Let `δ(x_out, B) = 0` if `x_out ∈ B` and `δ(x_out, B) = (‖x_out‖ − r_B)` otherwise (signed exit distance for L3 against the φ-weighted ball, or signed exit from the active well basin for L8).

```
m_locality = clip( 1 − max(0, δ(x_out, B)) / r_B , 0 , 1 )
```

- `m = 1.0`: `x_out` strictly inside `B` (no exit).
- `m = 0.99`: small exit, ~1 % of the region radius (near-miss).
- `m = 0.5`: significant excursion, ~50 % of `r_B` outside the region.
- `m = 0`: exit ≥ `r_B` (catastrophic; the layer is delivering points one full radius beyond the declared region).

For L4 (Poincaré ball), the locality check is `‖x_out‖ < 1` strictly: the formula uses `r_B = 1` and switches to a tighter cap, `m_locality = clip( 1 − ‖x_out‖² , 0 , 1 )`, since the exponential map's failure mode is asymptotic, not linear in radius. (L4 is not in the locality binding table; this note is for cross-axiom diagnostic consistency only.)

### 3.3 Causality (L6, L11, L13) — time ordering

The causality claim is that the layer respects the declared time-ordering: for L6, monotone phase advance under the breathing transform; for L11, accumulated triadic-temporal distance is non-decreasing inside a window; for L13, governance decisions do not retroactively rewrite earlier admits.

Let `Δt_i` be the per-event timestep on a window of `N` events, with the layer's claim being `Δt_i ≥ 0` for all `i`.

```
v = (1/N) · Σ_i max(0, −Δt_i) / max(τ_window, ε)
m_causality = clip( 1 − v , 0 , 1 )
```

where `τ_window` is the window's reference duration (declared at M0).

- `m = 1.0`: no causality violations in the window.
- `m = 0.99`: ~1 % of events have a small backward step.
- `m = 0.5`: violations average half the window duration (severe time-reversal).
- `m = 0`: every event in the window violates ordering.

### 3.4 Symmetry (L5, L9, L10, L12) — group equivariance

The symmetry claim is that the layer commutes with a declared group action `g`. For L5 (hyperbolic distance), the relevant group is PSU(1,1) Möbius isometries; for L9 / L10 (spectral and spin coherence), the symmetries are Fourier translation-invariance and SU(2) rotation respectively; for L12 (harmonic wall), the gauge invariance is the Möbius-equivariance of the wall on bit-identical k-means++.

For each layer, let `f` be the layer transform and `g` an element of the declared symmetry group sampled from a pre-registered test set. Let

```
e = ‖ f(g·x) − g·f(x) ‖ / max( ‖f(x)‖ , ε )
m_symmetry = clip( 1 − e , 0 , 1 )
```

- `m = 1.0`: equivariance holds at floating-point precision.
- `m = 0.5`: equivariance error 50 % of layer-output magnitude.
- `m = 0`: the layer transform reorders or reflects in a way that destroys the group structure.

For L12, the equivariance test is bit-identical: the harmonic-wall fixture (Annex A) shows `H(g·d, g·pd) = H(d, pd)` to ≥ 12 decimals. The continuous margin in this case is binary in practice (1.0 or near-zero) and the diagnostic value of ACV-CM at L12 is correspondingly limited; the rubric ACV cell is the load-bearing measurement.

### 3.5 Composition (L1, L14) — pipeline integrity

The composition claim is that L1 (entry encoding) and L14 (exit decoding) are consistent: the entry tokenization is the inverse of the exit detokenization on the round-trip.

Let `x_in` be the raw protocol exchange, `y` the L1-encoded representation, and `x_out` the L14-decoded recovery. Let

```
e = d_text(x_in, x_out) / max( |x_in| , ε )
m_composition = clip( 1 − e , 0 , 1 )
```

where `d_text` is the pre-registered string-distance metric (Levenshtein at the token level for the six-tongue tokenizer; declared at M0).

- `m = 1.0`: round-trip is byte-perfect.
- `m = 0.99`: ~1 % token-level edit distance.
- `m = 0.5`: half the input is unrecoverable.
- `m = 0`: the round-trip is uncorrelated with the input.

L14's audio-axis encoding is a *projection* of the pipeline state into FFT space; the round-trip claim is on the protocol-exchange level (L1 input ↔ L14 decoded protocol exchange), not on the audio waveform itself. The audio waveform is a telemetry artifact, not a composition-axiom output.

---

## 4. Severity bands and binary recovery

Each cell's continuous margin `m` maps to a severity band for triage:

| Band | Margin range | Triage action |
|---|---|---|
| **Pass (rubric)** | `m ≥ 1 − τ_axiom` | Binary cell `pass`; no triage action; record margin for trend |
| **Near-miss** | `1 − τ_axiom > m ≥ 0.95` | Binary cell `fail`; flag for tuning-batch attention; not an emergency |
| **Significant** | `0.95 > m ≥ 0.50` | Binary cell `fail`; root-cause review required before next milestone |
| **Catastrophic** | `m < 0.50` | Binary cell `fail`; pause Phase I tuning of the affected axiom; file in falsifier ledger |

`τ_axiom` per axiom is locked at M0:

| Axiom | `τ_axiom` (M0 lock) | Rationale |
|---|---|---|
| Unitarity | `1e-10` | Floating-point norm preservation; tighter than CDPTI 12-decimal because a single layer is one transform, not a composed pipeline |
| Locality | `1e-9` | Region containment; allows for exact-boundary numerical under-shoot |
| Causality | `0` (strict) | Time-ordering admits no tolerance; a backward step is a violation |
| Symmetry | `1e-12` | Equivariance must hold at the cross-stack 12-decimal threshold (Annex A reference) |
| Composition | `1e-9` | Round-trip token-level edit distance; tighter than 12-decimal because token distance is integer-valued at the level the metric is defined |

The severity-band thresholds (0.95, 0.50) are independent of `τ_axiom` and are the same across all five axioms; they exist to triage *failures* once binary `fail` is established, not to redefine the boundary between pass and fail.

---

## 5. Aggregation rule (and what NOT to do)

**Aggregation is forbidden at the rubric level.** The continuous-margin matrix is **not** rolled into the rubric ACV scalar. Doing so would violate the asymmetric-weighting rule (`feedback_asymmetric_weighting.md`) and would let near-miss continuous margins inflate a binary `fail`.

The continuous-margin matrix is rolled up *only* in the diagnostic table, with three reported scalars:

- **Per-axiom mean margin** (5 numbers): `m̄_axiom = mean over bound cells of m`.
- **Per-layer min margin** (14 numbers; N/A cells excluded): `m_layer = min over bound axioms at the layer of m`.
- **Worst-cell margin** (1 number): `m_worst = min over all bound cells of m`.

These three diagnostic scalars are reported alongside (never instead of) the rubric ACV binary matrix and the rubric ACV scalar. They support tuning-direction decisions; they do not enter the rubric.

---

## 6. Process integration

- **At M0:** the binding table (§1), the per-axiom formulas (§3), the per-axiom `τ_axiom` (§4), and the severity bands (§4) are locked. Any change is an amendment to this artifact and must be cited in the Living Metric narrative for the affected milestone.
- **At each Living Metric milestone (M0–M4):** the diagnostic table is refreshed on the sealed test corpus and reported. The rubric ACV matrix and rubric ACV scalar are reported on the same pass.
- **Between milestones:** the diagnostic table is computed nightly during tuning runs and logged. A monotone worsening of `m̄_axiom` for any axiom over three consecutive nightly runs trips the *process falsifier* in §2.1 and pauses the tuning loop for review.
- **In Phase II (forward-looking):** the same diagnostic schema applies to the Evolution Team's TA1+TA2 combined pipeline. ACV-CM does not change shape under Phase II; the per-axiom formulas, thresholds, and severity bands are forward-compatible with the Darwin–Gödel–Safe loop described in `phase_ii_bridge_narrative_v1.md` §1.

---

## 7. Source map

| Field | Source |
|---|---|
| ACV definition + binary cell rule | `proposer_metrics_specs_v1.md` §3.2 (rubric ACV; 8-field) |
| Open follow-up that this artifact closes | `proposer_metrics_specs_v1.md` §5 first bullet |
| Five-axiom mesh + binding table | `CLAUDE.md` (Quantum Axiom Mesh); `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/` (implementation) |
| Asymmetric-weighting principle (binary gate vs. continuous components) | `feedback_asymmetric_weighting.md` |
| Strict-rigor 8-field standard | `feedback_strict_scientific_rigor.md` |
| 12-decimal cross-language reference (used by §3.4 L12 note) | `M0_fixture_seal_v1.md` and `annex_a_basis_sheet_v1.md` |
| Phase II forward compatibility | `phase_ii_bridge_narrative_v1.md` §1 (Darwin–Gödel–Safe loop) |

---

## 8. Provenance

Authored 2026-04-27 by reading `proposer_metrics_specs_v1.md` (174 lines) in full, identifying §5 first bullet as the open follow-up flag, and cross-mapping the per-axiom formulas to the implementation in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/{unitarity,locality,causality,symmetry,composition}_axiom.py`. The severity bands and `τ_axiom` per-axiom locks are author-declared at M0 to satisfy the rigor-standard scope/limits fields; they are not derived from outside literature and are subject to amendment with documented rationale. The artifact is internal to ACV and is not a rubric metric: any conflict between this artifact and `proposer_metrics_specs_v1.md` §3.2 is resolved in favor of `proposer_metrics_specs_v1.md`.
