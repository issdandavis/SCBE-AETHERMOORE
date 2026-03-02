# Patent Readiness Master Plan (2026 Q1)

Status: In Progress  
Scope: SCBE-AETHERMOORE machine-science filing prep

## Objective

Consolidate claim architecture, prior-art differentiation, evidence mapping, and filing tasks into a single execution surface that can be handed to counsel with reproducible technical proof.

## Canonical Inputs

- `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`
- `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`
- `docs/specs/patent/MACHINE_SCIENCE_PATENT_SAFE_ABSTRACT.md`
- `docs/specs/patent/RESEARCH_PATENT_ANALYSIS.md`

## New Patent Packet Assets

- `docs/specs/patent/PATENT_CLAIMS_TREE_MACHINE_SCIENCE.md`
- `docs/specs/patent/PATENT_FIGURE_MAP_MACHINE_SCIENCE.md`
- `docs/specs/patent/PATENT_PRIOR_ART_DELTA_MACHINE_SCIENCE.md`
- `docs/specs/patent/PATENT_PROSECUTION_EVIDENCE_MATRIX.md`
- `docs/specs/patent/PATENT_FILING_CHECKLIST_2026Q1.md`

## Readiness Snapshot

Current state by evidence class:

- Spec: Strong
- Code: Partial
- Test: Partial
- Artifact Pack: Partial

Counsel-ready requires:

1. Claim chart generated from the claims tree and evidence matrix.
2. Determinism replay artifacts for fixed input/constant runs.
3. Runtime quorum-enforcement proof for critical/destructive action classes.
4. Replacement of placeholder tongue-signing path in `src/gateway/unified-api.ts`.
5. Independent audit-chain verifier output.

## Priority Gaps (Execution Order)

1. `GAP-01` Placeholder signing path in `src/gateway/unified-api.ts`.
2. `GAP-02` Missing dedicated fail-closed/trust-state transition tests for `src/governance/offline_mode.ts`.
3. `GAP-03` Partial runtime proof for quorum-gated destructive action flow.
4. `GAP-04` Missing deterministic replay + fault-injection evidence folders for prosecution appendix.

## 7-Day Execution Plan

Day 1-2:

- Complete `MS-07` signer implementation and tests.
- Add decision semantic alignment test (`ALLOW/QUARANTINE/ESCALATE/DEFER/DENY`).

Day 3-4:

- Build deterministic replay harness and store outputs in:
  - `artifacts/evidence/patent_2026q1/determinism_replay/`
- Run fault-injection scenarios and store outputs in:
  - `artifacts/evidence/patent_2026q1/fault_injection/`

Day 5:

- Build quorum enforcement evidence set in:
  - `artifacts/evidence/patent_2026q1/quorum_enforcement/`

Day 6:

- Build independent audit-chain verifier artifacts:
  - `artifacts/evidence/patent_2026q1/audit_chain_verify/`

Day 7:

- Assemble counsel handoff folder:
  - `docs/specs/patent/filing_packet_2026q1/`

## Done Criteria

- Every matrix element in `PATENT_PROSECUTION_EVIDENCE_MATRIX.md` has explicit status.
- High-priority prior-art rows have linked proof artifacts.
- `FR-001` through `FR-052` in `PATENT_FILING_CHECKLIST_2026Q1.md` are either complete or assigned with owner/date.
- Handoff packet contains appendix index and reproducibility runbook.

## Non-Physics Framing Guardrail

Use this language consistently in technical and claim drafts:

- "logical control hyperspace"
- "machine constants"
- "policy-field evaluation"
- "deterministic governance pipeline"

Do not present the system as a simulation of physical laws.
