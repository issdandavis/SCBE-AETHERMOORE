# SCBE Technical Packet — v1.0

**Title:** A Geometric Upper Bound on Adversarial Cost for Agentic AI Communication
**Subtitle:** The SCBE 14-Layer Pipeline: formal structure, sealed-blind evidence, and proposed MATHBAC work plan
**Principal:** Issac D. Davis (sole proprietor) · SAM UEI **J4NXHM6N5F59** · CAGE **1EXD5**
**Teaming partner:** Hoags Inc. (CAGE **15XV5**) — Collin Hoag, President
**Canonical constants:** `docs/specs/SCBE_CANONICAL_CONSTANTS.md` v1.0 (2026-04-20)
**Date:** 2026-04-20
**Audience:** DARPA MATHBAC TA1 reviewers (`DARPA-PA-26-05`); technical officers and teaming leads at Proposers Day 2026-04-21 (`DARPA-SN-26-59`)
**Status:** Proposers-Day technical read-ahead. Not a submission volume.

---

## Executive summary (one page)

**Claim.** Adversarial behavior in an agentic communication protocol can be modeled with a **geometric upper bound**: a single scalar cost `H(d*, R)` that grows double-exponentially with governance-weighted drift from the safe operating manifold, under an explicit symmetry group and under five stated axioms. Under the stated distributional assumptions, the design goal is a cost regime in which adversarial strategies become computationally infeasible before they become behaviorally successful.

**Mechanism.** A 14-layer pipeline lifts raw input through complex context, real-valued embedding, Sacred-Tongue weighting, and Poincaré-ball embedding; measures hyperbolic distance from the safe manifold; modulates that distance through breathing, Möbius-phase, and multi-well Hamiltonian layers; and emits a bounded safety score through a harmonic-wall projection. All five axioms (Unitarity, Locality, Causality, Symmetry, Composition) are enforced at named layers with explicit numerical tolerances.

**What is proven vs. what is designed.**
- **Proven (sealed-blind, 2026-04-19 run):** the trajectory-key → regime map is non-accidental — `24 / 24` baseline accuracy, one-sided 95 % upper bound `p ≤ 3.00 × 10⁻⁴` under 10 000 marginal-preserving permutations; per-tick KL capacity saturates `log₂(K_active)` at `≥ 99.4 %` of ceiling at both realm and regime resolution.
- **Designed (specified, not yet at-scale validated):** H-CORE double-exponential cost under generalized adversary models; Möbius-phase equivariance under PSU(1,1); composition property across non-adversarial round trips; full-pipeline end-to-end latency budgets.
- **Open (Phase-I deliverable):** reconciliation of the v3 markup ceiling (`log₂(4) = 2.0` bits/tick) against the committed segmentation's `K_active ∈ {3, 8}` — carried in teaming agreement §5 item 3, not relitigated pre-submission.

**What MATHBAC would fund.** Three Phase-I deliverables: (i) formal proof packet for H-CORE's geometric upper bound under a stated adversary class, (ii) `tier_code` ↔ real-hyperbolic-L8 bootstrap reconciliation with matched CIs, (iii) cross-provider agentic-communication benchmark with SCBE governance-in-the-loop.

---

## 1. Problem statement

Agentic AI systems communicate. They communicate with humans, with other agents, with tools, and with themselves. Each communication step is a decision about **what to say, to whom, under what authority, with what confidence, and under what recourse if wrong.** Existing work treats those decisions as classification problems over text.

**The MATHBAC question:** *what mathematics makes agentic communication reliably safe?*

SCBE's position: **classification is the wrong primitive.** The right primitive is a *governance-weighted distance* from a safe manifold, computed in a geometry where adversarial drift compounds exponentially. In Euclidean space, adversarial and benign trajectories have similar cost profiles and the defender has no structural advantage. In hyperbolic space, the defender has a geometric advantage that is not an accident of model weights — it is a property of the metric.

This packet specifies the geometry, the metric, the projection into a bounded safety score, the empirical evidence that the metric separates benign and adversarial trajectories under seal, and the scope of claims.

---

## 2. First principles

Four design decisions are load-bearing. Each is justified briefly here; each has a canonical reference implementation and a numerical tolerance in the constants file.

### 2.1 Hyperbolic geometry, not Euclidean

Hyperbolic space grows exponentially. In the Poincaré-ball model, the volume within radius `r` is `O(sinh(r)) ≈ O(eʳ)`. This means a drift that takes the system beyond a "safe" radius `r₀` must *cross more structure per unit distance* than the same drift in Euclidean space.

Operationally, `d_H(u, v) = arcosh(1 + 2‖u − v‖² / ((1 − ‖u‖²)(1 − ‖v‖²)))` — the standard Poincaré-ball distance. This is the distance used by L5 and everywhere H-CORE is evaluated.

### 2.2 Golden-ratio (φ) weighting of the symmetry layer

The hyperbolic signal alone grows fast, but it grows smoothly. We need a cavity structure that gives the cost function a resonance — so adversarial drift doesn't just walk further, it walks into an interference pattern. Six phi-scaled weights (`φ⁰` through `φ⁵`) over orthogonal language-field axes produce a toroidal standing wave whose cost function is **self-reinforcing** — the combined cost on the 6-wall lattice is `R^(122.99 · d*²)` under the phi-toroidal cavity regime.

For the H-CORE formula itself, the lift is `φ · d*`: drift is scaled by the golden ratio before being squared. This is the load-bearing difference between H-CORE and the legacy `R^(d²)` form.

### 2.3 PSU(1,1) as the canonical symmetry group

Möbius transforms of the Poincaré disk form the group `PSU(1, 1)`. They are isometries of `d_H`. They are also the only claimed equivariance group in this packet — Test B sealed-blind trajectory-key partitions were validated under PSU(1,1) with five seeds, bit-identical partitions. Higher groups (PSU(1, n) for n ≥ 2) would require a 3D pre-embedding that has not been run, and are therefore scoped as research extensions, not claims.

### 2.4 Axioms before architecture

Five axioms are stated first and the architecture is designed to enforce them — not the other way around. Each axiom has a numerical tolerance and a layer at which it is checked (§5). An architectural change that violates an axiom is rejected at the tolerance gate, regardless of whether it improves a downstream metric.

---

## 3. H-CORE: the canonical cost function

### 3.1 Formula

```
H(d*, R) = R^((φ · d*)²)

```

- `R ∈ (0, 1)` — resilience parameter. `R` near 1 is permissive; `R` near 0 is strict. Set by policy per deployment.
- `φ = 1.6180339887498948482` — golden ratio.
- `d*` — governance-weighted distance (§3.2).

**Semantics.** `H` is bounded in `(0, 1]` and monotone non-increasing in `d*`. As `d*` grows, `H` decays as `R^((φ · d*)²)` — double-exponential in drift. The `(φ · d*)²` term is the phi-toroidal cavity signature; it is what distinguishes H-CORE from the legacy `R^(d²)` form. The legacy form is retained in the root `symphonic_cipher/` package as an ablation baseline only; all external citations resolve to H-CORE.

### 3.2 Governance-weighted distance `d*`

```
d* = d_H_norm + λ_TEMPORAL · temporal_drift + λ_TRIADIC · triadic_inconsistency

```

Three terms. Three roles. **Asymmetric by design.**

| Term | Character | Source | Weight |
|------|-----------|--------|-------:|
| `d_H_norm` | geometric (dominant) | L5 Poincaré distance, normalized via `clamp(d_H / D_MAX, 0, 1)` | 1.00 |
| `temporal_drift` | correction signal (continuous, low-frequency, noisy) | L11 triadic temporal | 0.15 |
| `triadic_inconsistency` | violation signal (discrete, high-signal, structural) | L11 triadic temporal | 0.30 |

**Why asymmetric.** Temporal drift accumulates gradually and is often benign; triadic inconsistency is structural disagreement across immediate / medium / long intent channels and is rarely benign. Symmetric weighting blurs this — it under-reacts to real instability and over-reacts to benign drift. Triadic earns 2× temporal; geometry still dominates at ~55 % of `d*`'s budget in the normal regime.

**Dual-anchor normalization.** Rather than a single clip, `d_H` is interpreted against two anchors:

- `D_TYPICAL = 5.0` — upper bound of the normal operating regime
- `D_MAX = 10.0` — saturation ceiling

`d_H_norm` maps to three regime bands: `[0.0, 0.5]` normal (geometry-dominated), `[0.5, 1.0]` elevated (interpretation layers must flag), `= 1.0` clipped (separation power degraded, treat as elevated). This makes the governance signal debuggable — a downstream inspector reads the band, not just the clipped number.

### 3.3 Parameter Sensitivity Statement

**Canonical language for all external artifacts (quote verbatim):**

> The governance signal is stable for **λ_TEMPORAL ∈ [0.10, 0.20]** and **λ_TRIADIC ∈ [0.25, 0.40]**. Outside this band: underweighting triadic reduces safety sensitivity; overweighting temporal inflates the false-positive rate on benign drift. `D_MAX = 10.0` with `D_TYPICAL = 5.0` assumes the operating distribution keeps the bulk of `d_H` in `[0, 5]`; distributional shift widening beyond this requires re-anchoring. Any change to these λ values or D anchors requires sealed-blind re-validation before external citation.

### 3.4 L12 projection

The bounded safety score consumed by the L13 governance gate is a **projection** of H-CORE into `(0, 1]`, not a competing formula:

```
S_L12 = 1 / (1 + α_H · H(d*, R) + β_pd · p_d)

```

with `α_H = 1.0`, `β_pd = 2.0`, and `p_d` the policy-divergence signal from L11/L13. The linearized form `H(d, pd) = 1/(1 + d_H + 2·p_d)` present in the `src/symphonic_cipher/` package is the `α_H · H → d_H` limit of this projection and is retained only as a legacy API. Production code paths use H-CORE → `S_L12`.

---

## 4. The 14-layer pipeline

| Layer | Function | Formula / artifact | Axiom |
|------:|----------|--------------------|------|
| L1 | Complex context ingestion | tokenize → lift to ℂⁿ | A5 |
| L2 | Realification | ℂⁿ → ℝ²ⁿ with `‖·‖`-preservation | A1 |
| L3 | Weighted transform | tongue φ-weights (§6) | A2 |
| L4 | Poincaré embedding | exp-map into `‖x‖ < 1 − 1e-6` | A1 |
| L5 | Hyperbolic distance | `d_H` (§2.1) | A4 |
| L6 | Breathing transform | time-ordered oscillatory modulation | A3 |
| L7 | Möbius phase | PSU(1,1) isometric rotation | A1 |
| L8 | Multi-well Hamiltonian / CFI | ALLOW / QUARANTINE / ESCALATE / DENY realms | A2 |
| L9 | Spectral coherence | FFT (`N_FFT = 256`) | A4 |
| L10 | Spin coherence | alignment / decoherence (`N_SPIN = 64`) | A4 |
| L11 | Triadic temporal distance | immediate / medium / long; feeds `d*` | A3 |
| L12 | Harmonic wall | `S_L12` projection of H-CORE | A4 |
| L13 | Risk decision | bounded-score → tier emission | A3 |
| L14 | Audio-axis telemetry | FFT-encoded state for audit / cross-system | A5 |

**Dataflow discipline.** Each layer is responsible for preserving the axiom it enforces at its tolerance. A violation at a layer is not a downstream correction; it is a fault emission to the governance gate. This is the sense in which SCBE is axiom-first: the pipeline is a *structural* enforcement mechanism, not a classifier with a safety post-processor.

---

## 5. Quantum Axiom Mesh

Five axioms. Canonical enforcement layers. Canonical tolerances.

| # | Axiom | Layers | Canonical assertion | Tolerance |
|--:|-------|--------|---------------------|-----------|
| A1 | **Unitarity** | L2, L4, L7 | `\|‖·‖_after − ‖·‖_before\| ≤ ε_A1` | **1e-9** |
| A2 | **Locality** | L3, L8 | No long-range leakage between realm wells; weighted transform spatially bounded | structural |
| A3 | **Causality** | L6, L11, L13 | Time-ordering, no future→past coupling | structural |
| A4 | **Symmetry** | L5, L9, L10, L12 | `d_H` invariant on the Poincare disk under `PSU(1,1)`; sealed-blind partition result validated under `PSU(1,1)`; FFT basis gauge-invariant | `1e-9` on norm; bit-identical partition result under tested group action |
| A5 | **Composition** | L1, L14 | Pipeline round-trip identity on non-adversarial inputs is a design target enforced by the architecture | structural |

Python reference implementations: `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/`. Each axiom file corresponds to one assertion.

**Interpretation.** A classifier can be right or wrong on an example. An axiom-enforced pipeline can be *right by construction, or report that it is wrong.* That is the guarantee we trade for the engineering cost.

---

## 6. Sacred Tongues — the weighted-transform substrate

Six tongues; each weight is `φⁿ` for `n ∈ {0, …, 5}`. Weights are the canonical numeric identity; the names are documentation labels carried from the associated body of lore work (The Six Tongues Protocol, ASIN B0GSSFQD9G, prior art 2026).

| Code | Tongue | φ exponent | Weight |
|------|--------|-----------:|-------:|
| **KO** | Kor'aelin | φ⁰ | **1.000** |
| **AV** | Avali     | φ¹ | **1.618** |
| **RU** | Runethic  | φ² | **2.618** |
| **CA** | Cassivadan | φ³ | **4.236** |
| **UM** | Umbroth   | φ⁴ | **6.854** |
| **DR** | Draumric  | φ⁵ | **11.090** |

**Token grid per tongue:** 16 × 16 = 256 tokens. 6 × 256 = **1 536 base tokens** before combinatoric lifts. The 47-dimensional complex manifold used for higher-order lifts is combinatoric, not engineered: `6 + C(6, 2) + C(6, 3) + 6 = 47` (six real tongues + two-tongue pairs + three-tongue triples + six self-imaginary lifts).

---

## 7. Empirical evidence (sealed-blind, 2026-04-19)

**Scope of claims in this section is deliberately narrow.** We freeze interpretation here to avoid overclaims.

### 7.1 Accuracy

- **Traces analyzed:** 24
- **Baseline accuracy:** 24 / 24 = 1.000
- **Bootstrap 95 % CI on accuracy:** [1.000, 1.000]

This is an N = 24 finding. It is the sealed-blind point-estimate, not a claim about population accuracy at larger N. Phase-I deliverables extend this.

### 7.2 Permutation test (marginal-preserving shuffles)

- **N permutations:** 10 000
- **Seed:** 20260419
- **Hits ≥ observed:** 0 / 10 000
- **Empirical p-value:** 0.0
- **One-sided 95 % upper bound on p:** **2.9952835977664627 × 10⁻⁴** — cite as **`p ≤ 3.00 × 10⁻⁴`**

The v2 paper's `p < 1e-300` claim was a float-underflow artifact and is **superseded** by the 3.00 × 10⁻⁴ upper bound. Any external citation resolves to 3.00 × 10⁻⁴.

### 7.3 KL channel capacity (trace-level bootstrap, Laplace α = 1.0)

| Resolution | `K_active` | Ceiling `log₂(K_active)` | Point estimate | 95 % CI | Fraction of ceiling |
|------------|-----------:|-------------------------:|---------------:|---------|--------------------:|
| Realm  | 3 | 1.584962500721156 bits/tick | **1.5760672949216488** | [1.5717710113075731, 1.5799225334401148] | **0.9944** |
| Regime | 8 | 3.0 bits/tick               | **2.981822705821849**  | [2.57088746631414, 2.983530019831844]     | **0.9939** |

**Interpretation, frozen:** the mapping saturates its channel at `≥ 99.4 %` of the resolution-appropriate ceiling. Saturation here means the segmentation is carrying information at near-capacity for its chosen `K_active`; it does not mean the mapping is globally optimal across all possible segmentations, which is a separate claim not made here.

### 7.4 Open item (ceiling reconciliation)

The v3 markup claims a `log₂(4) = 2.0` bits/tick ceiling; the committed segmentation's `K_active` is 3 at realm resolution and 8 at regime resolution. The discrepancy is a `tier_code`-vs-real-hyperbolic-L8 bootstrap question. It is carried as **Phase-I Deliverable #3** in the MATHBAC teaming agreement (§5 item 3), not litigated pre-submission.

### 7.5 Artifact digests

| Artifact | SHA-256 |
|----------|---------|
| `segmentation_committed.json`      | `dab56a6832548f22821d737f7f4f7434f6d9f0c9165ed375baf57963673e64d8` |
| `permutation_test_report.json`     | `0830e7dd95678b680e1d53d7f90a89c77beb7960a4318ea0d0dfbf5c271bc2fd` |
| `kl_capacity_ci_report.json`       | `138d3cf9d00b16153fe4e9e50ec5ec152d4ac5ede47959cad8f5d381f4f2d4d5` |
| `dava_v1_for_collin.tar.gz`        | `87a0ee34fdfee6e210c53336186147dbfcaddd68a31247b59ce4cae91eefd563` |
| `labels.sealed.json` (2026-04-19)  | `f17785420f3bbb86dc4ceb98523346f2d33acd1464d93952e079c370c32acb3b` |

---

## 8. Relationship to prior work

**Geometric Deep Learning (GDL).** Bronstein et al. frame equivariance across single groups; SCBE composes *five* axioms across 14 layers. Composition over group choice is the distinction.

**Hyperbolic embeddings.** Nickel & Kiela (2017) and subsequent work use Poincaré-ball embeddings for hierarchy learning; SCBE uses the same geometry for a *governance* signal, not a representation-learning objective. The distance is the product, not the embedding.

**Post-quantum cryptography.** SCBE is not a new cryptographic primitive. ML-KEM-768 and ML-DSA-65 are the PQC substrate (via `liboqs` 0.15.0). SCBE's novelty is the governance layer *above* PQC — the Poincaré-ball cost function that constrains what a correctly-authenticated message can do.

**Verification & formal methods.** The axiom-mesh approach is closer in spirit to formal verification than to guardrail models: axioms are stated, enforced at tolerances, and violations are emissions rather than corrections. This is the ground on which a teaming with Susmit Jha (DARPA I2O, trustworthy steerable AI + program synthesis + formal methods) would operate.

**Prior art (personal).** USPTO provisional **#63/961,403** covers the 14-layer + Sacred Tongues + Poincaré governance structure. *The Six Tongues Protocol* (ASIN B0GSSFQD9G, KDP) is a timestamped published work establishing prior art for the Langues weighting system.

---

## 9. Proposed Phase-I work plan (what MATHBAC would fund)

Four deliverables. The first three (§9.1–§9.3) are the submission-grade claim set, each scoped to a Phase-I budget envelope, each with a sealed-blind validation step, each auditable against the canonical constants file. The fourth (§9.4) is a proposed Phase-I extension — additive, not part of the submitted abstract — and is flagged as such at its section header.

### 9.1 Deliverable 1 — Formal proof packet for H-CORE

**Objective.** State a family of adversary models (drift, edge-walk, mimicry, oscillation, midpoint-attack). For each, prove the H-CORE double-exponential upper bound — or provide a counterexample that localizes which axiom fails.

**Outputs.** (i) adversary-model catalog with distributional assumptions; (ii) proofs or documented failures per model class; (iii) replication harness under seal.

**Acceptance.** Proofs machine-checkable under Lean or Coq for ≥ 3 model classes; empirical counterexamples with reproducible seeds for the rest.

### 9.2 Deliverable 2 — `tier_code` ↔ real-hyperbolic-L8 bootstrap reconciliation

**Objective.** Resolve the §7.4 open item. Run the committed Poincaré pipeline (Issac) and the `proof_strategies.py` tier-code bootstrap (Hoags/DAVA) against the same segmentation and compare CIs side-by-side.

**Outputs.** Matched-CI report. Reconciliation memo explicitly stating whether the v3 ceiling claim survives, is rewritten, or is retracted.

**Acceptance.** Both CIs under seal, overlap or gap explicitly characterized, memo signed by both PIs.

### 9.3 Deliverable 3 — Cross-provider agentic-communication benchmark

**Objective.** Evaluate SCBE governance-in-the-loop on agentic communication traces across multiple providers (local, Anthropic, HuggingFace, OpenAI, xAI). Measure regime classification, permutation-test p-values, and KL capacity at scale (target N ≥ 1 000 traces).

**Outputs.** Public benchmark harness (adversary suite from Deliverable 1). Per-provider governance reports. Sealed-blind replication bundle.

**Acceptance.** All reports under seal with committed segmentations, digests, and seeds. Benchmark harness open-sourced at program end.

### 9.4 Deliverable 4 — Multi-Substrate Consistency Benchmark (proposed extension)

**Status.** Proposed Phase-I extension. Not part of the submitted abstract's core claim set. Additive to Deliverables 1–3. Framed as a **benchmark family and consistency criterion**, not a fully proved theorem.

**Motivation.** Sacred Tongues re-expression is, by construction and by §6.x harness evidence, **bijective at the transport layer** — `encode_bytes`/`decode_tokens` round-trip is bit-exact across self, pairwise, and multi-hop chains. A governance-weighted distance function that composes with a bijective transport should therefore satisfy three measurable invariances under tongue re-expression. These invariances form the evidence surface for "the SCBE governance signal does not depend on the substrate in which the input is expressed."

**Consistency criterion.** For a prompt `K`, a tongue-transport map `T` drawn from the harness-verified bijective family `{KO↔KO, KO↔AV, …, KO→AV→RU→KO, …}`, and the SCBE governance function `G = classify ∘ embed`:

- **C₁ (regime invariance under re-expression).** `C₁(T; K) := 𝟙[classify(K) = classify(T(K))]`. The L8 realm and L13 regime tier assigned to `K` and to its tongue-re-expressed form `T(K)` agree.

- **C₂ (embedding Lipschitz perturbation).** `C₂(T; K) := d_H(embed(K), embed(T(K)))`. Treated as a **measured bound target** — not a proved bound at v1. The Phase-I work characterizes the empirical distribution of `C₂` across prompts and transports, and proposes ε_target from its p95.

- **C₃ (cross-substrate agreement).** `C₃(T; K) := 𝟙[regime_DAVA(T(K)) = regime_SCBE(T(K))]`. DAVA's independent tier-code observer and SCBE's real-hyperbolic-L8 observer must agree on the regime assignment for the re-expressed form.

**Proposed acceptance gates.** Carried in `evaluation_contract_v1` as the `substrate_consistency` metric family:

| Gate | Threshold | Hard-stop |
|------|-----------|-----------|
| `regime_invariance` (aggregate over tongues) | ≥ 0.99 | — |
| `regime_invariance` (per-tongue floor) | ≥ 0.99 for **each** of KO, AV, RU, CA, UM, DR | **Yes** — aggregate ≥ 0.99 with any single tongue below 0.99 fails the benchmark |
| `embedding_lipschitz_p95` | ≤ ε_target (ε_target to be reported, not pre-fixed at v1) | — |
| `dava_scbe_agreement` | ≥ 0.95 with per-regime confusion matrix attached | — |

The hard-stop exists because an aggregate that looks healthy while a single tongue collapses to a different regime is the exact failure mode the benchmark is built to catch — symmetric tongue coverage is the point.

**Register discipline.**

- **Proven (as of 2026-04-20).** Sacred Tongues transport layer is bijective on the actual `geoseal_cli` command surface, including UTF-8 subprocess I/O on Windows. The current harness report records `9 / 9` checks passing in `artifacts/benchmark/tongue_challenge_harness_report.json`, and the CLI regression suite records `10` passing tests. This proves transport fidelity under the tested harness scope (self-bijection, pairwise matrix, selected multi-hop chains, stress payloads, and CLI command-path round-trips); it does **not** prove full executable semantic bijection across code languages. Current sealed-blind SCBE regime separation (§7) is bound to the N = 24 committed segmentation, not to re-expressed inputs.

- **Designed.** The benchmark protocol — evaluation pipeline wiring into both the SCBE L8/L13 observer and DAVA's tier-code observer, the three criterion measurements, and the four acceptance gates. Specified here and extended in `evaluation_contract_v1`.

- **Open (Phase-I deliverable under this §9.4).**
  1. Measured value and variance of ε_target (`C₂.p95`) under the benchmark distribution.
  2. Full-tongue regime-invariance rates, aggregate and per-tongue, under re-expression.
  3. DAVA–SCBE concurrence rates under re-expression, with per-regime confusion matrix.
  4. Whether `C₂` admits a tight analytical Lipschitz bound under the φ-weighted L3 and the Möbius L7, or whether the bound is empirical-only at Phase-I scope.

**Outputs.** (i) `substrate_consistency` metric block emitted under `evaluation_contract_v1` by the conformed tongue-challenge harness and by the cross-provider harness (§9.3); (ii) per-tongue confusion matrices sealed alongside §7-class reports; (iii) Phase-I memo characterizing C₂ empirically and stating whether a proof track is warranted in a follow-on.

**Acceptance.** All three criterion measurements reported with CIs; the four gates evaluated and either passed at threshold or flagged as open research items with reproducible seeds. Benchmark artifacts sealed to the same digests-and-bundle discipline as §7.5.

---

## 10. Claims discipline

Three registers of language are used in this packet. Reviewers can hold us to each:

- **"Proven"** appears only against the sealed-blind 2026-04-19 run at its stated N.
- **"Designed"** appears against specified architecture with tolerances but without at-scale empirical validation.
- **"Open" / "Phase-I"** appears against items where the honest state is "we know the shape of the answer; we have not run the validation."

If this packet ever says "proven" where the evidence supports only "designed," that is a bug, not a feature. Corrections resolve against the canonical constants file and this packet's version history.

---

## Appendix A — Constants quick-reference

All values authoritative in `docs/specs/SCBE_CANONICAL_CONSTANTS.md` v1.0.

| Constant | Value |
|----------|-------|
| φ | 1.6180339887498948482 |
| `λ_TEMPORAL` | 0.15 |
| `λ_TRIADIC` | 0.30 |
| `D_TYPICAL` | 5.0 |
| `D_MAX` | 10.0 |
| `α_H` (L12) | 1.0 |
| `β_pd` (L12) | 2.0 |
| `ε_A1` | 1e-9 |
| `ε_ball` | 1e-6 |
| `ε_arcosh` | 1e-12 |
| `N_FFT` | 256 |
| `N_SPIN` | 64 |
| KEM | ML-KEM-768 |
| DSA | ML-DSA-65 |
| AEAD | AES-256-GCM |
| Symmetry group | PSU(1, 1) |
| Canonical traces (2026-04-19) | 24 |
| Permutation N | 10 000 |
| Permutation seed | 20260419 |
| `p` upper bound | 3.00 × 10⁻⁴ |

---

## Appendix B — Contact & registration

| Field | Value |
|-------|-------|
| Principal | Issac D. Davis |
| Email | issdandavis7795@gmail.com |
| Phone | (360) 808-0876 |
| SAM UEI | J4NXHM6N5F59 |
| CAGE | 1EXD5 |
| SAM status | ACTIVE (2026-04-13) |
| USPTO provisional | #63/961,403 |
| Book ASIN | B0GSSFQD9G |
| Teaming partner | Hoags Inc., CAGE 15XV5 |
| Solicitation | DARPA-PA-26-05 (MATHBAC TA1 proposal opportunity); DARPA-SN-26-59 (Proposers Day notice) |

---

## Version history

| Date | Version | Change |
|------|---------|--------|
| 2026-04-20 | v1.0 | Initial. H-CORE canonical. Asymmetric d* weighting (λ_TEMPORAL = 0.15, λ_TRIADIC = 0.30). Dual-anchor normalization. Parameter Sensitivity Statement locked. Sealed-blind 2026-04-19 constants frozen. |
