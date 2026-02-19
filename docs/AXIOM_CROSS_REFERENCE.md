# Axiom Cross-Reference

**Document ID**: SCBE-AXREF-2026-02-18
**Status**: ACTIVE -- Reconciles three axiom systems

---

## Three Axiom Systems

This project uses three overlapping axiom systems. They are not contradictory; they describe the same system at different levels of abstraction.

| System | Count | Date | File | Abstraction Level |
|--------|-------|------|------|-------------------|
| **Formal Axioms (FA)** | 13 | Jan 17, 2026 | `docs/08-reference/archive/AXIOMS.md` | Mathematical properties of cost function |
| **Pipeline Axioms (PA)** | 12 | Feb 2026 | `PATENT_DETAILED_DESCRIPTION.md` S12 | Layer-specific operational invariants |
| **Quantum Axioms (QA)** | 5 | v3.0.0 | `CLAUDE.md`, `axiom_grouped/*.py` | Physics-inspired groupings across layers |

---

## Cross-Reference Map

### Formal Axiom -> Pipeline Axiom -> Quantum Axiom

| FA# | Formal Axiom | Maps to PA# | Pipeline Axiom | Maps to QA | Verification |
|-----|-------------|-------------|---------------|------------|-------------|
| FA1 | Positivity of Cost | PA12 | Harmonic scaling H(d,R)=R^(d^2) | QA4: Symmetry | VERIFIED (431 tests) |
| FA2 | Monotonicity of Deviation | PA12 | Harmonic scaling (monotone in d) | QA4: Symmetry | VERIFIED |
| FA3 | Convexity of Cost Surface | PA12 | H(d,R) strictly convex for d>=0 | QA4: Symmetry | VERIFIED |
| FA4 | Bounded Temporal Breathing | PA8 | Breathing diffeomorphism b(t) | QA3: Causality | VERIFIED (post Jan 19) |
| FA5 | Smoothness (C-infinity) | PA5, PA7 | d_H and Mobius are smooth | QA4: Symmetry | VERIFIED (13/13 tests) |
| FA6 | Lyapunov Stability | PA6 | Breathing converges to safe state | QA3: Causality | VERIFIED (13/13 tests) |
| FA7 | Harmonic Resonance | PA10 | Spin coherence (all gates) | QA4: Symmetry | VERIFIED |
| FA8 | Quantum Resistance | -- | Not in PA (separate PQC layer) | -- | VERIFIED (ML-KEM + ML-DSA) |
| FA9 | Hyperbolic Geometry | PA5 | d_H invariant | QA4: Symmetry | VERIFIED |
| FA10 | Golden Ratio Weighting | PA3 | SPD weighting G_k = phi^k | QA2: Locality | VERIFIED |
| FA11 | Fractional Dimension Flux | -- | Not in PA (Claim 6/16) | -- | VERIFIED (13/13 tests) |
| FA12 | Topological Attack Detection | PA9 | Spectral coherence (PHDM) | QA4: Symmetry | VERIFIED |
| FA13 | Atomic Rekeying | -- | Not in PA (Claim 5 PQC) | -- | VERIFIED |

### Pipeline Axioms Not in Formal Axioms

| PA# | Pipeline Axiom | Why No FA Equivalent | Covered By |
|-----|---------------|---------------------|------------|
| PA1 | Complex Context c_k = A_k exp(i phi_k) | Input format, not property | QA5: Composition |
| PA2 | Realification isometry | Transform step, not property | QA1: Unitarity |
| PA4 | Poincare embedding with clamping | Projection step | QA1: Unitarity |
| PA6 | Mobius addition gyrovector | Algebraic operation | QA1: Unitarity |
| PA7 | Phase transform isometry | Isometry guarantee | QA4: Symmetry |
| PA9 | Realm distance 1-Lipschitz | Continuity bound | QA2: Locality |
| PA11 | Triadic temporal distance | Aggregation formula | QA3: Causality |

### Quantum Axiom Coverage

| QA# | Quantum Axiom | Layers | Formal Axiom Coverage | Pipeline Axiom Coverage |
|-----|-------------|--------|----------------------|------------------------|
| QA1 | Unitarity | L2, L4, L7 | FA5 (smoothness) | PA2, PA4, PA7 |
| QA2 | Locality | L3, L8 | FA10 (golden ratio) | PA3, PA9 |
| QA3 | Causality | L6, L11, L13 | FA4 (breathing), FA6 (stability) | PA6, PA8, PA11 |
| QA4 | Symmetry | L5, L9, L10, L12 | FA1-3, FA5, FA7, FA9, FA12 | PA5, PA10, PA12 |
| QA5 | Composition | L1, L14 | -- | PA1 |

---

## Gap Analysis

### Gaps in Formal Axioms (not covering pipeline concepts)

1. **No FA for triadic temporal distance** (PA11 / L11). The three-timescale aggregation d_tri = sqrt(lam1*d1^2 + lam2*d2^2 + lam3*dG^2) has no formal axiom stating its properties.
2. **No FA for realm assignment** (PA9 / L8). The nearest-centroid assignment d* = min_k d_H(u, mu_k) has no formal axiom.
3. **No FA for input composition** (PA1 / L1, L14). The complex context encoding and audio axis telemetry have no formal axiom.

### Gaps in Pipeline Axioms (not covering formal concepts)

1. **No PA for PQC** (FA8). The dual-lattice consensus (Claim 5) is not among the 12 pipeline axioms A1-A12.
2. **No PA for fractional flux** (FA11). The ODE dynamics (Claim 6/16) are not among A1-A12.
3. **No PA for atomic rekeying** (FA13). The rekeying mechanism (related to Claim 5) is not in A1-A12.

### Recommendation

The formal axioms (FA1-13) and pipeline axioms (A1-A12) are complementary, not contradictory. The FAs describe global mathematical properties; the PAs describe per-layer operational invariants. Both are needed. No unification is required, but this cross-reference should be maintained.

---

## Verification Status Summary

| System | Verified | Partial | Theoretical | Total |
|--------|----------|---------|-------------|-------|
| Formal Axioms (FA) | 13 | 0 | 0 | 13 |
| Pipeline Axioms (PA) | 8 proven claims + 10 untested | -- | -- | 12 |
| Quantum Axioms (QA) | 5 (by construction) | 0 | 0 | 5 |

Formal axioms: 13/13 verified as of Jan 19, 2026 (`test_theoretical_axioms.py`, 431+ tests).
Quantum axiom implementations: re-verified Feb 18, 2026 after 8 bug fixes (10/10 + 57/57 tests, `verify_all_axioms()` all True).
Pipeline axioms: verification status tracked per-claim in [CLAIMS_EVIDENCE_LEDGER.md](CLAIMS_EVIDENCE_LEDGER.md).
Quantum axioms: verified by construction (each groups existing verified layers).

### Feb 18, 2026 Axiom Bug Fixes

8 breaking points fixed across 5 Quantum Axiom implementations:

| # | File | Line | Fix |
|---|------|------|-----|
| 1 | `locality_axiom.py` | 64 | None operator bug: handle missing operator gracefully |
| 2 | `causality_axiom.py` | 106 | Time-state leakage: prevent cross-contamination |
| 3 | `causality_axiom.py` | 616 | Missing L11 triadic temporal distance argument |
| 4 | `symmetry_axiom.py` | 222 | Mobius invariance check correction |
| 5 | `symmetry_axiom.py` | 309 | Rotation-invariance verification fix |
| 6 | `symmetry_axiom.py` | 340 | Spin coherence bounded assertion |
| 7 | `symmetry_axiom.py` | 397, 433 | Harmonic scaling/inverse consistency |
| 8 | `unitarity_axiom.py` | 422 | Layer 4 unitarity verification |

Post-fix results: 10 passed + 57 passed, `verify_all_axioms()` returns all True.

---

## Source Files

| File | Content |
|------|---------|
| `docs/08-reference/archive/AXIOMS.md` | Formal axioms 1-13 (canonical) |
| `docs/archive/AXIOM_VERIFICATION_STATUS.md` | Jan 18 verification (9/13 + 3 partial + 1 theoretical) |
| `docs/archive/THEORETICAL_AXIOMS_COMPLETE.md` | Jan 19 verification (13/13 complete) |
| `PATENT_DETAILED_DESCRIPTION.md` S12 | Pipeline axioms A1-A12 |
| `CLAUDE.md` | Quantum axiom mesh (5 axioms) |
| `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/` | Quantum axiom implementations |
| `tests/industry_standard/test_theoretical_axioms.py` | FA5, FA6, FA11 test suite |
| `tests/test_theoretical_axioms.py` | Copy of above |

---

*Updated Feb 18, 2026 with axiom re-verification status.*
*See [LANGUAGE_GUARDRAILS.md](LANGUAGE_GUARDRAILS.md) for writing standards.*
