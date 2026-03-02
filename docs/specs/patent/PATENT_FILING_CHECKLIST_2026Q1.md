# Patent Filing Checklist 2026 Q1: Machine-Science Readiness Pack

## Operating Guardrails
- This checklist is for technical filing readiness only.
- Legal conclusions, claim validity decisions, and filing strategy stay with counsel.
- Every completed item should produce a repo artifact (log, report, hash, or test output).

## A. Scope Lock and Baseline Capture
- [ ] `FR-001` Freeze source references used in packet and record commit SHA in `artifacts/evidence/patent_2026q1/repo_snapshot.json`. `[OWNER: ______]`
- [ ] `FR-002` Capture SHA-256 manifest for all cited artifacts/specs into `artifacts/evidence/patent_2026q1/source_hash_manifest.txt`. `[OWNER: ______]`
- [ ] `FR-003` Confirm source set includes:
  - `docs/specs/patent/RESEARCH_PATENT_ANALYSIS.md`
  - `docs/specs/patent/MACHINE_SCIENCE_PATENT_SAFE_ABSTRACT.md`
  - `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`
  - `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`
  `[OWNER: ______]`

## B. Prior-Art Delta and Claim Element Mapping
- [ ] `FR-010` Complete overlap/differentiator/evidence-needed rows in `docs/specs/patent/PATENT_PRIOR_ART_DELTA_MACHINE_SCIENCE.md`. `[OWNER: ______]`
- [ ] `FR-011` Complete all rows in `docs/specs/patent/PATENT_PROSECUTION_EVIDENCE_MATRIX.md` with status (`Spec`, `Code`, `Test`, `Artifact`). `[OWNER: ______]`
- [ ] `FR-012` Build claim-chart export for counsel at `artifacts/evidence/patent_2026q1/claim_chart_machine_science.md`. `[OWNER: ______]`

## C. Code/Test Evidence Hardening
- [ ] `FR-020` Run envelope determinism and boundary tests:
  - `tests/test_decision_envelope_v1.py`
  Save outputs under `artifacts/evidence/patent_2026q1/test_runs/decision_envelope/`. `[OWNER: ______]`
- [ ] `FR-021` Run governance simulation unit tests:
  - `tests/L2-unit/governanceSim.unit.test.ts`
  Save outputs under `artifacts/evidence/patent_2026q1/test_runs/governance_sim/`. `[OWNER: ______]`
- [ ] `FR-022` Run governance adapter trajectory tests:
  - `tests/test_governance_adapter.py`
  Save outputs under `artifacts/evidence/patent_2026q1/test_runs/governance_adapter/`. `[OWNER: ______]`
- [ ] `FR-023` Add and run missing tests for `src/governance/offline_mode.ts` fail-closed and trust-state transitions; store under `artifacts/evidence/patent_2026q1/test_runs/offline_mode/`. `[OWNER: ______]`
- [ ] `FR-024` Add cross-module decision semantic alignment test (`ALLOW/QUARANTINE/ESCALATE/DEFER/DENY`) and store results under `artifacts/evidence/patent_2026q1/test_runs/decision_alignment/`. `[OWNER: ______]`

## D. Prototype Evidence Build-Out
- [ ] `FR-030` Build deterministic replay prototype using fixed inputs/constants and capture reproducibility report in `artifacts/evidence/patent_2026q1/determinism_replay/`. `[OWNER: ______]`
- [ ] `FR-031` Build fault-injection prototype for manifest stale, key rollover required, and integrity degraded states; store outputs in `artifacts/evidence/patent_2026q1/fault_injection/`. `[OWNER: ______]`
- [ ] `FR-032` Build quorum-enforcement prototype for destructive actions with/without quorum evidence in `artifacts/evidence/patent_2026q1/quorum_enforcement/`. `[OWNER: ______]`
- [ ] `FR-033` Replace placeholder tongue-signature flow in `src/gateway/unified-api.ts` and capture compatibility tests in `artifacts/evidence/patent_2026q1/tongue_signatures/`. `[OWNER: ______]`
- [ ] `FR-034` Build independent audit-chain verification run for signed event chains and store report in `artifacts/evidence/patent_2026q1/audit_chain_verify/`. `[OWNER: ______]`

## E. Artifact and Figure Assembly
- [ ] `FR-040` Regenerate and freeze harmonic wall artifacts:
  - `artifacts/ip/harmonic_wall_figure1.json`
  - `artifacts/ip/harmonic_wall_figure1.csv`
  - `artifacts/ip/harmonic_wall_figure1.svg`
  - `artifacts/ip/harmonic_wall_figure1.md`
  Add generation log + hashes in `artifacts/evidence/patent_2026q1/figures/`. `[OWNER: ______]`
- [ ] `FR-041` Curate representative runtime evidence from:
  - `artifacts/aetherbrowse_runs/20260217T051547Z/decision_records/`
  - `artifacts/evidence_packs/20260217T103648Z/`
  Export curated subset to `artifacts/evidence/patent_2026q1/runtime_samples/`. `[OWNER: ______]`
- [ ] `FR-042` Build a single prosecution appendix index at `artifacts/evidence/patent_2026q1/APPENDIX_INDEX.md` linking every artifact to matrix element IDs (`MS-01...`). `[OWNER: ______]`

## F. Counsel Handoff Packet
- [ ] `FR-050` Assemble handoff folder `docs/specs/patent/filing_packet_2026q1/` with:
  - prior-art delta
  - prosecution evidence matrix
  - checklist status export
  - claim chart
  - artifact appendix index
  `[OWNER: ______]`
- [ ] `FR-051` Add open-risk register for unresolved technical gaps in `docs/specs/patent/filing_packet_2026q1/OPEN_RISKS.md`. `[OWNER: ______]`
- [ ] `FR-052` Add reproducibility instructions in `docs/specs/patent/filing_packet_2026q1/REPRO_RUNBOOK.md`. `[OWNER: ______]`

## G. Exit Criteria (Ready for Counsel Review)
- [ ] All matrix elements (`MS-01` to `MS-12`) have at least `Spec + Code + Test` evidence.
- [ ] High-priority delta rows have artifact-backed differentiator proof.
- [ ] All artifact folders include `README.md`, `run.log`, `result.json`, and `sha256.txt`.
- [ ] Packet passes internal engineering sign-off with named owners and dates.
