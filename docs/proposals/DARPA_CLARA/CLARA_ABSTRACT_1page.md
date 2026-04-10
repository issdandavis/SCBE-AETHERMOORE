---
title: "DARPA CLARA TA1 Abstract (1-Page) — SCBE-AETHERMOORE"
solicitation: DARPA-PA-25-07-02
ta: TA1
pi: Issac Daniel Davis
org: AetherMoore
uei: J4NXHM6N5F59
date: 2026-04-07
note: "Condensed to single page per DARPA abstract format. See CLARA_ABSTRACT_v1.md for full version."
---

# Geometric Intent Verification via Compositional ML+AR Architecture

**Solicitation**: DARPA-PA-25-07-02 | **TA**: TA1 | **PI**: Issac Daniel Davis | **UEI**: J4NXHM6N5F59

## What are you trying to do?

Eliminate the arms race in AI safety by replacing detection-by-recognition (classifiers that must have seen similar attacks) with detection-by-cost (geometric constraints that make adversarial behavior superexponentially expensive). Current SOA systems (Meta PromptGuard AUROC ~0.95, Llama Guard 3, ShieldGemma ~0.90) degrade on novel attacks and provide no formal guarantees. DARPA GARD confirms no single defense generalizes — compositional approaches win.

## How is it done today, and what are the limits?

Today's AI safety uses monolithic ML classifiers with AR bolted on externally: blocklists filter outputs, fine-tuned models detect known patterns, post-hoc monitors scan responses. Limits: (1) novel attacks evade recognition, (2) no verifiable cost guarantees, (3) no compositional building blocks, (4) explainability limited to attention weights or saliency maps.

## What is new in your approach?

SCBE-AETHERMOORE places Automated Reasoning inside the ML inference pipeline. A superexponential harmonic wall H(d,R) = R^(d^2) in a Poincare ball creates formal cost guarantees: adversarial drift at distance d=2 costs 1,420x more than safe operation. The system composes 4 ML kinds (transformer embeddings, custom tokenizer, spectral FFT, manifold routing) with 4 AR kinds (5-axiom formal verification, defeasible risk governance, 6D concept bottleneck knowledge representation, Byzantine multi-agent deliberation) across a 14-layer stratified pipeline. Each layer is independently verifiable against integrity constraints (unitarity, locality, causality, symmetry, composition). The 6 concept bottleneck dimensions provide hierarchical explainability in 5 unfolding levels. Inferencing runs in O(D^2) polynomial time — 2.5-185 microseconds per query. Risk decisions are deontic outputs (ALLOW/QUARANTINE/ESCALATE/DENY) produced by defeasible rule evaluation where adversarial rules are exponentially deprioritized via geometric distance, not syntactically blocked.

## Who cares?

DoD autonomous systems (DoDD 3000.09) require provable safety guarantees. SCBE provides mathematical cost bounds — not statistical confidence — for AI governance. Eight typed composition interfaces (L1 ingestion through L14 telemetry) enable interoperability with other TA1 performers and the TA2 integration library. Open source (MIT-licensed), published on npm/PyPI/HuggingFace.

## If successful, what difference will it make?

AI systems with formally verifiable safety guarantees that compose with existing ML infrastructure. Sample complexity reduced ~24x via curriculum learning, cross-domain transfer, and direct knowledge editing (0 samples for policy updates). A reusable compositional framework where adding a new domain means configuring concept bottleneck weights, not retraining from scratch.

## What are the risks?

Formal proof export (Coq/Lean4) for all 5 axioms is not yet complete — currently validated via 950+ automated tests. Logic program integration (ErgoAI/XSB compatibility) needs explicit mapping. Mitigations: Phase 1 milestones include formal proof stubs (Month 6) and LP-compatible rule export.

## How long will it take and how much will it cost?

Phase 1 (15 months): $770K. Phase 2 (9 months): $885K. Total: $1,655K (under $2M cap). Key deliverables: calibrated semantic projector + formal axiom proofs (Phase 1), AR-based training pipeline + multi-domain adaptation (Phase 2).

## Key Results (April 2026)

**Industry benchmark** (91 attacks): SCBE blocked 91/91 (0% ASR) vs ProtectAI DeBERTa v2 (10/91 blocked, 89% ASR) and Meta PromptGuard 2 (15/91 blocked, 84% ASR). Semantic projector F1: **0.813**. Blind eval on 200 unseen attacks: 54.5% hybrid detection with zero data leakage. Throughput: **6,975 decisions/sec** (~0.143ms). Prompt injection escalated ALLOW -> QUARANTINE. Role confusion escalated ALLOW -> DENY. 231,288 SFT training records. Patent: USPTO #63/961,403.
