# Patent Prosecution Evidence Matrix: Machine-Science

## Operating Guardrails
- This matrix maps technical claim elements to engineering proof artifacts.
- It does not determine patentability or legal scope.
- Goal is to reduce prosecution risk by closing proof gaps before filing.

## Matrix

| Element ID | Claim element (operations wording) | Proof artifact path(s) | Current proof level | Test / prototype needed to close gap | Owner |
|---|---|---|---|---|---|
| MS-01 | Tokenized control hyperspace with explicit base axes (`t,i,p,u,r,c`) | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md` | Spec | Add executable axis-state schema validation test: `tests/governance/test_axis_schema_contract.py` | `[OWNER: ______]` |
| MS-02 | Versioned machine constants as deterministic invariants (`k_tick`, `k_decay`, `k_gate`, `k_route`, `k_crypto`, `k_stability`) | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `src/governance/immutable_laws.ts` | Spec + Code | Add replay determinism tests over fixed constants: `tests/governance/test_offline_mode_determinism.ts` | `[OWNER: ______]` |
| MS-03 | Policy-field composition and threshold mapping to governance outcomes | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `src/governance/mmx.ts`; `src/governance/offline_mode.ts` | Spec + Code | Add threshold-boundary tests at decision edges (`allow/escalate/deny` boundaries) | `[OWNER: ______]` |
| MS-04 | Governance result set controlling execution pathways (`ALLOW`, `QUARANTINE`, `ESCALATE/DEFER`, `DENY`) | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `src/api/govern.ts`; `src/governance/offline_mode.ts`; `aetherbrowse/runtime/perceiver.py` | Spec + Code | Add cross-module enum/semantic alignment test to prevent drift | `[OWNER: ______]` |
| MS-05 | Fail-closed token lifecycle with context commitment and signature requirements | `docs/specs/MACHINE_SCIENCE_CONTROL_FRAMEWORK_RFC_0001.md`; `src/governance/packet.py`; `src/governance/offline_mode.ts` | Spec + Code | Add malformed-token and missing-metadata negative tests with expected fail-closed outcomes | `[OWNER: ______]` |
| MS-06 | Deterministic decision envelope canonicalization, signing, and MMR leaf hashing | `docs/specs/DECISION_ENVELOPE_V1.md`; `src/governance/decision_envelope_v1.py`; `tests/test_decision_envelope_v1.py`; `proto/decision_envelope/v1/decision_envelope.proto` | Spec + Code + Test | Add corpus/fuzz test for canonicalization invariance and invalid projection rejection | `[OWNER: ______]` |
| MS-07 | Multi-tongue envelope signatures for protocol-level authorization checks | `src/gateway/unified-api.ts`; `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md` | Spec + Code (placeholder signing) | Replace placeholder signer in `signWithTongue(...)` with key-backed implementation and add verification tests | `[OWNER: ______]` |
| MS-08 | Quorum-gated critical/destructive actions with recovery metadata | `docs/specs/MACHINE_SCIENCE_TAXONOMY_MAP.md`; `src/governance/decision_envelope_v1.py`; `tests/L2-unit/governanceSim.unit.test.ts` | Spec + Code + Test (partial runtime binding) | Add runtime integration test: destructive action denied without quorum, allowed with quorum | `[OWNER: ______]` |
| MS-09 | Signed decision capsule and append-only audit chain (`prev_hash -> event_hash`) | `src/governance/offline_mode.ts`; `src/governance/audit_ledger.ts`; `policies/base/audit.yaml` | Code + Policy config | Add independent verifier CLI/script and tamper mutation test report | `[OWNER: ______]` |
| MS-10 | Manifest verification + staleness/rollover trust-state transitions impacting decisions | `src/governance/offline_mode.ts`; `src/governance/flux_manifest.ts`; `policies/releases/manifest.json` | Code | Add scenario tests for stale manifest, bad signature, and rollover-required outcomes | `[OWNER: ______]` |
| MS-11 | Resource-aware wall-cost behavior as governance input under scarcity | `src/governance/decision_envelope_v1.py`; `tests/test_decision_envelope_v1.py`; `artifacts/ip/harmonic_wall_figure1.{json,csv,svg,md}` | Code + Test + Artifact | Add benchmark script to regenerate wall-cost figure deterministically with seed/config capture | `[OWNER: ______]` |
| MS-12 | Multi-head consensus governance behavior over real automation traces | `aetherbrowse/runtime/perceiver.py`; `artifacts/aetherbrowse_runs/20260217T051547Z/decision_records/`; `artifacts/evidence_packs/20260217T103648Z/scorecard.json` | Code + Run artifacts | Add replay script that re-scores stored traces and checks decision stability | `[OWNER: ______]` |

## Minimum Evidence-Closure Definition
- Spec evidence: canonical element is described in RFC/spec text.
- Code evidence: executable implementation exists in tracked source.
- Test evidence: deterministic pass/fail test asserts behavior.
- Artifact evidence: timestamped run outputs are stored under `artifacts/evidence/` or `artifacts/evidence_packs/`.

## Suggested Evidence Output Layout
- `artifacts/evidence/patent_2026q1/ms-01/` ... `ms-12/`
- Each folder should include:
  - `README.md` (scenario + expected behavior)
  - `run.log` (command output)
  - `result.json` (machine-readable pass/fail + metrics)
  - `sha256.txt` (hashes of generated artifacts)
