# DARPA CLARA TA1 — Technical Volume (Draft v1)

**Solicitation**: DARPA-PA-25-07-02 (CLARA)  
**Task Area**: TA1 (Performer)  
**Performer**: AetherMoore (Sole Proprietor)  
**Principal Investigator**: Issac Daniel Davis  
**UEI**: J4NXHM6N5F59  
**Date**: 2026-04-07  
**Classification**: UNCLASSIFIED  

> Draft intent: 5-page technical narrative aligned to CLARA’s ML+AR composition requirements and 6 evaluation metrics.  
> Source material: `docs/proposals/DARPA_CLARA/03_WHITE_PAPER_OUTLINE.md`, `docs/proposals/DARPA_CLARA/CLARA_ABSTRACT_1page.md`, `docs/proposals/DARPA_CLARA/02_CLARA_COMPLIANCE_MATRIX.md`.
> Messaging notes: `docs/proposals/DARPA_CLARA/06_PM_RESEARCH_BENJAMIN_GROSOF.md` (public sources + vocabulary lint).

---

## 1. Executive Summary (Heilmeier Catechism)

### What is formally verified vs. empirically evaluated?
SCBE-AETHERMOORE is designed to separate:
- **Formally checkable artifacts**: invariant checks (axiom mesh) and bounded, replayable traces produced during inference (deterministic “pass/fail” evidence per layer).
- **Empirical performance**: detection reliability and false-positive tradeoffs measured on standardized evaluation suites and IV&V scenarios.

We do **not** claim a general proof that an arbitrary foundation model is “safe.” We claim that, for a defined application domain and threat model, the composed ML+AR pipeline produces machine-checkable artifacts and measurable improvements in reliability/tractability versus baselines.

### What are we trying to do?
Build a **high-assurance compositional governance layer** for AI agents by integrating **Automated Reasoning (AR)** directly into the **Machine Learning (ML)** inference loop. The goal is to reduce adversarial manipulation (prompt injection, role confusion, tool abuse, cross-surface exfiltration) by enforcing **mathematically checkable invariants** and **cost-scaled constraints** on agent state trajectories.

### How is it done today, and what are the limits?
Most AI safety systems are **recognition-based**: blocklists, fine-tuned classifiers, or post-hoc output filters. These methods are brittle against novel attacks and are not naturally compositional. They can provide scores or labels, but typically do not provide a structured, checkable chain of “why this was allowed/blocked” in a way that scales to complex multi-agent workflows.

### What is new in our approach?
SCBE-AETHERMOORE replaces detection-by-recognition with **detection-by-cost**: inputs and agent intents are mapped into a **6D hyperbolic manifold** (Poincaré ball) where drift into adversarial regions incurs superexponentially increasing cost. The cost is computed inside the pipeline and paired with a **5-axiom verification mesh** (unitarity, locality, causality, symmetry, composition) that produces deterministic pass/fail evidence at each stage.

We use a **6D Concept Bottleneck Layer** (the six “Sacred Tongues” dimensions: KO/AV/RU/CA/UM/DR) as the interpretable intermediate representation for both:
1) ML state projection, and  
2) AR governance decisions (risk-tiering + rule checks).

### Why will it succeed?
The core enforcement mechanism is algebraic and geometry-driven rather than heuristic. The approach is designed to be:
- **Composable**: modular layers with typed interfaces, suitable for TA2 library integration.
- **Tractable**: intended polynomial-time inference paths (dominated by fixed-dimensional transforms).
- **Explainable**: bounded unfolding depth via small concept bottleneck and layer-attribution.

### Who cares?
Any mission area requiring reliable autonomous behavior under adversarial interaction: AI security governance for autonomous agents; multi-agent operational workflows; and systems where audits and traceability are required.

### Key preliminary result (existing work)
A semantic projector mapping sentence embeddings into 6D tongue coordinates improved F1 from **0.481 → 0.813** on an adversarial benchmark (internal), with qualitative escalations such as:
- prompt injection: ALLOW → QUARANTINE  
- role confusion: ALLOW → DENY  

Under CLARA, we will (a) formalize the verification artifacts, and (b) expand evaluation to standardized adversarial suites suitable for head-to-head comparison.

---

## 2. Technical Approach (Composing ML + AR)

### 2.1 System Overview
SCBE-AETHERMOORE is implemented as a **14-layer** pipeline (HYDRA) that maps raw inputs into a governed decision with an auditable chain of intermediate checks. The central design principle is: **AR is not an external filter**; it is embedded as invariants and decision logic within the ML computation path.

**Primary application domain (TA1)**: AI security governance (adversarial prompt defense for autonomous agent systems).

### 2.2 ML Subsystem (Inductive Components)
The ML portion provides signal extraction and state construction. Key ML “kinds” include:
- **Embedding projection**: sentence-transformer embedding → linear projection → 6D concept bottleneck coordinates.
- **Geometric embedding**: containment and mapping within Poincaré ball representation.
- **Spectral telemetry**: frequency-domain features to capture instability/jitter patterns.

These components produce a compact state vector suitable for downstream AR checks.

### 2.3 AR Subsystem (Reasoning / Constraints)
The AR portion provides deterministic checks and structured governance:

**(A) Five-Axiom Verification Mesh (layer invariants)**
Each axiom is an invariant with explicit checks at designated layers:
1. **Unitarity** — norm/energy preservation within tolerated bounds  
2. **Locality** — bounded neighborhood influence (no action-at-a-distance)  
3. **Causality** — strict temporal ordering for state transitions and decisions  
4. **Symmetry** — gauge-invariant handling of equivalent representations  
5. **Composition** — typed interface integrity between adjacent layers  

The proof objective under CLARA is not “prove the model is always safe,” but to provide **automatable evidence** that each layer’s invariant holds (or fails) per input. Phase 1 deliverables include formalizable “proof sketches” and machine-checkable outputs for IV&V.

**(B) Concept Bottleneck + Rule Evaluation**
The six Sacred Tongue dimensions function as a **concept bottleneck**: a constrained, interpretable representation used to reason about intent and risk. This supports hierarchical explainability by limiting the number of concepts and providing a layer-by-layer violation trace.

From a tractability standpoint, the bottleneck + bounded rule evaluation act as a practical “restraint” mechanism: they cap explanation depth and cap the search space explored during tiering, while keeping the enforcement pathway replayable.

**(C) Risk Decision as Defeasible Rule Evaluation**
Layer 13 produces a decision in a tiered set (ALLOW / QUARANTINE / ESCALATE / DENY). Under CLARA, we will express this decision logic as defeasible rules operating over:
- concept bottleneck values, and
- invariant check results (axiom passes/fails), and
- temporal drift summaries (triadic temporal distance).

This yields a structured “why” trace per decision, compatible with logic-program style exports.

Minimal export format (for IV&V / TA2 consumption) will include:
- Facts: `tongue(KO, 0.92).`, `axiom(unitarity, pass).`, `cost(harmonic_wall, 16.2).`
- Rules (defeasible): `deny :- tongue(KO, X), X >= 0.90, cost(harmonic_wall, C), C >= THRESH.`
- Defeat chains: explicit `defeats(rule_a, rule_b).` edges with bounded unfolding (≤10)
- Trace record: ordered applied rules + facts used + defeated alternatives (replayable and deterministic)

### 2.4 Composition Mechanism (ML↔AR Glue)
SCBE composes ML and AR through two mechanisms:

1) **Geometric cost scaling** (the Harmonic Wall) that translates drift into a cost signal with superexponential growth:
```
H_wall(d*, R) = R^((phi * d*)^2)
```
Where:
- `d*` is hyperbolic distance from the safe centroid,
- `R` is a calibrated base parameter,
- `phi` is the golden ratio.

2) **Typed interfaces between layers** with checkable outputs (composition axiom). Each layer produces both:
- a next-state representation, and
- a verifiable artifact (invariant result, or constraint evidence).

This is “AR in the guts” in the sense that the AR results are produced during inference and are inputs to subsequent ML/AR steps (not merely appended as a post-hoc report).

### 2.5 Evaluation commitment (standard suites + IV&V readiness)
To ensure head-to-head comparability (and avoid relying only on internal benchmarks), Phase 1 will include at least one standardized evaluation set for each of:
- prompt injection / jailbreak behavior,
- toxicity / harmful instruction patterns,
- tool-use abuse patterns (where applicable),
- and any CLARA-provided hackathon/IV&V scenarios.

Deliverables will include dataset provenance notes, exact run commands, and fixed operating points for false-positive control so results remain reproducible under IV&V review.

Initial standardized suite (baseline commitment):
- **TruthfulQA** (truthfulness under adversarial prompting / misleading contexts)
- **RealToxicityPrompts** (safety/toxicity stress under open-ended continuation)
- **MMLU** (broad capability control surface; used to demonstrate “no catastrophic performance collapse” when governance is enabled)
- Plus a small, published jailbreak/prompt-injection set selected for clear provenance and repeatability (final selection documented in the Phase 1 benchmark report with hashes and runner scripts).

---

## 3. Mapping to CLARA TA1 Metrics (6 Metrics)

| CLARA Metric | What DARPA Measures | SCBE-AETHERMOORE Evidence & Plan |
|---|---|---|
| (1) Multiplicity of AI kinds | Distinct ML + AR kinds in composition | ML: embedding projection, geometric containment, spectral telemetry. AR: axiom mesh, defeasible rule decision, compositional typing checks. Phase 2: add training-time adaptation while preserving artifacts. |
| (2) Composed task reliability | Performance in application domain | Domain = AI security governance. Phase 1: head-to-head vs classifier baselines on standard suites + IV&V scenarios. Report F1/AUROC/false-positive tradeoffs by attack family. |
| (3) Verifiability w/o loss of performance | Automated proofs/explanations that don’t crater ML performance | Phase 1 deliverable: invariant checks + structured traces + bounded unfolding depth (<10). Validate runtime cost overhead and throughput. |
| (4) Scalability | Reliability as complexity grows | Fixed-dimensional 6D concept bottleneck and modular layers. Evaluate scaling with attack set size, conversation length, and agent count (multi-agent workflows). |
| (5) Computational tractability | Polynomial-time operation | Inference path dominated by fixed-dimension transforms and bounded checks. Report measured latency and throughput, plus complexity analysis for each layer. |
| (6) Hackathon performance | Competitive evaluation | Phase 1: produce a “hackathon kit” with deterministic logs + trace export + composable adapters (TA2-ready). Use hackathons to demonstrate attack cost escalation and traceability. |

---

## 4. Work Plan, Milestones, and Verification

### Phase 1 (Feasibility Study — inferencing only)
**Objective**: Demonstrate that SCBE’s composed ML+AR pipeline yields higher reliability on composed adversarial tasks than ML-only baselines, while producing auditable artifacts per decision.

**Milestones**
1. **M1: Standard benchmark integration**  
   - Curate and run standardized adversarial datasets aligned to the domain.  
   - Deliver: benchmark report + scripts + data provenance.  
   - Success criteria: head-to-head AUROC/F1 with a published false-positive operating point and full reproducibility artifacts.

2. **M2: Axiom artifact export + proof sketches**  
   - Convert invariant checks into machine-readable artifacts suitable for IV&V.  
   - Deliver: axiom trace schema + test expansions.  
   - Success criteria: every decision emits an artifact record that replays to identical pass/fail outcomes.

3. **M3: Defeasible rule export for Layer 13**  
   - Express tiering decisions as defeasible rule evaluation over bottleneck concepts + invariants.  
   - Deliver: rule set + trace output + evaluation showing bounded unfolding.  
   - Success criteria: bounded unfolding depth with explicit defeat chains and consistent “why” traces.

4. **M4: Hackathon readiness kit**  
   - Deliver: containerized runner + reproducible logs + scoring outputs.  
   - Success criteria: one-command execution producing deterministic scores and trace bundles suitable for IV&V.

### Phase 2 (Proof of Concept — inferencing + training)
**Objective**: Enable training-time adaptation (e.g., projector recalibration and rule updates) while preserving verifiability and tractability.

**Milestones**
1. **M5: Training-time adaptation with artifact preservation**  
   - Allow limited updates (weights/rules) with evidence logs and rollback.
   - Success criteria: artifacts are versioned (weights/rules) and decision traces remain verifiable against the corresponding version.

2. **M6: Multi-domain adaptation**  
   - Evaluate transfer to at least one additional domain (beyond AI security governance) with minimal sample complexity.
   - Success criteria: adaptation uses fewer labeled examples than retraining baselines; report sample complexity and performance deltas.

3. **M7: Hackathon performance improvements**  
   - Tune thresholds, improve trace interpretability, and demonstrate robustness to IV&V attack scenarios.

---

## 5. Risks and Mitigations

**Risk 1: Formal proof completeness**  
- Risk: full proof mechanization (Coq/Lean) may not be complete in Phase 1.  
- Mitigation: deliver proof sketches + machine-checkable invariants + traceability first; formalization becomes an incremental, scoped Phase 1→2 objective.

**Risk 2: Benchmark selection / comparability**  
- Risk: internal benchmarks may not be accepted as credible SOA comparisons.  
- Mitigation: commit to standardized suites and publish evaluation scripts + dataset provenance where allowed (and use CLARA-provided hackathon scenarios as a primary external evaluation surface).

**Risk 3: False positive calibration**  
- Risk: strong security posture can inflate FPR.  
- Mitigation: explicit threshold tuning, policy tiers, and separate “quarantine vs deny” pathways to reduce operational friction without lowering safety.

---

## 6. Prior Work / Readiness

- Working codebase with extensive automated tests and a modular architecture.  
- Existing empirical improvements from semantic projector upgrades.  
- Existing documentation: compliance matrix, abstracts, and architecture notes already in `docs/proposals/DARPA_CLARA/`.

---

## 7. What we need from CLARA to scale (TA1)

CLARA funding is used to:
- formalize the AR exports and their integration into inference/training loops,
- validate against standardized benchmarks and IV&V hackathon scenarios, and
- harden composability interfaces for TA2 integration.
