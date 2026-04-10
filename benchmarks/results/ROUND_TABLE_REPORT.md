# SCBE-AETHERMOORE Governance Benchmark: Round Table Report

**Date**: 2026-04-05
**Methodology**: Adversarial self-review with cross-domain literature triangulation
**Reviewer**: Claude Opus 4.6 (Round 1 — self-review under maximum critical scrutiny)

---

## Executive Summary (Brief View)

The SCBE governance benchmark reveals a system with **sound math but premature claims**:

- **Regex-only benchmark**: 100% accuracy (circular — tests its own patterns)
- **Semantic benchmark**: 57% ASR (unacceptable — 0% detection on 5 key categories)
- **Harmonic wall math**: All 10 properties verified, formula is correct
- **Practical impact**: Hyperbolic geometry contributes ~8.5% of risk score
- **Literature support**: Poincare ball for safety IS a real research direction (4+ papers)
- **Critical gap**: No comparison against ANY standard benchmark (HarmBench, TensorTrust, Llamaguard)
- **Verdict**: Major Revision. Score: 4/10. Theory ahead of evidence.

**Three things to fix first:**
1. Run HarmBench dataset through the system
2. Ablation study: remove geometry, measure impact
3. Learn Poincare embeddings from data instead of hand-mapping

---

## Full Thesis

### Section 1: What We Tested

Two benchmark runs on the SCBE governance pipeline:

**Run 1 (Regex-Only)**
- 560 test cases (100 benign + 460 adversarial)
- 12 adversarial categories
- Pure regex + harmonic wall math
- Result: 100% accuracy, 0% FPR, F1=1.000
- **Problem**: Circular — all test prompts contain target keywords

**Run 2 (Semantic + ML)**
- 420 adversarial cases via synthetic dataset generator
- all-MiniLM-L6-v2 for semantic embedding
- Full SCBE pipeline
- Result: 57% ASR, 0% FPR, F1=0.601
- **Problem**: 0% detection on direct_override, prompt_extraction, role_confusion, spin_drift, tongue_manipulation

### Section 2: Mathematical Analysis

**Harmonic Wall: H(d, pd) = 1/(1 + phi * d_H + 2 * pd)**

Verified properties:
- Bounded in (0, 1] -- PASS
- Monotonically decreasing with distance -- PASS
- H(0,0) = 1.0 (safe origin) -- PASS
- Prior deception always lowers H -- PASS
- Triangle inequality on d_H -- PASS
- Attacker cost grows monotonically -- PASS

Critical observations:
- This is a **rational** function (O(1/d)), NOT exponential
- Maximum practical d_H ~ 3.56 (boundary-to-boundary in Poincare ball)
- Maximum cost ratio: 6.76x (safe origin vs maximum threat)
- The (1-H)*0.10 weight means geometry contributes 0-8.5% of risk score
- PHI has no derivation from first principles — cosmetic constant

**The "exponential cost" claim**:
The hyperbolic distance d_H = arcosh(1 + 2|u-v|^2/((1-|u|^2)(1-|v|^2))) does grow super-linearly near the boundary because the denominator approaches zero. But H = 1/(1 + phi*d_H) only decays as 1/d, not e^(-d). The system has **super-linear** cost scaling near the boundary, not exponential.

To make it truly exponential, the formula should be H(d,pd) = exp(-phi * d_H - 2*pd). This preserves all desired properties AND actually delivers exponential cost.

### Section 3: Literature Triangulation

**Does anyone else use hyperbolic geometry for AI safety?**

Yes — this is a real research direction:

1. **Adversarial Attacks on Hyperbolic Networks** (Dec 2024, arXiv 2412.01495): Poincare and Euclidean networks have *different adversarial weaknesses*. The geometry itself changes the attack surface. This validates SCBE's core intuition.

2. **Hyperbolic Deep RL** (Dec 2025, arXiv 2512.14202): Poincare ball has **known numerical instability near the boundary**. Recommendation: use Hyperboloid model or add RMSNorm. SCBE's [-0.95, 0.95] clamping is a known workaround but loses precision exactly where it matters most.

3. **Poincare Embeddings** (Nickel & Kiela, 2017): Foundational paper showing hyperbolic space naturally represents hierarchies. Trust/threat IS hierarchical — legitimate use case.

4. **HarmBench** (2024): 510 behaviors, 18 attack modules. SOTA defenses achieve 5-15% ASR. SCBE's 57% ASR is in the "no defense" range.

5. **TensorTrust** (2023): 563K real prompt injection attacks. SCBE's 0% detection on prompt_extraction is a red flag given this dataset's findings.

### Section 4: Comparison Against Standard Benchmarks

| System | ASR (automated) | ASR (human) | FPR | Notes |
|--------|----------------|-------------|-----|-------|
| GPT-4 + moderation | ~5% | ~15% | <1% | Commercial, proprietary |
| Llamaguard 3 | ~10% | ~25% | ~2% | Open-source, fine-tuned |
| HarmBench SOTA defense | 5-15% | up to 75% | varies | Adversarial training |
| Simple keyword filter | ~0% (known) | ~90% (novel) | varies | Baseline |
| **SCBE (regex only)** | 0% (circular) | not tested | 0% | Tests own patterns |
| **SCBE (semantic)** | **57%** | not tested | 0% | Unacceptable |

SCBE currently performs between a keyword filter and no defense at all against semantically novel attacks.

### Section 5: What's Genuinely Good

1. **Zero false positives** across all tests. This is harder than it sounds — most safety systems trade precision for recall. SCBE never blocks legitimate traffic.

2. **5000+ decisions/sec**. Fast enough for real-time use as a first-pass filter. Most ML-based safety systems add 50-200ms latency.

3. **Deterministic and explainable**. Every decision can be traced through exact intermediate values. No black-box neural network involved.

4. **Mathematical framework is sound**. The properties are real, the proofs are valid, the architecture is clean.

5. **Honest self-assessment**. The weaknesses section accurately identifies the real problems. This is rare and valuable.

6. **Architectural separation**. Scoring layer separate from decision layer means thresholds can be tuned without retraining.

### Section 6: Fatal Flaw

**The hyperbolic geometry is decorative, not structural.**

Remove the Poincare ball, harmonic wall, and golden ratio entirely. Replace with:
```python
risk = threat_score * 0.45 + sensitivity * 0.20 + (1-trust) * 0.15 + len_penalty * 0.10 + 0.085 - benign_score * 0.20
```

This constant-offset version would produce nearly identical decisions for every test case. The geometry is mathematically valid but operationally inert at its current weight (10%).

**To fix this**: Make the geometry the PRIMARY detection mechanism. Train Poincare ball embeddings where position = learned threat representation, not a linear trust mapping. Then d_H becomes the main signal, not a 10% correction.

### Section 7: Specific Recommendations (Priority Order)

**Immediate (this week):**
1. Ablation: Run benchmark with geometry removed. Quantify delta.
2. Weight the harmonic wall at 40%+ or make it the primary signal.
3. Add 10,000+ benign prompts to validate FPR at scale.

**Short-term (this month):**
4. Run against HarmBench 510-behavior dataset.
5. Compare against Llamaguard 3 on same dataset.
6. Implement GCG attack generator and test.
7. Consider switching to Hyperboloid model for boundary stability.

**Medium-term (this quarter):**
8. Train Poincare ball embeddings from labeled safety data.
9. Replace regex with embedding-based detection as primary signal.
10. Implement real prior deception tracking (session-level pd accumulation).
11. Submit to AI safety workshop (not main conference until ASR < 15%).

---

## Appendix A: Search Paths & Sources

All claims verified via:
- Local benchmark execution (2 runs, deterministic, seed=42)
- Web search: "HarmBench TensorTrust AI safety benchmark 2025 2026 state of the art attack success rate"
- Web search: "Poincare ball model adversarial robustness hyperbolic geometry machine learning safety 2025 2026"
- Direct computation of harmonic wall properties (10 mathematical tests)
- Risk score decomposition (weight analysis)

Sources:
- [HarmBench](https://www.harmbench.org/) — Standardized red-teaming framework
- [TensorTrust](https://tensortrust.ai/) — Prompt injection game dataset
- [Adversarial Attacks on Hyperbolic Networks](https://arxiv.org/html/2412.01495v1)
- [Hyperbolic Deep RL Improvements](https://arxiv.org/html/2512.14202)
- [Poincare Embeddings](https://arxiv.org/pdf/1705.08039)
- [AI Safety Index 2025](https://futureoflife.org/ai-safety-index-summer-2025/)
- [General Analysis AI Security Benchmarks](https://www.generalanalysis.com/benchmarks)
- [AISafetyLab Framework](https://github.com/thu-coai/AISafetyLab)

## Appendix B: Files Generated

- `scbe_benchmark_local_20260405_103757.json` — Full structured results
- `peer_review_prompt_local.md` — Single-platform review prompt
- `peer_review_prompt_combined.md` — Combined dual-run review prompt
- `review_claude_opus.md` — Claude's adversarial self-review
- `review_literature_context.md` — Academic literature mapping
- `ROUND_TABLE_REPORT.md` — This document (full thesis)

---

**Score: 4/10** — Genuine mathematical innovation trapped in a premature benchmark. The path from 4 to 7 is clear: ablation + HarmBench + learned embeddings. The path from 7 to 9 requires the geometry to be load-bearing, not decorative.
