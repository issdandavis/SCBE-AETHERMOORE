# System Overview (from Mind Map)

This document translates the SCBE-AETHERMOORE mind map into concrete repository surfaces and execution paths.

## 1) Core Security Pipeline

- **14-layer decision flow** is the conceptual center of the platform and is described at a high level in the top-level README and architecture docs.
- The canonical Python reference implementation lives in `src/scbe_14layer_reference.py`.
- Decision outputs align to **ALLOW / QUARANTINE / DENY** thresholds in docs.

Primary references:
- `README.md`
- `docs/01-architecture/README.md`
- `src/scbe_14layer_reference.py`

## 2) Cryptography Domain

Mind-map branch: *Cryptography* → *RWP v3 envelope*, *Sacred Tongues tokenizer*, *PQC modules ML-KEM / ML-DSA*.

Code mapping:
- `src/crypto/rwp_v3.py` → RWP v3 envelope handling (`encrypt`, `decrypt`).
- `src/crypto/sacred_tongues.py` → tokenizer and language security constructs.
- `src/pqc/*` + TS/Python integration surfaces → post-quantum primitives used across modules.

Test mapping:
- `tests/test_enterprise_compliance.py`
- `tests/crypto/test_rwp_v3.py`

## 3) Platform & API Surfaces

Mind-map branch: *Platform and APIs* → *Python API surfaces*, *TypeScript SDK modules*, *Gateway and cloud integration*.

Code mapping:
- Python orchestration/security APIs: `src/ai_orchestration/*.py`.
- TypeScript SDK/runtime surfaces: `src/spiralverse/*.ts`, `src/agentic/*.ts`, `src/fleet/*.ts`.
- Deployment/integration assets: `aws/*`, `deploy/*`, `render.yaml`, `Dockerfile.api`.

## 4) Testing System

Mind-map branch: *Testing System* → *pytest and strict markers*, *TS tests via Vitest*, *L1 to L6 test tiers*, *enterprise property/security suites*.

Code mapping:
- Python test configuration and markers: `pytest.ini`.
- Enterprise suite: `tests/test_enterprise_compliance.py`.
- TS test runner config: `vitest.config.ts` and `src/vitest.config.ts`.

Operational note:
- Runtime-dependent crypto tests should gate on actual runtime availability (not just importability), so CI/local environments produce deterministic pass/skip behavior.

## 5) Deployment, Ops, and Compliance

Mind-map branch: *Deployment and Ops* → *Docker/Cloud Run/Lambda assets*, *compliance dashboards/reports*, *system status and architecture docs*.

Code/docs mapping:
- Deployment assets: `Dockerfile.api`, `aws/template.yaml`, `deploy/multi_cloud_deploy.sh`.
- Operational docs and audits: `docs/test-audit-report-2026-01-20.md`, `TEST_AUDIT_REPORT.md`, `SYSTEM_IMPROVEMENT_RECOMMENDATIONS.md`.

## 6) Governance & Agentic Control

Mind-map branch: *Governance and Agentic* → *AI safety verifier modules*, *fleet workflows*, *consensus and trust scoring*.

Code mapping:
- Agent orchestration and governance: `src/agentic/*.ts`, `src/fleet/*.ts`, `src/ai_orchestration/*.py`.
- Trust/risk and harmonic modules: `src/harmonic/*`, `src/spiralverse/policy.ts`.

---

## Recommended Next Steps (Actionable)

1. **Architecture index hardening**
   - Keep this mind-map translation linked from `docs/01-architecture/README.md` and update it when new major modules are added.

2. **Runtime dependency gates in tests**
   - Standardize the `*_RUNTIME_AVAILABLE` test pattern for modules with optional crypto/native dependencies.

3. **Cross-language parity checks**
   - Add a small CI job verifying critical API parity between Python and TypeScript surfaces (e.g., envelope shape, decision schema).

4. **Decision-path observability**
   - Ensure each layer emits structured telemetry so ALLOW/QUARANTINE/DENY can be traced to exact layer contributions.

5. **Single source of truth for architecture docs**
   - Consolidate older archive architecture docs into one maintained canonical overview to reduce drift.
