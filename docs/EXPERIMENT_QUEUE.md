# Experiment Queue

**Document ID**: SCBE-EXPQ-2026-02-18
**Source**: [CLAIMS_AUDIT_V4.md](CLAIMS_AUDIT_V4.md) remaining experiments + [CLAIMS_EVIDENCE_LEDGER.md](CLAIMS_EVIDENCE_LEDGER.md) CODE_EXISTS_UNTESTED items
**Status**: ACTIVE

---

## Queue Priority Tiers

| Tier | Meaning | Promotion Effect |
|------|---------|-----------------|
| **Q0** | Reproducibility gate -- re-run existing proofs | Confirms PROVEN status holds |
| **Q1** | Core validation -- directly promotes patent claims | CODE_EXISTS_UNTESTED -> PROVEN |
| **Q2** | Comparative -- validates novelty vs baselines | Strengthens patent defense |
| **Q3** | Extension -- extends proven claims to new domains | Adds dependent claims |
| **Q4** | Research -- exploratory, may yield new claims | New IP potential |
| **Q5** | Nice-to-have -- low urgency | Polish |

---

## Q0: Reproducibility Gate

| ID | Experiment | Claims | Pass Criterion | Status |
|----|-----------|--------|---------------|--------|
| Q0-1 | Re-run Exp 4 (combined 3-mechanism) on fresh seed | 1, G | AUC >= 0.99 across 6 attack types | PENDING |
| Q0-2 | Re-run SE-1 (predicate matrix) 100 trials | 4, H | 100% gate accuracy maintained | PENDING |
| Q0-3 | Re-run SE-3 (geometry separation) at 1e-15 | 4, 11 | 100% AEAD failure at any perturbation | PENDING |

**Estimated effort**: 1 hour (scripts exist, just re-run with new seed)

---

## Q1: Core Claim Promotion

| ID | Experiment | Claims to Promote | What to Measure | Pass Criterion | Status |
|----|-----------|-------------------|-----------------|---------------|--------|
| Q1-1 | Phase+distance on real sentence-transformer embeddings | 1 (real-world) | AUC on HuggingFace embeddings (not synthetic) | AUC >= 0.90 | PENDING |
| Q1-2 | Anti-fragile pressure response | 6, 16 | Psi(P) expansion under sustained BOUNDARY_PROBE | Distance increases monotonically with P | PENDING |
| Q1-3 | Dual-lattice adversarial consensus | 5, 12 | Consensus rejects tampered Kyber OR tampered Dilithium | 100% rejection on single-lattice tamper | PENDING |
| Q1-4 | Sacred Eggs genesis gate (phi^3 threshold) | 15 | Genesis certificate vs noise output | 100% gate at W >= 4.236, 100% noise below | PENDING |
| Q1-5 | Roundtable multi-sig quorum escalation | 20 | 1-sig, 2-sig, 3-sig, 4-sig operations | Correct tier enforcement at each level | PENDING |

**Estimated effort**: 3-5 hours (code exists, need experiment harness)

---

## Q2: Comparative / Novelty Validation

| ID | Experiment | Claims | What to Compare | Pass Criterion | Status |
|----|-----------|--------|----------------|---------------|--------|
| Q2-1 | LWS (golden-ratio) vs uniform weighting | 3, 14 | Langues Metric with phi^k vs uniform w=1 | LWS AUC > uniform AUC by >= 5% | PENDING |
| Q2-2 | Spectral coherence vs simple threshold | 1 (L9-10) | FFT energy ratio vs cosine similarity | Spectral catches traffic manipulation that cosine misses | PENDING |
| Q2-3 | Cheapest-reject-first ordering measurement | 13 | Empirical rejection stage distribution | >= 60% rejected at O(1) stages | PENDING |
| Q2-4 | Breathing transform error surface | 7 | AUC with b=1.0 (no breathing) vs b adaptive | Adaptive b improves AUC | PENDING |

**Estimated effort**: 5-8 hours (needs new experiment code)

---

## Q3: Extension to New Domains

| ID | Experiment | Claims | Extension Target | Pass Criterion | Status |
|----|-----------|--------|-----------------|---------------|--------|
| Q3-1 | PHDM Hamiltonian path audit traceability | 17 (dependent D) | ROP detection via dimensional lifting | >= 90% ROP detection rate | PENDING |
| Q3-2 | Flux-state routing under pressure | 6, 16 | Route decisions change per Polly/Quasi/Demi state | Correct routing in each state | PENDING |
| Q3-3 | Dual-lane manifold intersection | 17 | K_intersect requires both S^2 and [0,1]^m | K_in alone fails, K_out alone fails, K_intersect succeeds | PENDING |
| Q3-4 | Physics-based trap cipher detection | 18 | Impossible-physics challenges vs agent classification | Zero false positives on legitimate agents | PENDING |
| Q3-5 | Provenance chain tamper detection | 21 | Tamper any field in provenance cert | 100% detection of tampered certs | PENDING |
| Q3-6 | Multi-model modal matrix governance | NEW | M models x N modalities voting matrix | Reducer matches single-model decision within tolerance | PENDING |

**Estimated effort**: 10-15 hours (new code + new test frameworks)

---

## Q4: Research / New IP

| ID | Experiment | Potential Claim | Hypothesis | Status |
|----|-----------|----------------|-----------|--------|
| Q4-1 | Chladni eigenmode geometry-as-key steganography | NEW | Cymatic patterns encode keys in geometry | PENDING |
| Q4-2 | Quasi-vector spin voxels (L5-L8 extension) | NEW | Spin Hamiltonian coupling improves detection | PENDING |
| Q4-3 | Multi-model consensus voting matrix | NEW | M-model disagreement catches adversarial inputs | PENDING |

---

## Q5: Nice-to-Have

| ID | Experiment | Purpose | Status |
|----|-----------|---------|--------|
| Q5-1 | Multi-agent coordination with drift-signature verification | Swarm interop demo | PENDING |
| Q5-2 | Cross-language parity (TypeScript vs Python) | Interop confidence | PENDING |
| Q5-3 | Performance benchmarking (latency per layer) | Production readiness | PENDING |

---

## Experiment Protocol Template

Each experiment must produce:

```
experiment_id: Q{tier}-{number}
date: YYYY-MM-DD
pipeline: [synthetic | real | real+embeddings]
trials: N (minimum 50 per condition)
seed: [random seed for reproducibility]
metrics: [AUC | accuracy | gate_rate | ...]
pass_criterion: [stated before running]
result: [PASS | FAIL | PARTIAL]
claims_promoted: [list of claim numbers]
artifact: [path to results file or notebook]
```

**Rule**: Pass criterion must be stated BEFORE the experiment runs. Post-hoc threshold adjustment is not allowed.

---

## Completion Tracker

| Tier | Total | Done | Remaining |
|------|-------|------|-----------|
| Q0 | 3 | 0 | 3 |
| Q1 | 5 | 0 | 5 |
| Q2 | 4 | 0 | 4 |
| Q3 | 6 | 0 | 6 |
| Q4 | 3 | 0 | 3 |
| Q5 | 3 | 0 | 3 |
| **Total** | **24** | **0** | **24** |

---

*Generated from CLAIMS_AUDIT_V4 remaining experiments + CLAIMS_EVIDENCE_LEDGER gap analysis*
*See LANGUAGE_GUARDRAILS.md for writing standards*
