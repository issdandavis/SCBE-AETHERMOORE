# AetherBrowse Cloud Run Quickstart

This moves your local browser agent (`agents/browser/main.py`) to Cloud Run so your AI agents can call it remotely.

## 1) Deploy browser service

```bash
chmod +x deploy/gcloud/deploy_aetherbrowse.sh
./deploy/gcloud/deploy_aetherbrowse.sh <GCP_PROJECT_ID> us-central1
```

Outputs:
- Service URL
- Health URL (`/health`)
- Browse URL (`/v1/integrations/n8n/browse`)

## 2) Get API key from Secret Manager

```bash
gcloud secrets versions access latest \
  --secret=scbe-browser-api-key \
  --project=<GCP_PROJECT_ID>
```

## 3) Run 2-5 agent jobs in parallel

```bash
export SCBE_API_KEY="<copied-secret-value>"
python scripts/aetherbrowse_swarm_runner.py \
  --jobs-file examples/aetherbrowse_tasks.sample.json \
  --url "https://<cloud-run-host>/v1/integrations/n8n/browse" \
  --concurrency 3 \
  --save-screenshots-dir artifacts/screenshots \
  --output-json artifacts/swarm_run.json
```

The runner now emits DecisionRecords + traces per job:

- `artifacts/aetherbrowse_runs/<run_id>/decision_records/*.json`
- `artifacts/aetherbrowse_runs/<run_id>/traces/*.json`

## 4) Use from n8n

- Node: `HTTP Request`
- Method: `POST`
- URL: `https://<cloud-run-host>/v1/integrations/n8n/browse`
- Header:
  - `X-API-Key: <scbe-browser-api-key>`
  - `Content-Type: application/json`
- Body:

```json
{
  "workflow_id": "wf-001",
  "run_id": "run-001",
  "source": "n8n",
  "actions": [
    {"action":"navigate","target":"https://example.com","timeout_ms":12000},
    {"action":"screenshot","target":"full_page","timeout_ms":12000}
  ],
  "session_id": "agent-1"
}
```

## Operational Notes

- This gives you remote browser execution; your local machine can stay small/off.
- Keep `concurrency` at `2-5` first to control cost and stability.
- Cloud Run may cold-start; first call can be slower.
- Rotate `scbe-browser-api-key` regularly.
