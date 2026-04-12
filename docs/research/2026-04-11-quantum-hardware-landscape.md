# Quantum Hardware Landscape & FTQC V&V — Reference Brief

**Date**: 2026-04-11
**Purpose**: Reference documentation on the current state of utility-scale fault-tolerant quantum computing (FTQC), hardware modality roadmaps, and verification & validation (V&V) tooling gaps.
**Framing**: This is a **technical landscape reference** for understanding where quantum hardware is headed and where classical-side tooling gaps exist. It is **NOT** a proposal-opportunity assessment. Source material was originally gathered for a DARPA QBI 2026 (DARPA-PA-26-02) review; the "fit assessment" section is retained as honest self-calibration on where SCBE's classical strengths do and do not overlap with quantum V&V problems.

---

## 1. Hardware Modalities (2024-2026 snapshot)

**Superconducting (IBM, Google, Rigetti, IQM)**
- **IBM**: Roadmap published 2023, updated Nov 2024. Condor (1,121 qubits, Dec 2023) was the last pure scale-up. Pivot to error correction: Heron (156 qubits, tunable couplers) is the current workhorse. Kookaburra/Flamingo/Blue Jay on roadmap through 2029 targeting modular multi-chip FTQC. Quantum System Two operational at Cleveland Clinic, RIKEN. IBM's revised 2024 roadmap claims ~200 logical qubits / 100M gates by 2029 using qLDPC "gross code" (Bravyi et al., Nature 2024, [arXiv:2308.07915](https://arxiv.org/abs/2308.07915)) — a major departure from surface code, ~10x overhead reduction.
- **Google Quantum AI**: Willow chip (105 qubits, Dec 2024) demonstrated below-threshold surface code scaling ([Nature 2024](https://www.nature.com/articles/s41586-024-08449-y)) — logical error rate halved each time code distance increased (d=3→5→7). Single logical qubit, but first experimental proof of scalable error correction. Target: 100 logical qubits by ~2030.
- **Rigetti**: Ankaa-3 (84 qubits, 99.5% 2Q fidelity), targeting 108+ qubits 2025-2026. Currently sub-scale.
- **IQM**: 150-qubit system targeted 2025; modular architecture.

**Trapped ion (IonQ, Quantinuum)**
- **Quantinuum**: H2 trapped-ion (56 qubits, 99.87% 2Q fidelity, all-to-all connectivity). Demonstrated 12 logical qubits with fault-tolerant entangling gates using [[7,1,3]] Steane code (2024). Roadmap: Helios (~96 physical), Sol (~192), Apollo (~400-1000 logical) by 2029-2030.
- **IonQ**: Forte/Tempo (35-64 algorithmic qubits). Acquired Oxford Ionics (2024) for fabrication path. Targeted ~2 million physical qubits by 2030 (aspirational).

**Neutral atom (QuEra, Atom Computing, Pasqal, Infleqtion)**
- **Atom Computing + Microsoft (2024)**: 24 logical qubits from 256 physical atoms, 28 logical qubits demonstrated ([arXiv:2411.11822](https://arxiv.org/abs/2411.11822)) — currently highest logical qubit count.
- **QuEra**: 256-atom Aquila; 2024 logical qubit milestone with Harvard/MIT (48 logical qubits, transversal gates, [Nature 2024](https://www.nature.com/articles/s41586-023-06927-3)). Roadmap: 100 logical qubits 2026, 10,000 logical qubits 2030.
- **Pasqal**: 1000-atom analog system 2024; digital mode 2025.

**Photonic (PsiQuantum, Xanadu, QuiX)**
- **PsiQuantum**: $1B+ investor commitment; building million-physical-qubit facilities in Brisbane (Australia) and Chicago. Fusion-based quantum computing architecture. No published logical qubits yet; the bet is they go directly from R&D to utility scale.
- **Xanadu**: Borealis (Gaussian boson sampling); targeting photonic FTQC via GKP states.

**Topological (Microsoft Station Q)**
- Feb 2025: Majorana 1 chip announced with 8 topological qubits ([Nature 638, 651](https://www.nature.com/articles/s41586-024-08445-2)). The underlying claim of Majorana zero modes remains controversial — 2024 Nature referees published signed concerns about interpretation. If real, ~1M qubits single chip possible; if not, decades away.

**Spin-based (Intel, Quantum Motion, Diraq)**
- **Intel**: Tunnel Falls (12 qubits silicon spin), 2023; targeting "quantum chip in a fab" leveraging CMOS. Physically small, currently sub-scale.
- **Diraq / UNSW**: high-fidelity donor spin qubits; research stage.

---

## 2. What "Utility-Scale" Actually Means

**Error correction overhead** (surface code, d=25 for Shor-scale work):
- Logical error rate target: ~10^-10 to 10^-15 per gate
- Surface code overhead: ~1000-10,000 physical qubits per logical qubit
- qLDPC codes (IBM gross code, 2024): 144 physical → 12 logical (~12x ratio), but require long-range connectivity — open hardware problem.

**Application targets (Gidney-Ekera 2019 / 2025 updates)**:
- **RSA-2048 (Shor's)**: Original estimate 20M physical qubits, 8 hours. Recent [Gidney 2025](https://arxiv.org/abs/2505.15917) revised to ~1M noisy qubits with better factoring and qLDPC — still orders of magnitude above today.
- **FeMoCo (nitrogenase chemistry)**: ~4,000 logical qubits, ~10^10 T-gates (Reiher et al., 2017; [Lee et al. 2021](https://arxiv.org/abs/2011.03494))
- **Cuprate superconductor simulation**: ~1,000-2,000 logical qubits
- **Quantum advantage without FTQC**: Google random circuit sampling (2019, 2023), Gaussian boson sampling — no economic value.

**The gap**: Today's best logical count is 48 (QuEra/Harvard). Utility scale needs ~1000-10,000 logical qubits. That is 20-200x away at the logical layer, but the real barrier is the physical-layer scaling AND the two-qubit fidelity floor (~99.9% isn't enough for most codes; need 99.99%+). Every modality is currently stuck on either (a) fidelity, (b) connectivity, or (c) fabrication yield.

---

## 3. V&V Tooling Gaps

**Known problems at scale**:

- **Full state tomography is exponential** — infeasible beyond ~10 qubits. Shadow tomography ([Huang, Kueng, Preskill 2020](https://arxiv.org/abs/2002.08953)) scales to ~100s but still can't validate arbitrary claims about a million-qubit device.
- **Randomized benchmarking (RB) saturates** — Standard Clifford RB only measures average gate error, not worst-case or correlated errors. Cycle benchmarking and mirror circuits ([Proctor et al., PRX Quantum 2022](https://arxiv.org/abs/2008.11294)) partially address this but hit scaling walls past ~100 qubits.
- **Cross-entropy benchmarking (XEB)** requires classical simulation of the same circuit — by construction impossible at utility scale. Circular validation problem.
- **Logical-layer V&V is essentially unsolved**. How do you verify that a 1000-logical-qubit machine is actually computing correctly when you cannot classically simulate even one logical operation? Proposals: holographic benchmarking, reverse-simulation circuits, certified randomness (Aaronson), but none are production-ready.
- **Compiler verification**: Translating a high-level quantum algorithm to fault-tolerant circuits involves magic state distillation, code switching, lattice surgery. [SQIR / VOQC (Hietala et al., 2019-2022)](https://dl.acm.org/doi/10.1145/3434318) are the only formal-methods compiler verification projects that have reached production. Gap: no end-to-end formally verified stack from algorithm → logical → physical.
- **Error correction validation**: How do you know a QEC cycle is actually suppressing errors and not re-injecting them? Requires post-selection analysis, correlated error detection. Current approach (Google Willow) is experimental curve-fitting, not formal verification.
- **Control-electronics/cryogenic integration**: No rigorous V&V framework for the full stack (FPGAs, DACs, classical decoders, cryogenic amplifiers) under realistic noise.

**Specific references**:
- [Eisert et al. 2020, "Quantum certification and benchmarking"](https://www.nature.com/articles/s42254-020-0186-4) — comprehensive V&V review
- [Proctor et al. 2025, PRX Quantum, "Benchmarking quantum computers"](https://arxiv.org/abs/2407.08828)
- [NIST IR 8547 (2024)](https://csrc.nist.gov/pubs/ir/8547/ipd) — post-quantum crypto context
- DARPA QBI program page, Stage A/B/C structure — explicitly calls out "IV&V team augmentation" as a separable role.

---

## 4. Classical-Quantum Hybrid Workflow Governance

Variational algorithms (VQE, QAOA) and quantum-enhanced ML pipelines already involve:
- classical optimizer loops (SciPy, gradient methods)
- shot-noise-sensitive cost-function evaluation
- error mitigation (zero-noise extrapolation, probabilistic error cancellation, Clifford data regression)
- pre/post-processing with classical data (chemistry active space selection, finance scenario generation)

**Real gaps**:
- **Audit trails for hybrid workflows** — Which classical step introduced which error? Almost no tooling for end-to-end provenance across classical→quantum→classical boundaries.
- **Error-mitigation verification** — ZNE and PEC extrapolate, and their validity depends on noise model assumptions that rarely come with bounds. [Quek et al. 2024](https://arxiv.org/abs/2210.11505) showed error mitigation has exponential sample complexity walls.
- **Governance for hybrid ML** — No standard for attesting that a quantum subroutine in an ML pipeline behaves within spec, much less meets fairness/safety constraints.
- **Reproducibility** — drift, recalibration, decoherence over wall-clock time; no canonical versioning of "this quantum state on this hardware at this time."
- **Supply-chain trust** — control software, firmware, QEC decoders; no SBOM equivalent for quantum stacks.

This layer is classical-software-centric, and is where a governance/formal-methods group without quantum hardware can credibly contribute.

---

## 5. SCBE Self-Calibration (NOT an opportunity assessment)

Retained for honest understanding of where SCBE's classical strengths intersect quantum V&V — useful for future conversations about hybrid stacks, not as a pursuit decision.

**Where SCBE does NOT overlap**: quantum hardware, circuit compilation, QEC code implementation, fabrication, tomography. Zero track record in any of these.

**Where SCBE's existing work IS structurally adjacent to quantum V&V needs**:
- 14-layer formal axiom pipeline → methodology for decomposing claims into verifiable sub-properties (compiler-verification pattern)
- Hyperbolic cost-scaling governance → novel benchmarking framing (treat adversarial drift / calibration drift as a distance from nominal)
- Post-quantum crypto fluency → supply-chain attestation, post-QBI security story
- Classical audit/ledger infrastructure → hybrid-workflow provenance (the Section 4 gaps)

**Honest weaknesses for any quantum-adjacent work**: no published quantum V&V papers, no QEC publications, no quantum benchmarking track record, no existing collaborators in the quantum hardware ecosystem.

**Key insight for future architecture thinking**: the most interesting structural overlap isn't with quantum hardware V&V — it's with **hybrid workflow governance** (Section 4). That's classical-software territory where the formal-methods + provenance + error-attribution + audit-trail problems look a lot like what SCBE's 14-layer pipeline already does for AI governance. If quantum ever becomes a substrate SCBE cares about, the entry point is the classical-quantum boundary, not the quantum internals.

---

## Source material

- DARPA QBI 2026 PA: DARPA-PA-26-02, posted 2025-11-14, parent for follow-on QBIT topic calls
- Notice ID DARPA-PA-26-02, NAICS 541715, PSC AC12, full and open competition
- QBI CUI Guide (signed 2025-06-11)
- Vendor roadmaps via public press releases and arXiv preprints cited inline above
