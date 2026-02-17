# Asana -> AetherBrowse Automation

This lets scheduled Asana tasks trigger governed headless browser work.

## Files

- `scripts/asana_aetherbrowse_orchestrator.py`
- `scripts/aetherbrowse_swarm_runner.py`

## Required environment

```bash
ASANA_TOKEN=<your_asana_pat>
ASANA_PROJECT_ID=<project_gid>
SCBE_API_KEY=<browser_api_key>
SCBE_BROWSER_WEBHOOK_URL=http://127.0.0.1:8001/v1/integrations/n8n/browse
```

## Run once

```bash
python scripts/asana_aetherbrowse_orchestrator.py \
  --project-id "$ASANA_PROJECT_ID" \
  --asana-token "$ASANA_TOKEN" \
  --endpoint-url "$SCBE_BROWSER_WEBHOOK_URL" \
  --api-key "$SCBE_API_KEY" \
  --max-tasks 5 \
  --output-json artifacts/asana_bridge/latest_run.json
```

Optional flags:

- `--complete-on-allow` marks task complete when decision is `ALLOW`
- `--include-no-due` includes tasks without due dates
- `--dry-run` only generates jobs/output without execution

## Task-to-job mapping

- Each due, incomplete Asana task is converted to one browser job.
- Default actions:
  - `navigate` (first URL found in task notes, fallback `https://example.com`)
  - `extract h1`
  - `screenshot full_page`
- You can override actions by putting JSON in task notes:

```text
AETHERBROWSE_ACTIONS:
[{"action":"navigate","target":"https://example.com"},{"action":"screenshot","target":"full_page"}]
```

## Governance behavior

- Task name or action set determines `risk_tier`.
- `DELIBERATION` requires `capability_token` (if configured).
- Decision + score is posted back to the Asana task as a comment.
- Decision records and traces are stored under `artifacts/aetherbrowse_runs/<run_id>/`.
