# n8n X/Twitter Monetize Automation

This sets up posting/reply/merch actions through n8n with a queue-driven runner.

## Files
- `workflows/n8n/x_growth_merch_ops.workflow.json`
- `workflows/n8n/x_ops_queue.sample.json`
- `scripts/system/x_ops_queue_runner.mjs`

## 1) Import workflow
In n8n:
1. Workflows -> Import from file
2. Select `workflows/n8n/x_growth_merch_ops.workflow.json`
3. Activate webhook node path `scbe-x-ops`

## 2) Configure secrets
Set these in your shell:
```powershell
$env:N8N_X_OPS_WEBHOOK_URL="https://YOUR-N8N-HOST/webhook/scbe-x-ops"
$env:N8N_X_OPS_API_KEY="YOUR_OPTIONAL_API_KEY"
```

Inside the n8n workflow replace:
- `PASTE_X_BEARER_TOKEN`
- `PASTE_SCBE_API_KEY`

## 3) Dry run queue
```powershell
node scripts/system/x_ops_queue_runner.mjs --queue workflows/n8n/x_ops_queue.sample.json --dry-run
```

## 4) Execute queue
```powershell
node scripts/system/x_ops_queue_runner.mjs --queue workflows/n8n/x_ops_queue.sample.json
```

## Action types
- `post`: publish a post to X
- `reply`: reply to an existing tweet (`reply_to`)
- `merch`: trigger SCBE browser workflow for product interaction checks/promos

## Cost control
- Start with queue batches of 3-5 items.
- Keep reply automation human-reviewed for brand safety.
- Route all failed webhook responses into an error queue for retry.
