# AI-to-AI Comms Chain Schema

Use this schema for automation chains in SCBE workflows.

## Typed Step Model

```yaml
chain:
  id: "string"
  name: "string"
  repo: "owner/repo"
  steps:
    - id: "string"
      type: tool
      tool: "service.action"
      input: {}
      output_key: "string"
    - id: "string"
      type: llm
      model: "string"
      tongue: "KO|AV|RU|CA|UM|DR"
      input_from: "step_id.output_key"
      output_key: "string"
    - id: "string"
      type: gate
      condition: "expression over prior outputs"
      on_true: "next_step_id"
      on_false: "next_step_id"
```

## Requirements

1. Include typed steps only: `tool`, `llm`, `gate`.
2. Keep branch conditions explicit and testable.
3. Record external service failures as structured outputs, not plain text.
4. Route denial paths to issue tracking with machine-readable failure details.
