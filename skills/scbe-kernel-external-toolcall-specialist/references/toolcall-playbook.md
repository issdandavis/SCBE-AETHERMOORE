# Tool-Call Playbook

## 1) External Service Discovery Gate

Before implementing any external route:

1. Discover callable tool surface.
2. Classify service state:
   - `service`
   - `callable_now`
   - `needs_configuration`
   - `missing_env`
   - `scopes`
   - `rate_limits`
3. Record connector decision in structured route output.

Canonical discovery contract:

```json
{
  "service": "notion",
  "callable_now": false,
  "needs_configuration": true,
  "missing_env": ["NOTION_TOKEN"],
  "scopes": [],
  "rate_limits": {"requests_per_minute": null}
}
```

## 2) Typed Chain Schema

```yaml
chain:
  id: "kernel-ext-route"
  name: "SCBE external route"
  repo: "owner/repo"
  steps:
    - id: discover
      type: tool
      tool: "connector.discovery"
      input: {}
      output_key: discovery
    - id: decide
      type: gate
      condition: "discovery.callable_now == true"
      on_true: execute
      on_false: config_issue
    - id: execute
      type: tool
      tool: "connector.action"
      input: {}
      output_key: result
    - id: config_issue
      type: tool
      tool: "issue.create"
      input: {}
      output_key: ticket
```

## 3) Domain Turnstile Mapping

- `browser`
  - Allowed: `ALLOW`, `HOLD`, `HONEYPOT`
  - Notes: Human checkpoint accepted.
- `vehicle`
  - Allowed: `ALLOW`, `PIVOT`, `DEGRADE`
  - Notes: No stall; choose safe maneuver.
- `fleet`
  - Allowed: `ALLOW`, `ISOLATE`, `DEGRADE`, `HONEYPOT`
  - Notes: Isolate bad node, keep swarm moving.
- `antivirus`
  - Allowed: `ALLOW`, `ISOLATE`, `HONEYPOT`
  - Notes: Last-line containment.
- `arxiv`
  - Allowed: `ALLOW`, `HOLD`, `STOP`
  - Notes: `HOLD` for human PDF review and final submit.
- `patent`
  - Allowed: `ALLOW`, `HOLD`, `STOP`
  - Notes: `HOLD` for attorney review; never auto-file.

Table-driven form is defined in `references/turnstile-matrix.yaml`.

## 4) Required Governed Output

Each executed gate/action should emit:

```yaml
StateVector:
  worker_id: "node-x"
  task_id: "task-123"
  role: "coder"
  status: "done"
  timestamp: "2026-02-18T00:00:00Z"

DecisionRecord:
  action: "ALLOW|HOLD|PIVOT|DEGRADE|ISOLATE|HONEYPOT|STOP"
  signature: "node-x:task-123:epoch"
  timestamp: "2026-02-18T00:00:00Z"
  reason: "short deterministic reason"
  confidence: 0.0
```

## 5) Safety Checklist for Command-Exec Nodes

1. Restrict command prefixes (allowlist).
2. Restrict filesystem writes to workspace subtree.
3. Capture stdout/stderr to structured result.
4. Apply per-task lease and retry bounds.
5. Emit failure records as machine-readable objects.

## 6) Chain Enforcement

Use the schema + linter:

1. `schemas/typed-chain.schema.json`
2. `tools/chain_lint.py`

Minimum lints:

- Step ids are unique.
- Step type is one of `tool`, `llm`, `gate`.
- `gate.condition` references declared output keys.
- Unknown tool names are forbidden unless `needs_configuration: true`.

## 7) Canonical Templates

- ArXiv chain template: `references/arxiv-chain.yaml`
