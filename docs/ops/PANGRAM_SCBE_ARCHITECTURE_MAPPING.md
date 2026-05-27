# Pangram × SCBE 14-Layer Pipeline — Architecture Mapping

**Status:** Draft  
**Date:** 2026-05-24  
**Scope:** Reference benchmark + optional integration path for external AI-authorship verification  

---

## Executive Summary

[Pangram Labs](https://www.pangram.com/) is a commercial AI text-detection tool with independently verified near-zero false-positive rates (Jabarian & Imas 2025, Chicago Booth). It is **not** a replacement for SCBE governance — it is an **external oracle** that provides an authorship-authenticity signal SCBE can ingest, benchmark against, or expose as a publishing gate.

This document maps Pangram's detection architecture onto SCBE's 14-layer hyperbolic geometry pipeline, identifies integration points, and defines a threat model for when SCBE should trust, distrust, or ignore external detection signals.

---

## 1. Pangram Technical Profile

| Attribute | Value |
|---|---|
| **Detection target** | AI-generated / AI-assisted / human-written text |
| **Model** | Proprietary deep-learning classifier (not perplexity-based) |
| **Context window** | 1,024 tokens |
| **Long-document mode** | Adaptive Boundaries — two-pass sentence-aware windowing |
| **Output taxonomy** | `fraction_ai` + `fraction_ai_assisted` + `fraction_human` (v3) |
| **FPR (verified)** | ≤ 0.005 (1 in 10,000) at stringent policy cap |
| **FNR (verified)** | Near-zero on contemporary LLMs |
| **Latency** | 300–500 ms per API call |
| **Languages** | 25+ including Chinese (Simplified/Traditional) |
| **Evasion resistance** | Detects humanized/obfuscated text at 400% improved rate (v3.2) |
| **Pricing** | Free: 4 checks/day; Developer: $25/500 credits; Individual: $20/mo 600 scans |

**Academic anchor:**  
> *"Pangram is the only detector that meets a stringent policy cap (FPR ≤ 0.005) without compromising the ability to accurately detect AI text."*  
> — Jabarian & Imas (2025), *Artificial Writing and Automated Detection*, Chicago Booth

---

## 2. SCBE 14-Layer Pipeline — Quick Reference

| Layer | Name | Governance Function |
|---|---|---|
| L0 | Intent Modulation | Feistel scrambling of input vector |
| L1 | Complex State | ℂᴰ amplitude+phase embedding |
| L2 | Realification | ℝ²ᴰ isometric split |
| L3 | Weighted Transform | SPD trust-weighting |
| L4 | Poincaré Embedding | Hyperbolic ball projection |
| L5 | Hyperbolic Distance | `d_ℍ(u,v)` metric |
| L6 | Breathing Transform | Dynamic radial rescaling |
| L7 | Phase Transform | Angular phase alignment |
| L8 | Multi-Well Realms | Stability well assignment |
| L9 | Spectral Coherence | Frequency-domain verification |
| L10 | Spin Coherence | Quantum-inspired state lock |
| L11 | Triadic Temporal | Time-based validation + intent aggregation |
| L12 | Harmonic Wall | Hard boundary `H(d*,R) = R^((φ·d*)²)` |
| L13 | Composite Risk | Risk aggregation across all layers |
| L14 | Audio Axis | Final output encoding / dispatch decision |

**Decision ontology:** `ALLOW` / `DENY` / `QUARANTINE`

---

## 3. Cross-Architecture Mapping

### 3.1 Signal-Ingestion Layer (L1–L3): Text → Feature Vector

| SCBE Layer | SCBE Behavior | Pangram Analog | Integration Note |
|---|---|---|---|
| **L1 Complex State** | Amplitude + phase from raw context | Pangram tokenizes input into a 1,024-token context window using a standard multilingual tokenizer | **No direct coupling.** Pangram's tokenizer is opaque; SCBE should treat its output as a black-box scalar signal, not as a replaceable L1 module. |
| **L2 Realification** | `ℝ²ᴰ` split of complex state | Pangram does not expose latent-space geometry | **Do not attempt to merge embeddings.** Use Pangram's aggregate scores (`fraction_ai`, `fraction_human`) as external observables fed into L3 weighting. |
| **L3 Weighted Transform** | SPD matrix `G` applies trust weights | Pangram's FPR ≤ 0.005 gives it a high trust weight in the publishing domain | **Recommended:** Assign Pangram a trust weight `w_pangram ≈ 0.85–0.90` in publishing scenarios, lower (`≈ 0.60`) in adversarial red-team contexts where evasion is expected. |

**Key principle:** Pangram is an **external observable**, not an internal layer replacement. SCBE's L1–L3 remain canonical for all geometry-derived decisions.

---

### 3.2 Geometry & Distance Layers (L4–L6): Trust Topology

| SCBE Layer | SCBE Behavior | Pangram Analog | Integration Note |
|---|---|---|---|
| **L4 Poincaré Embedding** | Projects state into hyperbolic ball `𝔹ⁿ` | Pangram's classifier operates in its own (undisclosed) latent space | **No mapping attempted.** Keep Pangram outside the hyperbolic manifold to preserve mathematical integrity. |
| **L5 Hyperbolic Distance** | `arcosh(1 + 2‖u−v‖² / …)` | Not applicable | Use Pangram's score as a **separate distance axis** in L13 Composite Risk, not as a replacement for `d_ℍ`. |
| **L6 Breathing Transform** | Radial rescaling `T_breath(u)` | Pangram v3's "Adaptive Boundaries" dynamically resize windows around uncertain regions | **Conceptual parallel only.** Both systems adapt resolution to local uncertainty, but the mathematics are unrelated. Do not merge. |

---

### 3.3 Spectral & Phase Layers (L7–L10): Decomposition & Verification

| SCBE Layer | SCBE Behavior | Pangram Analog | Integration Note |
|---|---|---|---|
| **L7 Phase Transform** | Angular phase alignment | Not applicable | — |
| **L8 Multi-Well Realms** | Stability well assignment | Not applicable | — |
| **L9 Spectral Coherence** | Frequency-domain verification | Pangram's **window-level analysis** decomposes a document into segments and scores each independently | **Strong analogy.** Pangram's windows are like spectral bins. SCBE can ingest per-window scores as a **coherence spectrum** and flag documents with high variance across windows (indicates patchy AI assistance). |
| **L10 Spin Coherence** | Quantum-inspired state lock | Not applicable | — |

**L9 Integration Pattern:**
```python
# Pseudo-code for L9-spectral ingestion
window_scores = pangram_result.windows  # List of per-segment scores
spectral_variance = variance([w.ai_assistance_score for w in window_scores])
if spectral_variance > threshold:
    # Document is "patchy" — some sections human, some AI
    risk_vector.patchiness = spectral_variance
```

---

### 3.4 Temporal & Triadic Layers (L11): Three-State Classification

| SCBE Layer | SCBE Behavior | Pangram Analog | Integration Note |
|---|---|---|---|
| **L11 Triadic Temporal** | Time-based validation; three-state logic | Pangram v3's **three-class taxonomy** (`Human` / `AI-Assisted` / `AI`) | **Direct mapping.** Pangram's three-way classification can feed into SCBE's triadic state engine without translation loss. This is the cleanest integration point in the entire stack. |

**Triadic state mapping:**
| Pangram v3 Label | SCBE Triadic State | Governance Action |
|---|---|---|
| `fraction_human > 0.90` | `STATE_HUMAN` | `ALLOW` |
| `fraction_ai_assisted > 0.30` | `STATE_ASSISTED` | `QUARANTINE` → manual review |
| `fraction_ai > 0.30` | `STATE_SYNTHETIC` | `DENY` or `QUARANTINE` |

---

### 3.5 Boundary & Aggregation Layers (L12–L14): Decision Gates

| SCBE Layer | SCBE Behavior | Pangram Analog | Integration Note |
|---|---|---|---|
| **L12 Harmonic Wall** | Hard boundary `H(d*,R)` | Pangram's FPR ≤ 0.005 is itself a **hard statistical wall** | **Benchmark reference:** Use Pangram's verified FPR as the gold-standard calibration target for SCBE's own content-authenticity wall. If SCBE's internal detector has FPR > 0.005, it is underperforming the external oracle. |
| **L13 Composite Risk** | Aggregates risk across all layers | Pangram score becomes one term in the risk summation | **Recommended formula:** `R_total = w_geo·R_geo + w_temp·R_temp + w_auth·R_auth` where `R_auth` is derived from Pangram's `fraction_ai` and `fraction_ai_assisted`. |
| **L14 Audio Axis** | Final dispatch encoding | Not applicable | Pangram has no audio modality. For audio intent verification, continue using SCBE's symphonic cipher (`ai_verifier.py`). |

---

## 4. Integration Patterns

### Pattern A: Reference Benchmark (Recommended)
SCBE's internal content-authenticity detector (if/when built) is evaluated against Pangram on a held-out test set. Pangram is **not** in the production inference path. This avoids latency, cost, and external dependency risks.

**When to use:** Model development, red-team exercises, academic publications.

### Pattern B: Publishing Pre-Flight Gate
Pangram is called as a **final check** before content leaves the SCBE Content Buffer for Twitter, LinkedIn, Medium, KDP, etc. If Pangram returns `fraction_ai > threshold`, the publish job is moved to `QUARANTINE` for human review.

**When to use:** High-stakes outbound content where reputational risk exceeds API cost.

**Latency impact:** +300–500 ms per document (acceptable for async publish pipeline).

### Pattern C: Manuscript Verification
For `book-workshop` and `watershed-cultivation`, Pangram scans chapters or full EPUBs to generate an **authorship report** that can be included in KDP metadata or shared with ARC readers as transparency evidence.

**When to use:** Book 1 launch, Chinese dual-language release, grant applications requiring provenance documentation.

### Pattern D: Flock Health Monitor
Pangram periodically samples agent-generated outputs in the SCBE flock. If a specific agent's outputs drift toward high `fraction_ai`, the flock shepherd quarantines that agent and triggers a trust-score recalculation.

**When to use:** Long-running autonomous agent deployments where model drift or prompt injection could cause synthetic-content spam.

---

## 5. Threat Model: When to Distrust Pangram

| Threat | Mitigation | SCBE Response |
|---|---|---|
| **API downtime** | Cache last-known scores; fallback to internal detector | Degrade gracefully; do not hard-fail publish pipeline |
| **Evasion attack** | Adversarial text engineered to fool Pangram | Treat Pangram as **one signal among many**; never single-point-of-failure |
| **Data exfiltration** | Pangram receives full text over HTTPS | Do **not** scan classified/proprietary text through commercial API; run internal SCBE analysis instead |
| **False positive on formal text** | Legal docs, technical specs, etc. may trigger low-confidence flags | Override with owner approval (`issdandavis` bypass gate) |
| **Cost overrun** | $0.05 per 1,000 words via Developer API | Budget cap in `PangramContentGate`; fail-open if quota exhausted |
| **Model obsolescence** | New LLM released that Pangram hasn't seen | Monitor Pangram's model-card updates; fall back to Pattern A (benchmark only) until verified |

---

## 6. Implementation Status

| Component | Status | Path |
|---|---|---|
| Prototype CLI scanner | ✅ Draft | `scripts/security/pangram_content_gate.py` |
| v3 API client | ✅ Draft | Embedded in scanner (no SDK dependency) |
| SCBE API endpoint integration | ⬜ Not started | TBD: `POST /v1/scan/authorship` |
| Content Buffer hook | ⬜ Not started | TBD: `src/content_buffer/pangram_hook.py` |
| Book-workshop report generator | ⬜ Not started | TBD: `scripts/book/generate_authorship_report.py` |
| Flock health monitor | ⬜ Not started | TBD: `src/fleet/health/pangram_sampler.py` |

---

## 7. Open Questions

1. **Should SCBE build its own text-authenticity detector?**  
   If yes, Pangram becomes the benchmark target (Pattern A). If no, Pangram becomes a production dependency (Pattern B/C).

2. **Chinese-market release:** Does Pangram's Chinese detection handle classical/literary register (e.g., cultivation fiction prose) as well as modern web text? Needs empirical test.

3. **Audio-axis parity:** Pangram is text-only. For audio intent authentication (Layer 14), SCBE's `ai_verifier.py` remains canonical. Should we benchmark audio synthetic-voice detection against a Pangram audio equivalent (if/when released)?

4. **Pricing at scale:** A 386-page manuscript (~90,000 words) costs ~$4.50 per scan at Developer API rates. Is this acceptable for pre-publish gating, or should we batch-sample chapters?

---

## 8. References

- Jabarian, B. & Emi, A. (2025). *Artificial Writing and Automated Detection*. Chicago Booth.
- Pangram Labs. (2026). [Pangram 3.1 Model Card](https://www.pangram.com/research/model-card/pangram-3-1).
- Pangram Labs. (2026). [v3 API Migration Guide](https://www.pangram.com/blog/v3-api-migration-guide).
- SCBE Canonical Formula Registry: `docs/specs/CANONICAL_FORMULA_REGISTRY.md`
- SCBE 14-Layer Reference: `src/scbe_14layer_reference.py`
- SCBE Code Governance Gate: `scripts/security/code_governance_gate.py`
