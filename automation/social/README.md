# SCBE X + n8n Monetize Pack

This pack wires your existing SCBE publish dispatcher to n8n webhooks for:

- `x` (new thread/standalone posts)
- `x_reply` (reply/engagement loops)
- `merch_sale` (promo + offer pushes)
- `merch_upload` (catalog/upload/update events)

It is built to run with:

- `C:\Users\issda\.codex\skills\scbe-research-publishing-autopilot\scripts\campaign_orchestrator.py`
- `C:\Users\issda\.codex\skills\scbe-research-publishing-autopilot\scripts\claim_gate.py`
- `C:\Users\issda\.codex\skills\scbe-research-publishing-autopilot\scripts\publish_dispatch.py`

## 1) Copy Example Pack

Use PowerShell from repo root:

```powershell
New-Item -ItemType Directory -Force .\artifacts\social | Out-Null
Copy-Item .\automation\social\examples\* .\artifacts\social\ -Force
```

## 2) Set Webhook Environment Variables (n8n)

Point these to your n8n webhook endpoints:

```powershell
$env:SCBE_X_WEBHOOK_URL = "http://127.0.0.1:5678/webhook/scbe-x-post"
$env:SCBE_X_WEBHOOK_TOKEN = "replace_me"
$env:SCBE_X_REPLY_WEBHOOK_URL = "http://127.0.0.1:5678/webhook/scbe-x-reply"
$env:SCBE_X_REPLY_WEBHOOK_TOKEN = "replace_me"
$env:SCBE_MERCH_SALE_WEBHOOK_URL = "http://127.0.0.1:5678/webhook/scbe-merch-sale"
$env:SCBE_MERCH_SALE_WEBHOOK_TOKEN = "replace_me"
$env:SCBE_MERCH_UPLOAD_WEBHOOK_URL = "http://127.0.0.1:5678/webhook/scbe-merch-upload"
$env:SCBE_MERCH_UPLOAD_WEBHOOK_TOKEN = "replace_me"
```

## 3) Run Pipeline

```powershell
python C:\Users\issda\.codex\skills\scbe-research-publishing-autopilot\scripts\claim_gate.py --posts .\artifacts\social\campaign_posts.x-monetize.json --repo-root C:\Users\issda\SCBE-AETHERMOORE --out .\artifacts\social\claim_gate_report.json
python C:\Users\issda\.codex\skills\scbe-research-publishing-autopilot\scripts\campaign_orchestrator.py --campaign .\artifacts\social\campaign.x-monetize.json --out .\artifacts\social\dispatch_plan.json
python C:\Users\issda\.codex\skills\scbe-research-publishing-autopilot\scripts\publish_dispatch.py --plan .\artifacts\social\dispatch_plan.json --posts .\artifacts\social\campaign_posts.x-monetize.json --connectors .\artifacts\social\connectors.n8n.json --approval .\artifacts\social\approvals.x-monetize.json --claim-report .\artifacts\social\claim_gate_report.json --out-log .\artifacts\social\dispatch_log.jsonl --state .\artifacts\social\dispatch_state.json
```

## 4) Thread Starter

Use `automation/social/examples/thread.launch.md` as your first X thread payload source.

## 5) Notes

- Keep approvals on for production dispatch (`--allow-unapproved` off).
- Dispatcher now includes full `post_data` and `meta` in webhook payload for reply/merch actions.
- If you need dry-runs, add `--dry-run` to `publish_dispatch.py`.

