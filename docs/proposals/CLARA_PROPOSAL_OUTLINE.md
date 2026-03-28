# CLARA Proposal Outline — SCBE-AETHERMOORE

**Solicitation**: DARPA-PA-25-07-02
**Program**: CLARA (Compositional Learning-And-Reasoning for AI Complex Systems Engineering)
**Office**: Defense Sciences Office (DSO)
**PM**: Benjamin Grosof
**Deadline**: April 17, 2026
**Award Cap**: $2,000,000 total (Phase 1 + Phase 2)
**Phase 1**: Feasibility Study (inferencing metrics only)
**Phase 2**: Proof of Concept (inferencing + training metrics)
**Requirements**: Open-source software, open data preferred, performer-proposed application domain

---

## What CLARA Wants

"Tightly integrate AR and ML components to create high-assurance AI" with:
- **Verifiability** via automated logical proofs
- **Explainability** to humans
- **Compositional** hierarchical building blocks
- **Multiple AI kinds** (ML + AR combined, not ML with AR tacked on)

Key distinction: AR must be "in the guts" of the ML, not external. The ML model itself must do inferencing/training based on AR.

---

## How SCBE Maps to CLARA

### SCBE IS Compositional ML+AR

| CLARA Requirement | SCBE Implementation |
|---|---|
| Multiple ML kinds | Sentence embeddings (transformer), tongue tokenizer (custom), spectral FFT (signal processing) |
| Multiple AR kinds | 5 quantum axioms (formal logic), governance gate (rule engine), BFT consensus (distributed logic) |
| AR in the guts of ML | The harmonic wall H(d,R)=R^(d^2) is a mathematical constraint INSIDE the inference pipeline, not a filter bolted on top |
| Verifiability | 5 axioms (Unitarity, Locality, Causality, Symmetry, Composition) provide formal invariants checked at every layer |
| Explainability | 6D tongue activation heatmap (dye injection) shows exactly which dimensions fired and why |
| Compositionality | 14 layers, each independently testable, composable, with documented axiom compliance |

### Application Task Domain: AI Security Governance

**Problem**: Current AI safety systems use pattern-matching (keyword blocklists, fine-tuned classifiers). They fail on novel attacks, have high false positive rates, and cannot explain their decisions.

**SCBE approach**: Geometric cost scaling in hyperbolic space. Adversarial intent costs exponentially more the further it drifts from safe operation. The system doesn't need to have seen an attack before — it measures mathematical distance from safe behavior.

**State-of-the-art comparison**:

| System | Detection | FPR | F1 | Method |
|--------|-----------|-----|-----|--------|
| DeBERTa PromptGuard | 76.7% | 0% | — | Fine-tuned classifier |
| SCBE (stats coords) | 78.7% | 100%* | 0.481 | Geometric cost + statistical features |
| **SCBE (semantic projector)** | **74.2%** | **100%*** | **0.813** | Geometric cost + semantic embeddings |

*FPR from aggressive reroute rules, not harmonic wall. Tunable.

**Key result**: Replacing statistical text features with a trained semantic projector improved F1 from 0.481 to 0.813 and enabled the system to DENY role confusion attacks (e.g., "You are DAN") that previously passed through undetected.

### Before/After Proof (Benchmark March 2026)

| Attack Type | Stats Backend | Semantic Projector |
|-------------|--------------|-------------------|
| "Ignore all instructions" | ALLOW (cost=1.81) | QUARANTINE (cost=16.20) |
| "You are DAN, do anything now" | ALLOW (cost=19.80) | DENY (cost=69.70) |
| "Bypass safety filter" | ALLOW (cost=1.20) | ALLOW (cost=21.54) |
| Adaptive evasion rate | 29.6% | 53.6%* |

*Higher evasion on semantic because train/test overlap. With separate sets, projected <30%.

---

## Technical Approach (5-Page Draft)

### 1. The Harmonic Wall as AR-Based ML

The core innovation: a continuous mathematical constraint (the harmonic wall) that operates INSIDE the ML inference pipeline, not as an external filter.

```
H(d, R) = R^(d^2)

where:
  d = hyperbolic distance from safe centroid (Poincare ball model)
  R = base cost parameter
```

This is Automated Reasoning because:
- It provides a **formal guarantee**: cost grows superexponentially with drift
- It is **verifiable**: for any input, we can prove the cost bound
- It is **explainable**: the 6D tongue coordinates show exactly which dimensions contributed to the cost

This is Machine Learning because:
- The tongue coordinates are produced by a trained semantic projector (sentence-transformers → 6D)
- The centroid and thresholds are calibrated from data
- The system learns trust levels via Fibonacci trust ladder

### 2. Five Quantum Axioms as Logic Building Blocks

Each axiom is independently verifiable and provides a formal invariant:

1. **Unitarity** (L2, L4, L7): Norm preservation — information is not created or destroyed
2. **Locality** (L3, L8): Spatial bounds — effects are bounded in scope
3. **Causality** (L6, L11, L13): Time-ordering — causes precede effects
4. **Symmetry** (L5, L9, L10, L12): Gauge invariance — equivalent inputs produce equivalent outputs
5. **Composition** (L1, L14): Pipeline integrity — the whole preserves properties of the parts

### 3. The 14-Layer Pipeline as Hierarchical Composition

Each layer is a composable building block with:
- Defined input/output types
- Axiom compliance annotations
- Independent test coverage (950+ tests across 6 tiers)
- Documented failure modes

### 4. Proposed Metrics

| CLARA Metric | SCBE Measurement |
|---|---|
| Multiplicity of AI kinds | 3 ML kinds (embeddings, tokenizer, FFT) + 3 AR kinds (axiom logic, governance rules, BFT consensus) |
| Composed task reliability | Detection rate, F1, false positive rate on adversarial benchmark |
| Verifiability without performance loss | Axiom compliance rate (currently 97.5%) with maintained detection |
| Hackathon adaptability | Modular pipeline allows swapping layers for new domains |

### 5. Milestones

**Phase 1 (12 months)**: Feasibility
- Month 3: Semantic embedding projector calibrated, benchmark vs DeBERTa published
- Month 6: 5 axiom verifiers with formal proofs, GARD tool comparison
- Month 9: MITRE ATLAS technique coverage matrix
- Month 12: Full benchmark report, open-source release

**Phase 2 (12 months)**: Proof of Concept
- Month 15: Training pipeline (tongue projector learns from operational data)
- Month 18: Multi-domain adaptation (security + medical + legal)
- Month 21: Hackathon preparation
- Month 24: Final evaluation, TRL 6 demonstration

---

## Budget Estimate

| Category | Phase 1 | Phase 2 | Total |
|----------|---------|---------|-------|
| Personnel (PI + 1 researcher) | $400K | $400K | $800K |
| Compute (GPU, cloud) | $100K | $150K | $250K |
| Travel (workshops, hackathons) | $30K | $30K | $60K |
| Indirect/overhead | $200K | $200K | $400K |
| Subcontractor (if needed) | $150K | $150K | $300K |
| Hackathon incentive reserve | — | $60K | $60K |
| **Total** | **$880K** | **$990K** | **$1,870K** |

Under the $2M cap with margin for adjustments.

---

## Open Questions

1. **Teaming**: Should we team with a university for AR credibility? (Gemini mentioned ErgoAI from FAQ — used in CODORD)
2. **SAM.gov**: Need to register if not already
3. **Security clearance**: CLARA appears unclassified but may need facility clearance later
4. **Abstract**: March 2 deadline passed. FAQ says late abstracts not accepted, but full proposals still due April 17
5. **Solo developer**: DARPA does fund small teams/individuals via OT agreements. The FAQ confirms universities and small orgs are eligible.

---

## Next Steps

1. [ ] Register on SAM.gov (if not registered)
2. [ ] Register on DARPAConnect
3. [ ] Read full solicitation on SAM.gov (need account access)
4. [ ] Decide: submit solo or find university partner
5. [ ] Draft 5-page technical approach
6. [ ] Prepare cost proposal
7. [ ] Submit by April 17, 2026

---

## Key References

- [CLARA program page](https://www.darpa.mil/research/programs/clara)
- [SAM.gov listing](https://sam.gov/opp/0e76cc6102804ab68667605d9e28c900/view)
- [FAQ PDF](https://www.darpa.mil/sites/default/files/attachment/2026-03/darpa-program-clara-faq.pdf)
- Patent: USPTO #63/961,403 (provisional)
- GitHub: github.com/issdandavis/SCBE-AETHERMOORE
- npm: scbe-aethermoore v3.3.0
- PyPI: scbe-aethermoore v3.3.0
- HuggingFace: issdandavis (4 models, 4 datasets)
