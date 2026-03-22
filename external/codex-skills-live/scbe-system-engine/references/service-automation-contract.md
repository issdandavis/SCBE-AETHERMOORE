# Service Automation Contract

## Discovery-first Rule

For every external service in scope, first run discovery, then route:

1. What action is requested?
2. Is the action discoverable/authorized now?
3. Can execution happen with current credentials?
4. If not, return a `pending_integrations` list with exact setup steps.

## Connector Status Vocabulary

- `callable now`: action exists and appears authenticated.
- `needs config`: action exists but auth/webhook URL/secret not registered.
- `not discovered`: action unavailable in the current MCP surface.

## Known Service Profiles

### GitHub (PR lifecycle)

- Inputs: `owner/repo`, `pull_request` payload, labels/comments.
- Typical actions:
  - read PR diff
  - post comment
  - create/check issues

### Linear

- Inputs: issue title, description, tags.
- Typical actions:
  - create issue
  - search workspace metadata

### Zapier

- Inputs: trigger id, action id, route id, environment.
- Typical actions:
  - trigger workflow
  - receive event payload
  - route to tools and LLM steps

### Hugging Face

- Inputs: dataset_id/model_id/query string.
- Typical actions:
  - search dataset/model/space
  - create repo card metadata
  - upload artifacts

### Notion

- Inputs: page title, database query, block insert payload.
- Typical actions:
  - search existing pages
  - append audit notes
  - create structured status pages

## Security Requirements

- Do not store secrets in file output.
- Use service tokens only inside runtime environment or dedicated secret store.
- Keep retry IDs and correlation IDs for traceability.

## Minimal Chain Rule

Every chain must use typed steps:

- `tool` step first for discovery or side-effect action.
- `llm` step for reasoning/decision.
- `gate` step for branching with explicit conditions.

## Audit Template

- Title: action + timestamp
- Status: `ALLOWED`, `QUARANTINE`, `DENY`
- Evidence: file path(s), test ids, failed assertions, connector status.
