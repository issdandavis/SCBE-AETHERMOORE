# MATHBAC Proposer-Added Metrics — 8-Field Specifications (v1)

**Solicitation:** DARPA-PA-26-05 (MATHBAC), Technical Area 1
**Performer:** SCBE AetherMoore (UEI J4NXHM6N5F59, CAGE 1EXD5)
**Date:** 2026-04-28
**Status:** Working artifact for the Phase I full proposal (due 2026-06-16). Submitted abstract DARPA-PA-26-05-MATHBAC-PA-010 (2026-04-27 05:02 ET) carries one-line metric statements with falsifiers; this artifact expands each into the strict-rigor 8-field form.

---

## 1. Purpose and consistency rule

The submitted MATHBAC TA1 abstract declares four proposer-added metrics: **MEE, ACV, CDPTI, PIS**. The abstract attaches a one-line falsifier to each; it does *not* present the 8-field specification required by SCBE's internal rigor standard (`feedback_strict_scientific_rigor.md`, §2026-04-05).

This artifact is the canonical 8-field form. It governs the full proposal's §4 (Methods and Measurement Plan) and §5 (Living Metric milestones). The fields here MUST remain consistent with the as-sent abstract one-liners; the abstract is locked.

The eight fields per metric are: **name, definition, mechanism, inputs, outputs, test, falsifier, scope**. Each metric also carries a **limits** note that disambiguates what is NOT claimed (Tier 2 of the rigor standard).

The textual material in §3.1 through §3.4 below for **definition / mechanism / inputs / outputs / test / falsifier** is a verbatim carry-over from the existing full-proposal draft (`artifacts/mathbac/MATHBAC_FULL_PROPOSAL_v1_2026-04-26.md` §4.1–§4.4). Where the draft already populated those six fields, no edits are made — the role of this artifact is to *add* the **scope** and **limits** fields that the rigor standard requires and the draft has not yet supplied.

---

## 2. Cross-reference to the submitted abstract

The submitted abstract introduces the four metrics in a single bullet block:

| Metric | As-sent abstract one-liner |
|---|---|
| MEE | "Mutual Encoding Efficiency: KL between right-path and naive cross-register encoding. Falsifier: MEE collapses to zero if registers are interchangeable." |
| ACV | "Axiom Compliance Vector: per-layer check of Unitarity, Locality, Causality, Symmetry, and Composition across the 14-layer pipeline. Falsifier: any failed axiom halts the vector." |
| CDPTI | "Cross-Domain Principle Transfer Index: internal TypeScript/Python parity as the primary channel; independent Rust-kernel convergence as supplementary witness. Falsifier: internal parity fails beyond declared tolerance." |
| PIS | "Principle Interpretability Score: the same protocol object must remain readable by machine and human. Falsifier: a principle the machine uses but the human cannot read scores zero." |

The 8-field specs in §3 are direct expansions of these one-liners. No metric is renamed; no falsifier is weakened; the substrate (Poincaré ball, six-register tokenizer, harmonic wall H(d, pd) = 1/(1 + φ·d_H + 2·pd)) is identical.

---

## 3. Specifications

### 3.1 MEE — Mutual Encoding Efficiency

**Name.** MEE — Mutual Encoding Efficiency.

**Definition.** MEE is the Kullback–Leibler divergence between right-path and naive cross-tongue encoding, computed on a held-out protocol corpus.

**Mechanism.** For each pair of tongues (t_i, t_j) with i ≠ j, encode the corpus through the right-path (φ-weighted, harmonic-wall-gated) and through a naive identity crossing (no weight, no gate). Compute the KL divergence between the two encoded distributions. MEE is the mean over all 30 ordered tongue pairs.

**Inputs.** Held-out corpus of N ≥ 1,000 protocol exchanges, each labeled with a ground-truth source tongue.

**Outputs.** A scalar MEE ∈ [0, ∞) in nats (or bits), reported with a 95 % bootstrap confidence interval.

**Test.** Pre-registered split: 50 % training, 50 % held-out. MEE computed only on held-out partition. Reproducible with a fixed PRNG seed.

**Falsifier.** MEE collapses to zero (within the confidence interval) if the tongues are interchangeable. A protocol substrate whose tongues are interchangeable does not encode anything useful at the tongue boundary; MEE is therefore a direct test of whether the multi-tongue structure carries information.

**Scope.** MEE is defined for the six-register tokenizer with the φ-weighted harmonic wall. It applies to *protocol-exchange corpora* — sequences whose units carry an admit/reject decision under the wall. It does not apply to free-form natural-language corpora absent a harmonic-wall annotation. The 30-pair count is fixed by 6 ordered tongues; if the substrate is later extended to additional tongues the pair count and aggregation rule must be re-declared.

**Limits.** MEE measures encoding distinctness, not communication-protocol *correctness*. A high MEE shows that the tongues carry different information; it does not prove the right-path encoding is *correct* in a downstream task — that role is borne by CDPTI and PIS. MEE also assumes the held-out corpus's source-tongue labels are correct; a corpus with mislabeled source tongues will produce a deflated MEE that should not be read as substrate failure. The bootstrap confidence interval is a sample-level uncertainty, not a population claim — extrapolation beyond the M1 corpus class requires re-measurement on the new corpus class.

---

### 3.2 ACV — Axiom Compliance Vector

**Name.** ACV — Axiom Compliance Vector.

**Definition.** ACV is the per-layer five-component vector of axiom compliance results across all 14 pipeline layers, evaluated on a sealed test set.

**Mechanism.** For each (layer, axiom) pair where the axiom binds (Table 3.1 of the full proposal), evaluate the per-axiom check on a sealed test corpus and record pass/fail. ACV is the resulting 14 × 5 binary matrix (with cells where the axiom does not bind marked N/A).

**Inputs.** Sealed test corpus of N ≥ 500 protocol exchanges, with ground-truth admit/reject labels.

**Outputs.** ACV matrix, plus a rolled-up scalar *axiom-compliance score* equal to the fraction of bound (layer, axiom) pairs that pass.

**Test.** Sealed-blind: the test corpus is not exposed during pipeline tuning. Thresholds are pre-registered.

**Falsifier.** Any single (layer, axiom) cell failure on any held-out batch falsifies the gate's claim of being axiom-compliant. The vector is *complete or it is incomplete*; it does not admit partial credit at the rubric level.

**Scope.** ACV is defined for the canonical 14-layer SCBE pipeline (L1–L14) and the five-axiom mesh (Unitarity, Locality, Causality, Symmetry, Composition) bound per Table 3.1. It applies to *gated* pipelines — pipelines whose layers expose the axiom checks as runtime invariants. Variant pipelines that omit a layer or rebind an axiom must restate ACV with the changed binding table; ACV is *not* a portable cross-pipeline score.

**Limits.** ACV is a *binary structural* property; passing ACV does not imply the pipeline is well-tuned for any particular task. A pipeline can be axiom-compliant and still produce poor MEE or PIS. The N/A cells (where an axiom does not bind to a layer) are *expected*, not failures, and must not be counted against the rolled-up scalar. ACV as a binary matrix does not graduate severity: a Locality near-miss at L3 and a Composition catastrophic failure at L14 both count as one cell failure. Where severity matters (e.g. for triage during Phase I tuning), the proposal supplements ACV with the per-axiom continuous-margin diagnostics held internally; those are not part of the rubric ACV.

---

### 3.3 CDPTI — Cross-Domain Principle Transfer Index

**Name.** CDPTI — Cross-Domain Principle Transfer Index.

**Definition.** CDPTI measures whether the protocol's admit/reject behavior is a property of the *protocol object* and not of any single implementation. CDPTI is composed of two independent components:

- **CDPTI-Internal (load-bearing).** Numerical parity between the performer's TypeScript and Python implementations of the substrate, evaluated against a versioned, repository-resident vector fixture. The two implementations are written in different languages, share no runtime, and exercise independent code paths through the L1–L14 pipeline. Parity is the load-bearing primary measurement.
- **CDPTI-External (corroborating).** Decision-level agreement between the performer's substrate and an independently developed third-party stack (the teaming partner's Rust kernel; see Amendment A) on the same held-out communication surface. CDPTI-External is reported as a corroborating witness; it is not load-bearing for Phase I.

**Mechanism — Internal.** Both performer-owned implementations consume a shared, repository-resident vector fixture set under `tests/interop/polyglot_vectors/` and must agree on each numerical output to ≥ 12 decimal places. As of 2026-04-27, the fixture set comprises five v1.0.0 fixtures, all committed and exercised by both runners with measured 12-decimal agreement on every case:

- `poincare_distance.v1.json` — L5 hyperbolic distance `dH = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))` (5 cases, 2-D / 3-D / 6-D).
- `mobius_addition.v1.json` — L7 Möbius addition `u ⊕ v` on the Poincaré ball (5 cases).
- `exponential_map.v1.json` — L4 exponential map `exp_p(v) = p ⊕ tanh(λ_p‖v‖/2)·v/‖v‖` with `λ_p = 2/(1-‖p‖²)` (5 cases).
- `logarithmic_map.v1.json` — L4 inverse `log_p(q) = (2/λ_p)·arctanh(‖-p ⊕ q‖)·(-p ⊕ q)/‖-p ⊕ q‖` (5 cases; `log_p ∘ exp_p = id` round-trip cross-validated).
- `harmonic_wall.v1.json` — L12 harmonic-wall scalar `H(d, pd) = 1/(1 + φ·d_H + 2·pd)` with `φ = (1+√5)/2`, matching the locked abstract DARPA-PA-26-05-MATHBAC-PA-010 (5 cases at varying `pd`).

The TypeScript runner is `tests/cross-language/polyglot-hyperbolic-ops.test.ts` (vitest, `toBeCloseTo(_, 12)`); the Python runner is `tests/interop/test_polyglot_hyperbolic_ops.py` (pytest, `pytest.approx(_, abs=1e-12)`). Both pass on every CI commit. Each fixture is generated from a deterministic seed, committed to the repository, and sealed by SHA-256; the seals are recorded in the M0 baseline. The fixture set expands across Phase I to cover the full L1–L14 pipeline.

**Mechanism — External.** The performer's substrate and the partner's kernel each emit admit/reject decisions on the same held-out protocol corpus; per-item agreement is recorded and rolled up into a scalar agreement rate.

**Inputs.** For Internal: shared fixture set under repository version control, no third-party dependency, runs in CI on every commit. For External: held-out corpus of N ≥ 200 protocol exchanges, both stacks running on identical inputs without sharing internal state.

**Outputs.** Internal: per-fixture decimal-agreement count and a roll-up scalar (fraction of fixture cases meeting the decimal threshold). External: scalar agreement rate ∈ [0, 1] on the shared corpus.

**Test — Internal.** Reproducible inside the performer's repository with `npm test` (TypeScript side) and `pytest tests/interop/` (Python side). The fixture and both test runners are committed and timestamped. The TypeScript path resolves to `src/harmonic/hyperbolic.ts:hyperbolicDistance`; the Python path resolves to the reference function in `tests/interop/test_polyglot_poincare_vectors.py`. Versioning of the fixture is sealed (SHA-256 over the JSON) and the seal is recorded in the M0 baseline.

**Test — External.** The two stacks are built independently — different languages, different teams, different parameter choices. Convergence of admit/reject decisions on a shared surface is a non-trivial property; chance agreement on a balanced corpus is 0.5.

**Falsifier — Internal (load-bearing).** Any pair of fixtures on which the TypeScript and Python implementations disagree by more than the pre-registered decimal threshold falsifies the claim that the substrate is a single mathematical object reproducible across implementations. This falsifier fires inside the performer's repository alone; no partner artifact is required.

**Falsifier — External (supplementary).** A principle that survives the internal-parity test but disagrees with the third-party stack does *not* falsify CDPTI in Phase I; it flags the disagreement for documented investigation as a Phase II research target. This is intentional: external corroboration strengthens the claim, but its absence does not collapse it.

**Scope.** CDPTI applies to the substrate's *numerical* behavior (Internal) and to *decision-level* behavior (External). Internal scope is the L1–L14 pipeline as evaluated against the versioned fixture; External scope is the held-out admit/reject corpus shared with the teaming partner. CDPTI is *not* a measure of source-code similarity, nor a measure of architectural agreement: two stacks may diverge in implementation language, layer factoring, and runtime model and still converge on CDPTI. Where the partner stack is unavailable (Article 7.6 contingency in the teaming agreement), CDPTI-Internal proceeds unchanged and CDPTI-External is reported as discontinued.

**Limits.** Internal parity at 12 decimals is a *floating-point* claim; it does not extend to symbolic equivalence and it does not survive arithmetic with denormalized numbers, NaN/Inf flow paths, or hardware-FMA ordering differences that exceed the 12-decimal margin. The threshold is set by the most-stringent fixture in the set; relaxing it for any individual fixture requires a documented amendment to the M0 baseline. External agreement at 1.0 on a 200-item corpus is *evidence*, not proof, of cross-stack convergence; the chance-baseline of 0.5 sets the floor for non-trivial agreement, but agreement on a *biased* corpus (one where right-path is over-represented) can be inflated. The corpus split is therefore declared in advance and reported with right-path/wrong-path proportions.

---

### 3.4 PIS — Principle Interpretability Score

**Name.** PIS — Principle Interpretability Score.

**Definition.** PIS is the readability of the same protocol object by both human evaluators (via the human-readable face of the substrate) and machine evaluators (via the tokenizer).

**Mechanism.** Three human evaluators (independent, blinded to ground truth) read a 100-item protocol corpus presented in human-readable form (the published *Six Tongues Protocol* book, KDP ASIN B0GSSFQD9G, is one such face) and assign admit/reject decisions. Three machine evaluators (the tokenizer at three pre-registered seed values) do the same. PIS is the agreement rate between the human modal vote and the machine modal vote.

**Inputs.** 100 protocol exchanges with pre-registered ground truth. Human evaluators briefed on the rubric but not on the test items.

**Outputs.** Scalar agreement rate ∈ [0, 1], plus per-evaluator breakdown.

**Test.** Pre-registered evaluator pool. Blinding enforced by physical separation of test items.

**Falsifier.** A principle the machine uses but the human cannot read (or vice versa) scores at chance level. PIS therefore tests whether the protocol object is *the same object* in both presentations.

**Scope.** PIS applies to admit/reject decisions on protocol exchanges where a published human-readable face exists (the *Six Tongues Protocol* book is the M3 canonical face; later faces, if added, must be declared in advance). The evaluator pool is three humans + three machine-seed instances; smaller pools change the modal-vote tie-breaking rule and require re-declaration. PIS is *not* a measure of explanation quality — it is a measure of decision agreement under two different presentations of the same object.

**Limits.** Human evaluators are *not* domain naive; they are briefed on the rubric. PIS therefore measures interpretability *to a rubric-trained human*, not to an arbitrary reader. The 100-item corpus is a sample-level claim; per-item disagreements are recorded and surfaced even when the rolled-up rate is high, since cluster-disagreement at a particular tongue or wall-distance can flag a substrate weakness invisible to the scalar. Machine evaluators run at three seed values to expose seed-sensitivity; if the three machine seeds disagree, PIS reports the human-vs-modal-machine score *and* the inter-machine variance separately. The book's continued availability (KDP) is an external dependency; if the book is withdrawn or revised mid-program, the canonical face is frozen at the M0 declaration and the live edition is no longer authoritative for PIS.

---

## 4. Aggregation and the Living Metric

The four metrics are reported separately at each Living Metric milestone (M0–M4 per §4.5 of the full proposal). They are *not* combined into a single weighted score for the rubric; the rubric is the *vector* (MEE, ACV, CDPTI, PIS) plus the milestone declarations from M0.

If the program later requests a single rolled-up scalar for triage, the proposed aggregation is:

- ACV scalar (axiom-compliance fraction) is the *gating* component: ACV < 1.0 means the pipeline is structurally non-compliant and the other three metrics are reported but not relied on for promotion.
- Conditional on ACV = 1.0, the triage scalar is the geometric mean of (MEE-normalized, CDPTI-Internal-roll-up, PIS), where MEE is normalized against its M0 baseline.

This aggregation is *only* used if the program asks for it; the default rubric is the four-component vector. (Asymmetric weighting per `feedback_asymmetric_weighting.md` was considered for the aggregation: ACV is binary/structural and weights as a gate; MEE/CDPTI-Internal/PIS are continuous and weight as components inside the gate.)

---

## 5. Open follow-ups

- [x] Add the per-axiom continuous-margin diagnostic schema (held internal to ACV) as a separate annex if requested. **Closed 2026-04-27**: schema landed at `docs/proposals/DARPA_MATHBAC/acv_continuous_margin_diagnostics_v1.md` — five per-axiom formulas, M0-locked `τ_axiom`, severity bands, aggregation rule (rubric ACV unchanged; diagnostic scalars reported alongside).
- [ ] Resolve the M3 PIS evaluator pool: three named individuals with no FCOC affiliation, briefed before M3.
- [x] Confirm M0 corpus generation script + seal is committed before kickoff. **Closed 2026-04-27**: SHA-256 seals for all five v1.0.0 fixtures recorded in `docs/proposals/DARPA_MATHBAC/M0_fixture_seal_v1.md`; verification command (Python stdlib `hashlib`) committed in the same file.
- [x] Confirm the fixture set under `tests/interop/polyglot_vectors/` is actually present at the paths cited (3.3 mechanism). **Closed 2026-04-27**: all five v1.0.0 fixtures (`poincare_distance`, `mobius_addition`, `exponential_map`, `logarithmic_map`, `harmonic_wall`) committed; vitest runner `tests/cross-language/polyglot-hyperbolic-ops.test.ts` and pytest runner `tests/interop/test_polyglot_hyperbolic_ops.py` both pass at 12-decimal tolerance.

---

## 6. Source map

| Field | Source |
|---|---|
| Definition / Mechanism / Inputs / Outputs / Test / Falsifier (all four metrics) | `artifacts/mathbac/MATHBAC_FULL_PROPOSAL_v1_2026-04-26.md` §4.1–§4.4 (verbatim carry-over) |
| Scope and Limits (this artifact, new) | Authored 2026-04-28 to satisfy `feedback_strict_scientific_rigor.md` 8-field standard |
| Submitted abstract one-liners | `artifacts/mathbac/MATHBAC_ABSTRACT_SEND_CANDIDATE_v1_2026-04-27.md` §"Living Metric and Added Metrics" |
| Aggregation rule | `feedback_asymmetric_weighting.md` (binary structural gate vs. continuous components) |
