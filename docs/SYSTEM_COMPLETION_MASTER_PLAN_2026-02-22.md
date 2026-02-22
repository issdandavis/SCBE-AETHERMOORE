# System Completion Master Plan — 2026-02-22

## North Star
Deliver a production SCBE platform with clean separation of:
- `system` (math/runtime core)
- `governance` (policy, trust, risk decisions)
- `functions` (connectors, tools, workflows)

Each layer must be testable and deployable independently.

## Current Position
- Strong velocity: Docker and MCP terminal operations are live.
- Training pipeline now supports track splitting + legacy quotas.
- Connector reality:
  - GitHub: stable
  - Drive: stable
  - Notion: stable via Zapier/Codex, direct API token needs repair

## Workstreams

### A) Platform Partitioning (System/Governance/Functions)
Deliverables:
1. Define strict interfaces between partitions (`input schema`, `output schema`, `error schema`).
2. Move cross-cutting logic into shared contracts package.
3. Enforce boundaries in CI (no direct imports across forbidden layers).
Exit criteria:
- All core flows run with partition contract tests passing.

### B) Reliability and CI
Deliverables:
1. Stabilize failing workflow(s), especially weekly security audit jobs.
2. Add generated-artifact guardrails to avoid noisy commits.
3. Add nightly connector health workflow.
Exit criteria:
- Main branch green for required pipelines.

### C) Data and Training Discipline
Deliverables:
1. Keep `sft_system`, `sft_governance`, `sft_functions` as canonical train artifacts.
2. Add schema validation for `track`, `source_type`, `quality` in CI.
3. Keep legacy ratio capped (default 15% or lower).
Exit criteria:
- Dataset build reproducible and policy-compliant nightly.

### D) Code Prism (Polyglot Builder)
Yes, this is feasible, but **"no errors"** requires phased constraints.

Phase 1 (safe subset):
- Build language-neutral IR from your interoperability matrix.
- Start with 3 targets (Python/TypeScript/Go).
- Round-trip tests: source -> IR -> target -> tests.

Phase 2 (semantic hardening):
- Add static type/effect contracts to IR.
- Add conlang semantic tags to IR nodes (KO/AV/RU/CA/UM/DR channels).
- Gate output by governance checks before emission.

Phase 3 (scale):
- Expand to additional languages.
- Add agentic repair loop for compile/test failures.
- Publish Code Prism API + UI builder.

Exit criteria:
- >=95% transpilation pass rate on supported subset with deterministic test parity.

## 30 / 60 / 90 Day Targets
- 30 days: partition contracts + connector health + CI stabilization.
- 60 days: Code Prism phase 1 shipping in CLI/API form.
- 90 days: Code Prism phase 2 with governance-tagged IR and automated repair loop.

## Immediate Next Actions
1. Fix direct Notion MCP token.
2. Merge scoped branch changes into `main` through PR #247.
3. Start Code Prism spec doc from existing interoperability matrix and lock phase-1 language subset.
