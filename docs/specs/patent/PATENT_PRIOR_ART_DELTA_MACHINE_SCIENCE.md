# Patent Prior-Art Delta: Machine-Science (Readiness Ops)

## Operating Guardrails
- This document is an engineering readiness artifact, not a legal opinion.
- Use it to prepare evidence, prototypes, and claim charts for counsel review.
- Focus is on overlap risk reduction and proof coverage expansion.

## Source Baseline
- `docs/specs/patent/RESEARCH_PATENT_ANALYSIS.md`
- `docs/specs/patent/MACHINE_SCIENCE_PATENT_SAFE_ABSTRACT.md`
- `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`
- `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`

## Prior-Art Delta Table

| Prior-art anchor | Likely overlap area | SCBE differentiator to prove | Current repo-grounded evidence | Evidence still needed before filing packet | Ops priority |
|---|---|---|---|---|---|
| US 7,856,294 (autonomous spacecraft ops, single command language) | Autonomous mission control loops, command gating, scheduling | Multi-axis control hyperspace (`t,i,p,u,r,c`) + policy-field composition + deterministic token governance (not single-command orchestration) | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`; `src/governance/offline_mode.ts` | Determinism replay harness across repeated runs and constant sets; attach run logs under `artifacts/evidence/patent_2026q1/` | High |
| US 11,465,782 (autonomous deorbiting) | Autonomous AI decisioning under constrained resources | General-purpose governance envelope for `A_read/A_write/A_execute/A_destructive`, not a single deorbit workflow | `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`; `src/governance/decision_envelope_v1.py`; `tests/test_decision_envelope_v1.py` | Scenario suite showing at least 3 non-deorbit domains (browse, data write, destructive action) with reproducible decisions | High |
| US 12,452,957 B2 (heterogeneous sensor closed-loop tasking) | Closed-loop autonomy, distributed coordination, compact telemetry | Protocol-layer governance with context commitment, policy fields, and cryptographic envelope checks (not sensor-fusion tasking alone) | `docs/specs/patent/MACHINE_SCIENCE_PATENT_SAFE_ABSTRACT.md`; `src/governance/offline_mode.ts`; `src/gateway/unified-api.ts` | Comparative prototype where same sensor payload yields different governance outcomes by context/policy vector | High |
| 2025 self-healing MADA architectures | Monitor/Analyze/Decide/Act control loops, self-healing claims | Six-tongue policy weighting + trust-state machine + fail-closed gate + signed decision capsules | `docs/specs/patent/RESEARCH_PATENT_ANALYSIS.md`; `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`; `src/governance/offline_mode.ts` | Fault-injection campaign (manifest stale, key rollover, integrity degraded) with captured transition evidence | High |
| Generic ABAC/RBAC governance engines | Policy-based allow/deny decisions | Machine constants as versioned invariants with deterministic replay and explicit threshold families (`k_gate`, `k_decay`, etc.) | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `src/governance/immutable_laws.ts`; `src/governance/mmx.ts` | Cross-runtime reproducibility test (same packet + constants => same decision/proof hash) | Medium |
| BFT / quorum consensus prior art | Multi-agent voting and consensus thresholds | Role-diverse quorum integrated with policy fields and action classes, tied to recovery metadata | `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`; `tests/L2-unit/governanceSim.unit.test.ts`; `src/governance/decision_envelope_v1.py` | Runtime enforcement proof that quorum requirements are checked before destructive/sensitive execution | High |
| Standard secure envelopes (HMAC/AEAD/nonces) | Signed payloads, nonce replay controls, timestamp checks | Context-locked governance envelopes where invalid context produces non-actionable execution pathways | `src/gateway/unified-api.ts`; `src/crypto/envelope.ts`; `docs/specs/DECISION_ENVELOPE_V1.md` | Replace placeholder tongue signing with key-managed implementation + replay-window tests + tamper tests | Medium |
| Merkle/hash-chain audit systems | Tamper-evident logs and chain verification | Decision capsule binds `inputs_hash`, `laws_hash`, `manifest_hash`, and `state_root` to governance decision | `src/governance/offline_mode.ts`; `policies/base/audit.yaml`; `artifacts/evidence_packs/20260217T103648Z/` | Independent verifier script and red-team tamper test report with pass/fail evidence | Medium |

## Immediate Evidence Backlog (30-Day)
- [ ] Build `artifacts/evidence/patent_2026q1/determinism_replay/` with repeated decision runs and hash comparison reports. `[OWNER: ______]`
- [ ] Build `artifacts/evidence/patent_2026q1/fault_injection/` for stale manifest, integrity degradation, and key-rollover cases. `[OWNER: ______]`
- [ ] Build `artifacts/evidence/patent_2026q1/quorum_enforcement/` proving runtime quorum gates for critical/destructive actions. `[OWNER: ______]`
- [ ] Build `artifacts/evidence/patent_2026q1/crypto_envelope/` with nonce replay and signature tamper tests. `[OWNER: ______]`
- [ ] Build `artifacts/evidence/patent_2026q1/independent_audit_verify/` for hash-chain integrity verification outside runtime. `[OWNER: ______]`
