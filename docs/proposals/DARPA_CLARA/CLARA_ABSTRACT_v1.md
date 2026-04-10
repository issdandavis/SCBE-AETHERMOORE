---
title: "DARPA CLARA TA1 Abstract — SCBE-AETHERMOORE"
solicitation: DARPA-PA-25-07-02
program: CLARA
ta: TA1
pi: Issac Daniel Davis
org: AetherMoore (Sole Proprietor)
uei: J4NXHM6N5F59
date: 2026-04-07
version: 1
---

# Geometric Intent Verification via Compositional ML+AR Architecture

**Solicitation**: DARPA-PA-25-07-02 (CLARA)
**Task Area**: TA1 — Performer
**Principal Investigator**: Issac Daniel Davis
**Organization**: AetherMoore
**UEI**: J4NXHM6N5F59 | **Patent**: USPTO #63/961,403

---

## Technical Challenge

Current AI safety systems rely on detection-by-recognition: fine-tuned classifiers (Meta PromptGuard, AUROC ~0.93-0.96; Llama Guard 3, ~0.95; ShieldGemma, ~0.88-0.92) that must have encountered similar attacks during training. This creates an arms race where attackers retain initiative, systems degrade on novel inputs, and no formal guarantee exists that adversarial behavior becomes computationally infeasible. DARPA GARD evaluations confirm that no single monolithic defense generalizes across threat models — compositional defenses consistently outperform. Yet no existing system provides compositional ML+AR with automated verifiability and tractable inference.

## Proposed Approach

We propose SCBE-AETHERMOORE, a compositional AR-based ML framework where automated reasoning operates inside the machine learning inference pipeline — not as an external filter. The system uses detection-by-cost: every input maps to a point in a continuous semantic domain (Poincare ball model of hyperbolic space), where a superexponential harmonic wall H(d,R) = R^(d^2) makes adversarial drift formally prohibitive.

**Tight ML+AR composition across a 14-layer stratified pipeline:**

- **4 ML kinds**: (1) Transformer sentence embeddings projected to 6D concept bottleneck coordinates, (2) custom Sacred Tongues tokenizer with phi-weighted dimensional scaling, (3) spectral FFT coherence analysis, (4) geometric manifold routing via quasicrystal lattice.

- **4 AR kinds**: (1) Five formal axiom verifiers (unitarity, locality, causality, symmetry, composition) providing per-layer integrity constraints with automated proof traces, (2) defeasible risk governance with prioritized rule defeat — adversarial rules are exponentially deprioritized via geometric distance rather than syntactically blocked, (3) 6D concept bottleneck knowledge representation with golden-ratio-stratified inference costs (analogous to stratified negation in Datalog), (4) multi-agent Byzantine fault-tolerant deliberation with 6 symbolic reasoning agents.

**The pipeline operates as a stratified logic program**: each layer depends only on outputs of lower layers, correctness is verified layer-by-layer via five axiom decorators, and the overall system produces deontic outputs (ALLOW / QUARANTINE / ESCALATE / DENY) with hierarchical explainability in 5 unfolding levels — well within CLARA's 10-level requirement.

## Key Results

| Metric | SCBE Result | SOA Comparison |
|--------|-------------|----------------|
| Industry benchmark (91 attacks) | **91/91 blocked (0% ASR)** | ProtectAI DeBERTa: 10/91 blocked; Meta PromptGuard 2: 15/91 blocked |
| Semantic projector F1 | **0.813** (vs 0.481 baseline) | +69% improvement |
| Blind eval (200 unseen attacks) | 54.5% hybrid detection | Zero train/test contamination |
| Inferencing complexity | O(D^2), D=6 -> O(36) constant | Polynomial (tractable) |
| Inference throughput | **6,975 decisions/sec** (~0.143ms latency) | Real-time capable |
| Concept bottleneck explainability | 5-level unfolding | Meets <=10 requirement |
| ML+AR kinds | 4 ML + 4 AR = 8 total | Exceeds Phase 2 requirement (>=2+1) |
| Sample complexity reduction | ~24x via curriculum + transfer + knowledge editing | Phase 2 metric |
| Cost amplification at d*=2 | 1,420x (single wall), 10^37 (toroidal cavity) | Cryptographic-strength |
| Training corpus | 231,288 SFT records | Multi-domain coverage |

**Head-to-head industry benchmark** (April 2026, 91 adversarial attacks): SCBE achieved 0% attack success rate vs ProtectAI DeBERTa v2 (89% ASR) and Meta Prompt Guard 2 (84% ASR). SCBE advantage confidence: 0.80 average vs 0.18 for DeBERTa.

**Prompt injection** ("Ignore all instructions"): escalated from ALLOW (cost 1.81) to QUARANTINE (cost 16.20). **Role confusion** ("You are DAN"): escalated from ALLOW (cost 19.80) to DENY (cost 69.70). The harmonic wall was always mathematically sound — the trained semantic projector gave it geometrically meaningful inputs.

**Honest blind evaluation** (200 unseen attacks, zero data leakage): Single classifier detected 34.5%; hybrid system detected 54.5%. 20 attack categories mapped to MITRE ATLAS, OWASP LLM Top 10, and NIST AI RMF. This represents the system's true generalization capability on novel attack vectors — the compositional architecture catches attacks the individual classifiers miss.

## Application Domain

**AI Security Governance** — real-time adversarial prompt defense for autonomous AI systems. SOA benchmarks: Meta PromptGuard (DeBERTa, 86M params), Meta Llama Guard 3, DARPA GARD Armory testbed, MITRE ATLAS framework (~50+ adversarial ML techniques). Defense relevance: autonomous weapons systems (DoDD 3000.09) require provable safety guarantees — mathematical cost bounds, not statistical confidence scores.

## Composability (Metric 6)

Eight typed composition interfaces enable interoperability with other TA1 approaches and the TA2 integration library:

| Interface | Pipeline Location | External Integration |
|-----------|-------------------|---------------------|
| COMPLEX_TO_REAL | L1 entry | Any sensor, API, or external data source |
| REAL_TO_BALL | L4 | External ML embeddings -> SCBE geometry |
| BALL_TO_SCALAR | L13 | Risk scores consumable by any system |
| DECISION_TO_SIGNAL | L14 output | Broadcast to external governance systems |

The 6D concept bottleneck coordinates provide a natural exchange format: other TA1 performers using Bayesian LP feed evidence at L1; performers using neural networks exchange embeddings at L4; all consume verified risk decisions at L13. Open source (MIT-licensed), Apache 2.0 compatible. Published on npm (scbe-aethermoore v3.3.0), PyPI, and HuggingFace (6 models, 9 datasets).

## Proposed Milestones

**Phase 1 — Feasibility Study (15 months, inferencing metrics):**
- Month 3: Semantic projector calibrated on expanded dataset; benchmark report vs PromptGuard + Llama Guard
- Month 6: Five axiom verifiers with formal proof export (Coq/Lean4 stubs); LP-compatible rule representation (ErgoAI/XSB format)
- Month 9: GARD Armory integration; MITRE ATLAS technique coverage matrix
- Month 12: Full CLARA metric evaluation; Hackathon participation with composable modules
- Month 15: Phase 1 final report; open-source release

**Phase 2 — Proof of Concept (9 months, inferencing + training):**
- Month 18: AR-based training pipeline (tongue projector learns from operational data); sample complexity benchmarks
- Month 21: Multi-domain adaptation (security + medical/legal compliance); cross-performer TA2 composition demo
- Month 24: Final evaluation at TRL 6; extended Hackathon; final report and open-source package

## Budget Summary

| Category | Phase 1 (15mo) | Phase 2 (9mo) | Total |
|----------|----------------|---------------|-------|
| PI Labor | $350K | $350K | $700K |
| Compute (GPU cloud) | $100K | $150K | $250K |
| Travel (workshops, hackathons) | $30K | $30K | $60K |
| Materials / software | $20K | $20K | $40K |
| Subcontractor (university TBD) | $200K | $200K | $400K |
| Indirect (de minimis 10%) | $70K | $75K | $145K |
| Hackathon incentive reserve | $0 | $60K | $60K |
| **Total** | **$770K** | **$885K** | **$1,655K** |

Under the $2M cap with $345K margin for adjustments.

## Key Personnel

**Issac Daniel Davis** — Principal Investigator. Creator of SCBE-AETHERMOORE (879 commits, 62+ modules, 950+ tests across 6 tiers). Patent holder: USPTO #63/961,403 (Geometric AI Governance). Published: npm, PyPI, HuggingFace. Background: AI security, post-quantum cryptography (ML-KEM-768, ML-DSA-65), hyperbolic geometry. ORCID: 0009-0002-3936-9369.

## Existing IP and Open Source

- **Patent**: USPTO #63/961,403 (provisional, filed 2025)
- **License**: MIT (open source) — CLARA-compliant
- **Codebase**: 50,000+ lines across TypeScript (canonical), Python (reference), Rust (experimental)
- **Training data**: 400,000+ SFT records; 260-sample adversarial benchmark
- **HuggingFace**: 6 models, 9 datasets, 4 interactive spaces
- All work produced under the program would continue as open source per CLARA requirements.

---

*Submitted in response to DARPA-PA-25-07-02 (Amendment 1)*
*Contact: issdandavis7795@gmail.com*
*GitHub: github.com/issdandavis/SCBE-AETHERMOORE*
