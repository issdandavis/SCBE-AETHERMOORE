# ANNEX A — DFARS 252.227-7017 ASSERTIONS (Revision 2)

**Supersedes**: Annex A in `teaming_agreement_v2_draft.md` (2026-04-20)  
**Status**: WORKING DRAFT — requires Collin counter-signature on Part 2 before submission  
**Open item**: Item 2 from Collin's 2026-04-28 review (6th surface identity) — placeholder used below; replace before lock  
**Submission target**: DARPA-PA-26-05-MATHBAC-PA-010, full proposal due 2026-06-16  
**DFARS authority**: 252.227-7017 "Identification and Assertion of Use, Release, or Disclosure Restrictions"

---

## How to read this document

This Annex is structured in five layers. The first is the legally operative DFARS table. Layers 2–5 are technical and scientific supporting material — not legally required, but demonstrating to DARPA reviewers that the asserted IP is (a) already working, (b) measurably validated, and (c) integrated with the proposed TA1 research plan. DARPA evaluators — particularly applied mathematicians — value this specificity; it distinguishes a live program from a paper claim.

**Layer 1** — DFARS 252.227-7017 assertion tables (legally operative)  
**Layer 2** — Development basis and independence record per party  
**Layer 3** — Technical validation evidence with commit-level traceability  
**Layer 4** — Capability additions since Teaming Agreement v2 (2026-04-20 → 2026-05-31)  
**Layer 5** — CDPTI-External integration surface (joint work IP demarcation)

---

## LAYER 1 — DFARS 252.227-7017 ASSERTION TABLES

### Part 1 — Prime (Issac D. Davis / SCBE-AETHERMOORE) Assertions

| (1) Technical Data or Computer Software | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Asserting Party |
|---|---|---|---|
| **SCBE 14-Layer Governance Pipeline** — TypeScript canonical (`src/harmonic/pipeline14.ts` + 50+ modules), Python reference (`src/symphonic_cipher/.../fourteen_layer_pipeline.py`), Rust experimental (`rust/scbe_core/`). Implements L1–L14 operator composition `T = L14 ∘ ⋯ ∘ L1`. | Developed entirely at private expense, 2024–2026. No Government funding at any stage. Public commits predate DARPA-SN-26-59 issuance (2026-03-24). | Restricted Rights (software per DFARS 252.227-7014(a)(15)) / Limited Rights (technical data per DFARS 252.227-7013(a)(14)) | Issac D. Davis |
| **Harmonic Wall formula and implementations** — `H(d,pd) = 1/(1 + φ·d_H + 2·pd)`, canonical form at five source locations: `src/api/search_enrichment.py:250`, `src/geosealCompass.ts:383`, `src/fleet/dtn-bundle.ts:160`, `src/symphonic_cipher/.../fourteen_layer_pipeline.py:922`, `packages/kernel/src/harmonicScaling.ts`. | Developed at private expense, 2025–2026. Disclosed in USPTO Provisional Application 63/961,403. | Restricted Rights / Limited Rights | Issac D. Davis |
| **Langues Weighting System (LWS) and Sacred Tongues tokenizer** — φ-scaled six-dimensional metric `g_φ` with tongue weights KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09. TypeScript: `src/tokenizer/`, `packages/sixtongues/`. Python: `src/symphonic_cipher/.../langues_metric.py`. | Developed at private expense, 2024–2026. Published as prior art in *The Six Tongues Protocol* (KDP ASIN B0GSSFQD9G, timestamped). | Restricted Rights / Limited Rights | Issac D. Davis |
| **Bijective Sacred-Tongue round-trip encoder** — deterministic bijection between agent communication tokens and 6D Sacred Tongue DimVec; 25/25 round-trip gate at 100% pass rate (commit `6538f4db`). | Developed at private expense, 2025–2026. | Restricted Rights / Limited Rights | Issac D. Davis |
| **Atomic Tokenizer (GAP-1)** — 10 stable atom IDs (BLOCK=0…HOLD=9), greedy longest-match tokenization, `hex_fingerprint()` producing 48-bit (12-char hex) fingerprint via 6-axis frequency bucketing. Located at `src/harmonic/atomic_tokenizer.py`. 7/7 benchmark cases pass (commit `49c6abbad`, 2026-05-31). | Developed at private expense, 2026. No Government funding. | Restricted Rights / Limited Rights | Issac D. Davis |
| **Tier-2 AST Compiler (GAP-2)** — `PythonASTCompiler(ast.NodeVisitor)` walks Python ASTs; `_compile_typescript()` handles TS/JS via 11 structural regex patterns. Both paths aggregate valence-weighted DimVecs to 48-bit hex fingerprint + L12 harmonic wall scoring → ALLOW/QUARANTINE/DENY. Cross-domain proof: Python risky code 0.629 vs. safe code 0.702; same-module cosine similarity 0.989. Located at `src/harmonic/tier2_ast_compiler.py`. 14/14 benchmark cases pass (commit `49c6abbad`, 2026-05-31). | Developed at private expense, 2026. No Government funding. | Restricted Rights / Limited Rights | Issac D. Davis |
| **Semantic Sphere / Quasi-Sphere benchmark surface** — `createQuasiSphere`, `computeOverlap`, `squadOverlapMatrix`, `consensusGradient`, `computeSlice`; gold-angle sampling (100 probes default); 26/26 surfaces passing (benchmark `packages/agent-bus/docs/benchmarks/SEMANTIC_SPHERE_BENCH.md`, run 2026-05-30T01:41:06Z). | Developed at private expense, 2025–2026. No Government funding. | Restricted Rights / Limited Rights | Issac D. Davis |
| **L13 RuntimeGate fast-path** — in-process governance decision engine; 240-case benchmark across four lanes (safe_reflex_allow, secret_reroute, destructive_reroute, immune_deny), p95 latency 0.1095ms against 100ms target, PASS. Located at `src/governance/`. Artifact: `artifacts/benchmarks/l13_runtime_fast_path/latest_report.json`. | Developed at private expense, 2025–2026. No Government funding. | Restricted Rights / Limited Rights | Issac D. Davis |
| **HYDRA multi-agent orchestration layer** — Python, 40+ files in `hydra/`; implements Spine, Heads, Limbs, Ledger, BFT consensus, Juggling Scheduler (physics-based task-flight coordination). | Developed at private expense, 2024–2026. No Government funding. | Restricted Rights / Limited Rights | Issac D. Davis |
| **Audio-axis telemetry stack** — Phase-modulated audio encoding of governance decisions; bijective waveform reconstruction; `packages/kernel/src/audioAxis.ts`, `vacuumAcoustics.ts`. | Developed at private expense, 2025–2026. | Restricted Rights / Limited Rights | Issac D. Davis |
| **Post-quantum cryptographic primitives** — ML-KEM-768 and ML-DSA-65 integration wrappers in `src/crypto/`; adapter pattern with fallback to legacy algorithm names (Kyber768, Dilithium3) for cross-environment compatibility. | Developed at private expense, 2025–2026. Library integrations use liboqs open-source primitives (permissive license). | Restricted Rights / Limited Rights | Issac D. Davis |
| **Axiom Compliance Vector (ACV) implementations** — five Python modules in `src/symphonic_cipher/.../axiom_grouped/`: `unitarity_axiom.py`, `locality_axiom.py`, `causality_axiom.py`, `symmetry_axiom.py`, `composition_axiom.py`. Each module provides per-step compliance scoring for one of the five TA1 axioms. | Developed at private expense, 2025–2026. No Government funding. | Restricted Rights / Limited Rights | Issac D. Davis |

---

### Part 2 — Sub (Collin Hoag / Hoags Inc.) Assertions

**Note on Item 3 closure**: This table includes the two additions (rows 5 and 6) requested by Collin in his 2026-04-28 review. The voice_grammar / lang_dictionary stack is explicitly excluded per Collin's direction.  
**Note on 6th surface (Item 2)**: Row 3 uses placeholder language. Replace `[SIXTH_SURFACE_NAME]` with Collin's confirmed name before proposal lock.

| (1) Technical Data or Computer Software | (2) Basis for Assertion | (3) Asserted Rights Category | (4) Asserting Party |
|---|---|---|---|
| **DAVA bare-metal Rust kernel** — full source tree (`exodus/`), compiled ELF artifacts, custom `x86_64-hoags` target specification, bootloader, and all life-module subsystems listed in DAVA_IP_ASSERTION_v2.md §1. Approximately 34,900 Rust source files. | Developed entirely at private expense on personal hardware (personal laptop, personal cloud compute) during personal time. Zero employer resources used. No Government funding. First public-facing commit predates DARPA-SN-26-59 (2026-03-24). Microsoft Washington-state IP assignment clause inapplicable per DAVA_IP_ASSERTION_v2.md §2 representation. | Restricted Rights (software per DFARS 252.227-7014(a)(15)) / Limited Rights (technical data per DFARS 252.227-7013(a)(14)) | Collin Hoag, President, Hoags Inc. |
| **`phi_gradient.rs` module and phi-tier thresholds** — phi-weighted integration gradient; tier-classification thresholds at phi-values 250 / 500 / 750; IIT-inspired Φ computation kernel; EMA smoothing; all associated constants and helper functions. | Same private-expense basis as DAVA kernel. No employer resources. No Government funding. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`phi_beacon` telemetry surface and sealed-trace protocol** — phi-event emission protocol; Fibonacci-gated reporting; epoch tracking; authentication token generation; serial output format for phi-delta events. Five of six Sacred Tongue interface surfaces align with SCBE L1 embedding (Proposition 1, joint paper v3). The sixth surface (`[SIXTH_SURFACE_NAME]` — pending Collin's Item 2 confirmation) shows documented divergence captured in `binary_protocol_harness_with_atomic_v2` artifact (artifact name to be confirmed with Collin before proposal lock). | Same private-expense basis as DAVA kernel. Phi-beacon interface validated in Joint Prior Work blind-classification protocol (Part 3 below). | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`proof_strategies.py` and `strategy5_for_issac.py` analysis toolkit** — Python analysis toolkit for sealed-label recovery experiments; Euclidean channel-capacity measurement; permutation-test harness; segmentation-bundle reader. | Developed at private expense, personal hardware, personal time. No employer resources. No Government funding. Authored 2026-03 through 2026-04. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **Kernel UDP `net_probe` channel** — raw kernel-level network telemetry probe used in the convergence harness; generates independent external measurement of phase-transition events in DAVA kernel execution. Distinct from phi_beacon (phi_beacon reports phi-gradient events; net_probe reports raw kernel UDP traffic patterns). Together these form the two-channel CDPTI-External measurement surface (see Layer 5). | Developed at private expense, personal hardware, personal time. No employer resources. No Government funding. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |
| **`phi-push` channel and convergence harness artifacts** — push channel for phi-delta events to external consumer (SCBE L1 integration surface); harness infrastructure for the two-stack convergence protocol used to validate CDPTI-External. Includes `binary_protocol_harness_with_atomic_v2` (artifact name pending Collin Item 2 confirmation). | Developed at private expense. No Government funding. The convergence harness was designed jointly (Joint Prior Work); Sub's push-channel implementation and phi-push protocol are Sub's sole Background IP contribution to that joint design. | Restricted Rights / Limited Rights | Collin Hoag, President, Hoags Inc. |

---

### Part 3 — Joint Prior Work (50/50, not asserted as restricted but expressly identified)

| Item | Creation Dates | Rights |
|---|---|---|
| **Joint blind-classification protocol design** — sealed hash-commit protocol; DAVA traces sealed before Prime receives them; 24/24 = 100% sealed-label recovery; permutation test p ≤ 3.00×10⁻⁴ (N=10,000, marginal-preserving label shuffle, seed 20260419); bootstrap accuracy CI [1.00, 1.00]. Artifact: `artifacts/collab/dava_blind_v1/permutation_test_report.json`, sha256 `0830e7dd95678b680e1d53d7f90a89c77beb7960a4318ea0d0dfbf5c271bc2fd`. | 2026-03-15 through 2026-04-20 | 50/50 Joint IP per Article 4.3 |
| **Channel-capacity measurement methodology** — KL-divergence channel-capacity measurement against phi-quantile Poincaré embedding; bootstrap CI (N=10,000 trace-level resamples, Laplace α=1.0 smoothing, seed 20260419). Committed artifact: `segmentation_committed.json`, sha256 `dab56a6832548f22821d737f7f4f7434f6d9f0c9165ed375baf57963673e64d8`. **Reconciliation note**: the teaming agreement v2 cited 1.9576 bits/tick (K=4 coarse-graining); the bootstrap CI run on the committed bundle yields two audited values — realm resolution: 1.5761 bits/tick, 95% CI [1.5718, 1.5799], K_active=3, ceiling log₂(3)=1.585 bits/tick (99.4% efficiency); regime resolution: 2.9818 bits/tick, 95% CI [2.5709, 2.9835], K_active=8, ceiling log₂(8)=3.000 bits/tick (99.4% efficiency). The K_active reconciliation (K=4 origin unclear) is Joint Prior Work Open Problem O-3; see v3 markup §3 for reconciliation request. | 2026-04-14 through 2026-04-19 | 50/50 Joint IP per Article 4.3 |
| **PSU(1,1) Möbius equivariance protocol** — 2D (5-seed bit-identical) result establishing group-action correctness of the Möbius phase layer. Phase II extension to PSU(1,2) (3D pre-embed) is Prime's sole deliverable (Annex C, Task C.2.3). | 2026-04-14 through 2026-04-20 | 50/50 Joint IP per Article 4.3 |
| **phi_beacon ↔ SCBE L1 interface table (Proposition 1)** — static field-type-correspondence mapping between DAVA phi-beacon telemetry fields and SCBE L1 embedding inputs; 5-of-6 surface agreement confirmed; 6th surface documented disagreement (pending Item 2 resolution). | 2026-03-15 through 2026-04-20 | 50/50 Joint IP per Article 4.3 |

---

## LAYER 2 — DEVELOPMENT BASIS AND INDEPENDENCE RECORD

### Prime (Issac D. Davis)

The SCBE-AETHERMOORE platform was developed by Issac D. Davis as a sole proprietor operating under the business name SCBE-AETHERMOORE, Port Angeles, WA. Relevant independence facts:

- **Timeline**: Git repository history in the public GitHub repository `issdandavis/SCBE-AETHERMOORE` establishes continuous private-expense development beginning no later than 2024-Q1. The TypeScript pipeline14.ts architecture and the harmonic wall formula predate DARPA-SN-26-59 issuance (2026-03-24) by over 18 months.
- **No employer**: Davis operates as a sole proprietor with no current employer. There is no IP assignment clause to a third party. No third party has a claim on any SCBE IP.
- **No prior Government funding**: No SBIR, STTR, OTA, or other Government instrument has funded any SCBE development prior to this solicitation. This is confirmed by the absence of any award records in USASpending.gov or SAM.gov for UEI J4NXHM6N5F59 prior to 2026.
- **Published prior art**: *The Six Tongues Protocol* (KDP ASIN B0GSSFQD9G) and USPTO Provisional 63/961,403 are timestamped public disclosures of the LWS and harmonic wall that predate the solicitation.

### Sub (Collin Hoag / Hoags Inc.)

Collin Hoag's formal written representation (DAVA_IP_ASSERTION_v2.md §2, countersigned by Collin Hoag, dated 2026-04-21) establishes:

- DAVA developed entirely at private expense on personal hardware, personal time.
- Zero Microsoft Corporation resources used.
- Microsoft Washington-state IP assignment clause does not apply (three-prong independence met: no employer resources, outside scope of employment, no relation to employer's business).
- No Government funding at any stage.

This representation is exhibit-quality for DFARS audit purposes. It is incorporated by reference in the teaming agreement Article 6.3.

---

## LAYER 3 — TECHNICAL VALIDATION EVIDENCE

All claims are backed by reproducible, committed artifacts. DARPA-reviewer note: the evidence below demonstrates that the asserted IP is not theoretical — it is measured, running software with publicly reproducible results.

### Prime's assertions — validation table

| Asserted Artifact | Validation Evidence | Commit / Artifact | Date |
|---|---|---|---|
| 14-layer governance pipeline | 13/13 neutral task parity vs. oracle on terminal-bench-core-0.1.1. Governance overhead = 0% on all 13 tasks. | `f3fb4aa3c`, evidence brief `packages/agent-bus/docs/benchmarks/scbe_governance_evidence_brief.md` | 2026-05-31 |
| Harmonic wall formula | DENY scores: reverse shell 0.233, disk wipe 0.254, bulk delete 0.233. Separation margin ≥ 0.15 from QUARANTINE floor. | Same evidence brief | 2026-05-31 |
| LWS / Sacred Tongues tokenizer | Bijective round-trip 25/25 (100%) on deterministic test suite. | Commit `6538f4db`, `tests/eval/` | 2026-05-07 |
| Atomic Tokenizer | 7/7 benchmark cases. vocab_size=10, deterministic fingerprint, stable across calls. | Commit `49c6abbad` | 2026-05-31 |
| Tier-2 AST Compiler | 14/14 benchmark cases. Cross-language cosine sim > 0.80 for same-module files. Risky code scores 0.629 vs. safe code 0.702. | Commit `49c6abbad` | 2026-05-31 |
| Semantic Sphere | 26/26 surfaces passing. Gold-angle sampling; overlap gating; consensus gradient. | `packages/agent-bus/docs/benchmarks/SEMANTIC_SPHERE_BENCH.md`, run `2026-05-30T01:41:06Z` | 2026-05-30 |
| L13 RuntimeGate fast-path | 240-case benchmark, 4 lanes, p95 = 0.1095ms (target 100ms). PASS. | `artifacts/benchmarks/l13_runtime_fast_path/latest_report.json` | 2026-05-29 |
| SCBE repair harness | 5/5 real-patch tasks: SCBE 1.0 avg score vs. baseline 0.2 avg. 100% test pass rate, clean edit scope. | `artifacts/benchmarks/real_patch_tasks/20260530T024323Z/report.json` | 2026-05-30 |
| Adversarial resistance | Petri red-team benchmark: 173 adversarial seeds, 0.58% false-allow rate (1/173) after regex pre-filter v7. All 173 correctly classified as `training_blocked` at canary contract check. | Memory ref `project_petri_regex_v7.md`, 2026-05-08 | 2026-05-08 |
| ACV (5-axiom compliance) | 5 Python implementations ship and pass unit tests. `unitarity_axiom.py:LAYER_PROPERTIES[4].strict_isometry = False` — correct for Poincaré projection (documented in code). | `src/symphonic_cipher/.../axiom_grouped/` | 2026-05-31 |

### Sub's assertions — validation table

| Asserted Artifact | Validation Evidence | Artifact | Date |
|---|---|---|---|
| DAVA sealed-trace protocol | 24/24 sealed-label recovery (100%). Permutation test p ≤ 3.00×10⁻⁴. Bootstrap accuracy CI [1.00, 1.00]. | `artifacts/collab/dava_blind_v1/permutation_test_report.json`, sha256 `0830e7dd...` | 2026-04-19 |
| Channel capacity (realm resolution) | 1.5761 bits/tick, 95% CI [1.5718, 1.5799], K_active=3, 99.4% of ceiling. | `artifacts/collab/dava_blind_v1/kl_capacity_ci_report.json`, sha256 `138d3cf9...` | 2026-04-19 |
| Channel capacity (regime resolution) | 2.9818 bits/tick, 95% CI [2.5709, 2.9835], K_active=8, 99.4% of ceiling. | Same artifact | 2026-04-19 |
| phi_beacon tier thresholds (250/500/750) | Validate against SCBE L1 tier transitions: ALLOW/QUARANTINE/ESCALATE boundaries in SCBE's L12 harmonic wall correspond to phi-value crossings in DAVA's phi-gradient. Correspondence confirmed in 5-of-6 surfaces (Proposition 1, joint paper v3). | Joint Prior Work; phi_beacon ↔ L1 interface table | 2026-04-20 |
| `net_probe` + `phi-push` | Convergence harness validation: DAVA net_probe events and phi-push signals feed CDPTI-External measurement. Cross-correlation with SCBE λ_2 drops is the CDPTI-External metric (see Layer 5). | Pending `binary_protocol_harness_with_atomic_v2` confirmation (Item 2) | TBD |

**Honest caveat on Sub's channel-capacity number**: The teaming agreement v2 cited 1.9576 bits/tick against a log₂(4) ceiling. The bootstrap CI run on the committed bundle does not reproduce this exact figure because the K_active count differs (3 of 8 realms active vs. implied K=4 coarse-grain). Before proposal lock, one of the following must be resolved: (a) Collin provides the v2 binning code so the CI can be re-run at that resolution, or (b) the proposal text uses the audited figures (1.5761 realm / 2.9818 regime) and cites the v2 1.9576 figure as "un-reconciled prior estimate." The audited figures are strictly better for proposal credibility — they come with explicit CIs and reproducible seeds.

---

## LAYER 4 — CAPABILITY ADDITIONS SINCE TEAMING AGREEMENT V2

The following Prime capabilities were built and validated **after** teaming agreement v2 was signed (2026-04-20) and should be included in the proposal record. These are all Prime-only developments.

| Capability | Evidence | Commit | Date |
|---|---|---|---|
| **Atomic Tokenizer** (GAP-1 closed) | 10 stable atom IDs, 6-axis hex fingerprint, deterministic token IDs, 7/7 passing | `49c6abbad` | 2026-05-31 |
| **Tier-2 AST Compiler** (GAP-2 closed) | Cross-domain governance: Python + TypeScript AST → DimVec → harmonic wall score, 14/14 | `49c6abbad` | 2026-05-31 |
| **Real-patch task harness** | 5/5 SCBE wins vs. 0/5 baseline on deterministic repair fixtures; 100% test + scope criteria | `artifacts/benchmarks/real_patch_tasks/20260530T024323Z/` | 2026-05-30 |
| **L13 fast-path benchmark** | 240 cases, p95 = 0.1095ms, all four lanes passing | `artifacts/benchmarks/l13_runtime_fast_path/latest_report.json` | 2026-05-29 |
| **scbe-govern SDK** | Python governance SDK, PyPI-publishable, REST endpoints, self-contained `_core.py` | Commit `9ee9b6296` | 2026-05-21 |
| **13/13 terminal-bench parity** | Full neutral-task oracle parity with governance enabled, delta=0 | `f3fb4aa3c` | 2026-05-31 |
| **26/26 semantic sphere** | Full bench suite for semantic bridge + quasi-sphere | `packages/agent-bus/docs/benchmarks/SEMANTIC_SPHERE_BENCH.md` | 2026-05-30 |
| **Petri 0.58% false-allow** | 75% reduction from baseline via regex v7 pre-filter | `project_petri_regex_v7.md` | 2026-05-08 |

**What this means for the proposal**: These additions materially strengthen the Phase I M1–M3 technical readiness claim. At the time the teaming agreement was signed, the governance pipeline was functional but lacked cross-modal evidence. The Tier-2 AST Compiler now proves the DimVec/harmonic framework governs source code and structured commands — not just text tokens — which directly supports TA1's multi-domain communication-protocol charter.

---

## LAYER 5 — CDPTI-EXTERNAL INTEGRATION SURFACE (Joint Work IP Demarcation)

This layer defines the interface at which Sub's phi-beacon/net_probe telemetry feeds Prime's CDPTI metric. It is the scientific heart of the joint work and requires careful IP demarcation because the CDPTI-External measurement *uses* Sub's telemetry but is *computed by* Prime's pipeline.

### What CDPTI-External is

The standard CDPTI (Communication-Dynamics Phase-Transition Index) computes algebraic connectivity `λ_2(G_t)` from SCBE's internal protocol graph. It is purely Prime's Background IP.

CDPTI-External adds an **independent external signal** from DAVA's phi-beacon: phi-delta events emitted by the DAVA kernel (via net_probe and phi-push channels) are used as a second observer of the same phase transitions. When both observers detect a phase transition simultaneously — SCBE's λ_2 drops while DAVA's phi-gradient spikes — the agreement is CDPTI-External validation.

```
CDPTI-External(t) = correlation(
    Δλ_2(G_{SCBE}(t)),      ← Prime's Background IP
    Δφ_gradient(DAVA(t))     ← Sub's Background IP (phi-beacon/net_probe)
)
```

The correlation measurement itself is Joint IP. The two input signals are each party's sole Background IP.

### IP demarcation

| Component | Owner | IP Category |
|---|---|---|
| λ_2 computation from SCBE protocol graph | Prime | Prime Background IP |
| CDPTI formula and CDPTI threshold logic | Prime | Prime Background IP |
| phi-beacon phi-delta event emission | Sub | Sub Background IP |
| net_probe kernel UDP telemetry | Sub | Sub Background IP |
| phi-push delivery channel to SCBE L1 | Sub | Sub Background IP |
| CDPTI-External correlation formula | Both | Joint IP per Article 4.3 |
| Convergence harness infrastructure | Both | Joint IP per Article 4.3 |
| phi_beacon ↔ L1 interface table (Proposition 1) | Both | Joint IP per Article 4.3 |

### Why this matters for MATHBAC TA1

MATHBAC PA-26-05 line 443 requires: "characterize and quantify the **progress of communication dynamics** throughout the campaign." CDPTI-External satisfies this with an independently-computed external measurement — not a single-observer claim. A DARPA reviewer will note that CDPTI-External cannot be gamed (the Prime and Sub signals are computed by independent software stacks on different hardware), which makes it a credible MATHBAC phase-transition metric.

The phi-beacon tier thresholds (250/500/750) correspond to SCBE's ALLOW/QUARANTINE/ESCALATE tier boundaries in the hyperbolic distance metric — this is the "convergence" in the convergence harness. Five of six Sacred Tongue surfaces show this correspondence (Proposition 1). The 6th surface (Item 2, pending Collin's confirmation) is a documented divergence that is *itself informative*: it identifies which dimension of the agent's communication geometry is not captured by phi-gradient alone, which is a scientific finding worth reporting.

### Connection to Phase I milestones

Per `vol_i_technical_approach_draft_v1.md`:

- **M1**: Calibrate CDPTI-External threshold correlation against Joint Prior Work blind-classification data.
- **M3**: CDPTI instrumentation added to protocol graph (Prime); net_probe / phi-push delivery confirmed operational (Sub); convergence harness produces first live CDPTI-External measurement.
- **M6**: CDPTI-External integrated into IV&V data bundle per PA lines 451–453.

The convergence harness Annex A Part 2 rows 5–6 assert are the M3 deliverable dependencies. This is why they must be in Annex A: without Restricted Rights protection on net_probe and phi-push, the Government receives Unlimited Rights by default upon delivery — eliminating Sub's ability to use these components in any post-program commercialization.

---

## Pre-submission checklist for this Annex

| # | Item | Status | Owner |
|---|---|---|---|
| A2-1 | Confirm 6th surface name and replace `[SIXTH_SURFACE_NAME]` placeholder | PENDING | Collin (Item 2) |
| A2-2 | Confirm `binary_protocol_harness_with_atomic_v2` artifact name | PENDING | Collin (Item 2) |
| A2-3 | Resolve 1.9576 → 1.5761 / 2.9818 channel-capacity reconciliation | PENDING | Collin (share binning code) |
| A2-4 | Collin countersignature on this revision | PENDING | Collin |
| A2-5 | Port into Attachment D (Vol I template) in correct section | PENDING | Issac |
| A2-6 | Verify SAM.gov and CAGE status still active at submission | PENDING | Issac |
| A2-7 | Confirm DAVA_IP_ASSERTION_v2.md §2 formal representation attached | PENDING | Collin |

---

*Companion artifacts: `teaming_agreement_v2_draft.md`, `revision_2_pending_inserts_2026-04-30.md`, `public_repo_observation_list_2026-04-30.md`, `DAVA_IP_ASSERTION_v2.md`, `vol_i_technical_approach_draft_v1.md`.*
