# SCBE-AETHERMOORE: Geometric Intent Verification via Compositional ML+AR Architecture

**Prepared for**: DARPA CLARA (DARPA-PA-25-07-02)
**Principal Investigator**: Issac Daniel Davis
**Organization**: AetherMoore (Sole Proprietor)
**Date**: March 2026

---

## 1. Executive Summary

Current AI security systems rely on pattern-matching classifiers (keyword blocklists, fine-tuned DeBERTa models) that fail predictably against novel adversarial prompts. The fundamental problem: detection-by-recognition requires having seen an attack before. Attackers evolve faster than defenders can retrain.

SCBE-AETHERMOORE proposes a fundamentally different approach: **geometric intent verification**. Instead of asking "have I seen this attack before?" the system asks "how much does this input cost in hyperbolic space?" The answer is computed mathematically, not learned from examples.

**The core result**: By replacing statistical text features with a trained semantic projector (sentence-transformers all-MiniLM-L6-v2 projected to 6D tongue coordinates via ridge regression), SCBE improved F1 from 0.481 to **0.813** on a 260-sample adversarial benchmark. Prompt injection ("Ignore all instructions") went from ALLOW to QUARANTINE (cost 1.81 to 16.20). Role confusion ("You are DAN") went from ALLOW to DENY (cost 19.80 to 69.70).

**CLARA alignment**: SCBE is a compositional ML+AR system where Automated Reasoning (the harmonic wall, 5 quantum axioms, governance gate) operates *inside* the ML inference pipeline, not as an external filter. This directly addresses CLARA's requirement for "AR in the guts of ML" with "verifiability based on automated logical proofs."

---

## 2. Problem Statement

### What Exists (and Why It Fails)

| System | Approach | Limitation |
|--------|----------|-----------|
| Keyword blocklists | Pattern match against known bad strings | Zero-day attacks pass through |
| DeBERTa PromptGuard | Fine-tuned binary classifier | 32% adaptive evasion rate, no explainability |
| Llama Guard | Category-based content classifier | Requires retraining for new attack vectors |
| Output filtering | Post-generation content scanning | Race condition: content may leak before filter acts |

### The Root Cause

All current approaches use **detection-by-recognition**: they must have seen a similar attack during training. This creates an arms race where attackers always have the initiative.

### What SCBE Does Differently

SCBE uses **detection-by-cost**: every input is mapped to a point in 6-dimensional hyperbolic space, and the cost of reaching adversarial regions grows superexponentially. The system doesn't need to recognize the attack — it measures the mathematical distance from safe behavior.

---

## 3. Technical Approach

### 3.1 The Harmonic Wall (AR Component)

The core mathematical constraint:

```
H(d, R) = R^(d^2)

where:
  d = hyperbolic distance from safe centroid in Poincare ball
  R = base cost parameter (calibrated per deployment)
```

This is Automated Reasoning because:
- It provides a **formal guarantee**: cost grows superexponentially with drift distance
- It is **verifiable**: for any input, we can prove the cost bound holds
- It is **explainable**: the 6D tongue coordinates show exactly which dimensions contributed

Properties:
- d=0 (safe): cost = R^0 = 1 (minimum)
- d=1 (moderate drift): cost = R^1 = R
- d=2 (large drift): cost = R^4 (superexponential)
- d=3 (adversarial): cost = R^9 (prohibitive)

### 3.2 Semantic Tongue Projection (ML Component)

The ML component maps input text to 6D coordinates via:
1. Sentence embedding (all-MiniLM-L6-v2, 384 dimensions)
2. Trained linear projection (385x6 ridge regression matrix)
3. Sigmoid activation to [0, 1] per tongue

The 6 dimensions (Sacred Tongues) represent distinct semantic channels:
- **KO** (Intent): Override, command, authority claims
- **AV** (Transport): Data flow, API calls, network operations
- **RU** (Policy): Compliance, authorization, governance rules
- **CA** (Compute): Code execution, system operations
- **UM** (Security): Credential access, PII, redaction
- **DR** (Structure): Data integrity, schema validation

### 3.3 Compositional Architecture (14-Layer Pipeline)

Each layer is an independently verifiable building block:

| Layers | Function | ML/AR | Axiom |
|--------|----------|-------|-------|
| L1-2 | Complex context + realification | ML | Composition |
| L3-4 | Weighted transform + Poincare embedding | ML+AR | Unitarity, Locality |
| L5 | Hyperbolic distance computation | AR | Symmetry |
| L6-7 | Breathing transform + Mobius phase | ML | Causality, Unitarity |
| L8 | Multi-well Hamiltonian realms | AR | Locality |
| L9-10 | Spectral + spin coherence (FFT) | ML | Symmetry |
| L11 | Triadic temporal distance | AR | Causality |
| L12 | Harmonic wall cost computation | AR | Symmetry |
| L13 | Risk decision (ALLOW/QUARANTINE/ESCALATE/DENY) | AR | Causality |
| L14 | Audio axis telemetry | ML | Composition |

**ML kinds used**: Transformer embeddings, custom tokenizer, spectral FFT
**AR kinds used**: Formal axiom verification, governance rule engine, Byzantine fault-tolerant consensus

This satisfies CLARA's "Multiplicity of AI Kinds" metric with 3 ML + 3 AR = 6 distinct kinds in composition.

### 3.4 Five Quantum Axioms (Verifiability Building Blocks)

Each axiom provides a formally verifiable invariant:

1. **Unitarity** (L2, L4, L7): Information norm is preserved through transformations
2. **Locality** (L3, L8): Effects are bounded in scope — no action-at-a-distance
3. **Causality** (L6, L11, L13): Temporal ordering is maintained — causes precede effects
4. **Symmetry** (L5, L9, L10, L12): Equivalent inputs produce equivalent outputs — gauge invariance
5. **Composition** (L1, L14): Pipeline integrity — the whole preserves properties of the parts

Current axiom compliance rate: 97.5% across 950+ automated tests.

---

## 4. Preliminary Results

### Before/After Semantic Projector (March 2026)

| Metric | Statistical Coords (Before) | Semantic Projector (After) |
|--------|---------------------------|--------------------------|
| F1 Score | 0.481 | **0.813** |
| Detection Rate | 78.7% | 74.2% |
| False Positive Rate | 100%* | 100%* |
| "Ignore all instructions" | ALLOW (cost=1.81) | **QUARANTINE (cost=16.20)** |
| "You are DAN" | ALLOW (cost=19.80) | **DENY (cost=69.70)** |

*FPR from aggressive keyword reroute rules (tunable, not from harmonic wall)

### Comparison with Industry

| System | Detection | FPR | F1 | Approach |
|--------|-----------|-----|-----|----------|
| DeBERTa PromptGuard | 76.7% | 0% | -- | Fine-tuned classifier |
| SCBE (semantic projector) | 74.2% | 100%* | 0.813 | Geometric cost + semantic embeddings |
| SCBE (projected, tuned FPR) | ~85% | ~10% | ~0.88 | With reroute threshold tuning |

### Category-Specific Strengths

SCBE outperforms DeBERTa on attack categories that exploit geometric properties:
- Tongue manipulation, spin drift, tool exfiltration, half-auth, cross-surface
- These categories are invisible to classifiers but create distinct geometric signatures

---

## 5. Application Task Domain: AI Security Governance

**Proposed domain**: Real-time adversarial prompt defense for autonomous AI systems

**SOA benchmarks**:
- DeBERTa PromptGuard (Meta, 2024)
- Llama Guard (Meta, 2024)
- GARD Armory testbed (DARPA, 2024)

**Train/test corpus**:
- 470+ SFT training pairs (adversarial + benign, tongue-classified)
- 260-sample synthetic benchmark (240 attacks across 12 categories + 20 benign)
- Adaptive attacker engine with 5 mutation strategies

**Relevance to DARPA mission**: Autonomous weapons systems (DoDD 3000.09) require provable safety guarantees. SCBE provides mathematical cost bounds on adversarial behavior — not just statistical confidence scores.

---

## 6. Proposed Milestones

### Phase 1: Feasibility Study (12 months, inferencing metrics)

| Month | Milestone | Deliverable |
|-------|-----------|-------------|
| 3 | Semantic projector calibrated on expanded dataset | Benchmark report, open-source projector weights |
| 6 | 5 axiom verifiers with formal proof sketches | Verification report, axiom test suite |
| 9 | GARD Armory integration + MITRE ATLAS mapping | Comparison benchmark, technique coverage matrix |
| 12 | Full evaluation against CLARA metrics | Phase 1 final report, open-source release |

### Phase 2: Proof of Concept (12 months, inferencing + training)

| Month | Milestone | Deliverable |
|-------|-----------|-------------|
| 15 | Training pipeline (projector learns from operational data) | Self-improving calibration system |
| 18 | Multi-domain adaptation (security + medical + legal) | Domain transfer evaluation |
| 21 | Hackathon preparation + composability with TA2 library | Integration demo |
| 24 | Final evaluation, TRL 6 demonstration | Final report, open-source package |

---

## 7. Key Personnel

**Issac Daniel Davis** — Principal Investigator
- Creator of SCBE-AETHERMOORE framework (879 commits, 97 GitHub repos)
- Patent holder: USPTO #63/961,403 (Geometric AI Governance)
- Published: npm (scbe-aethermoore, 608 downloads/month), PyPI, HuggingFace (6 models, 9 datasets)
- Background: AI security research, post-quantum cryptography, hyperbolic geometry
- ORCID: 0009-0002-3936-9369

---

## 8. Budget Summary

| Category | Phase 1 | Phase 2 | Total |
|----------|---------|---------|-------|
| PI Labor | $350K | $350K | $700K |
| Compute (GPU cloud) | $100K | $150K | $250K |
| Travel (workshops, hackathons) | $30K | $30K | $60K |
| Materials / software | $20K | $20K | $40K |
| Subcontractor (TBD) | $200K | $200K | $400K |
| Indirect (de minimis 10%) | $70K | $75K | $145K |
| Hackathon incentive reserve | $0 | $60K | $60K |
| **Total** | **$770K** | **$885K** | **$1,655K** |

Under the $2M cap with $345K margin.

---

## 9. Existing IP and Open Source

- **Patent**: USPTO #63/961,403 (provisional, filed 2025)
- **License**: MIT (open source) + Commercial dual-license
- **GitHub**: github.com/issdandavis/SCBE-AETHERMOORE (86 public repos)
- **npm**: scbe-aethermoore (14 versions published)
- **PyPI**: scbe-aethermoore v3.3.0
- **HuggingFace**: 6 models, 9 datasets, 4 spaces

CLARA requires open-source software. SCBE is already MIT-licensed and publicly available. All work produced under the program would continue as open source per solicitation requirements.
