---
name: scbe-kernel-external-toolcall-specialist
description: Kernel engineering and external tool-call orchestration for SCBE-AETHERMOORE. Use when implementing or reviewing SCBE runtime paths that call external systems (Hugging Face, Notion, GitHub, Linear, Zapier, browser automation, MCP connectors), when mapping domain-specific turnstile actions, when enforcing StateVector and DecisionRecord outputs, or when generating deterministic chain scripts/YAML for multi-agent workflows.
---

# SCBE Kernel External Tool-Call Specialist

## Operating Contract

1. Preserve canonical SCBE terms and spelling.
2. Preserve canonical wall formula as defined in `references/scbe-canonical-formulas.md` unless explicitly overridden.
3. Treat all proposed formulas as untrusted until dimensional analysis and behavior checks pass.
4. Prefer concrete artifacts: scripts, tests, chain YAML, patch files.
5. Emit dual output for governed actions:
   - `StateVector`
   - `DecisionRecord`
6. Keep GeoSeal scope discipline; avoid unrelated side effects.
7. For external systems, discover callable tools first and report the discovery contract:
   - `service`
   - `callable_now`
   - `needs_configuration`
   - `missing_env`
   - `scopes`
   - `rate_limits`

## Workflow

1. Identify scope:
   - SCBE layer(s)
   - formula(s)
   - external systems/connectors in play
2. Validate math and behavior before routing:
   - unit compatibility
   - boundedness
   - graph-size sensitivity where spectral/determinant terms exist
3. Produce deterministic artifacts:
   - route YAML with `tool`, `llm`, `gate` typed steps
   - machine-checkable schemas in `schemas/`
   - executable scripts for repeated paths
   - targeted tests for path correctness
4. Enforce domain turnstile mapping (see `references/toolcall-playbook.md`):
   - `browser`: may `HOLD`
   - `vehicle`: must `PIVOT` (no stall)
   - `fleet`: `ISOLATE` node, continue swarm
   - `antivirus`: `ISOLATE` or `HONEYPOT` as final containment
   - `arxiv`: `HOLD` for human review before final submit
   - `patent`: `HOLD` for attorney review before filing
5. End substantial tasks with tri-fold `action_summary` (use template in `assets/`).

## External Tool-Call Rules

1. Discover external callable tools first.
2. Never claim connector capability that is not currently callable.
3. Route failures as structured records, not prose.
4. Require explicit allowlist for command execution in coding workers.
5. Prefer remote/virtual workers for heavy browser or multi-window execution.
6. Lint typed chains before execution with `tools/chain_lint.py`.
7. Validate governed outputs against `schemas/` with `tools/schema_validate.py`.

## Output Contract

Every route or kernel-change response must include:

- `files_changed`
- `rationale`
- `services_to_update`
- `pending_integrations`

For governed execution, include:

- `StateVector`
- `DecisionRecord`

These objects must conform to:

- `schemas/statevector.schema.json`
- `schemas/decisionrecord.schema.json`
- `schemas/typed-chain.schema.json`

## References

- `references/toolcall-playbook.md`
- `references/scbe-canonical-formulas.md`
- `references/turnstile-matrix.yaml`
- `references/arxiv-chain.yaml`
- `assets/action-summary.template.yaml`
