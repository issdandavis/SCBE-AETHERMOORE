# Polly + Clay Squad Runtime

This runtime provides a practical multi-agent browser pattern:

- `Polly`: leader route controller and user-facing coordinator
- `Clay-01..N`: concurrent browser workers
- Lightweight HITL dashboard generated only when human review is needed

## Why this shape

- Fast: fixed worker pool + chunked action requests
- Reliable: same governed browser endpoint and containment checks
- Human-in-the-loop: full screenshot + extracted text snapshot only on escalations
- Lightweight by default: screenshot payloads stay truncated unless HITL requests full data

## Run from PowerShell

```powershell
./scripts/run_polly_clay_squad.ps1
```

Custom run:

```powershell
./scripts/run_polly_clay_squad.ps1 -OrdersFile examples/polly_clay_orders.gumroad.sample.json -Clays 4 -OpenHitlBrowser
```

Continuous mode:

```powershell
./scripts/run_polly_clay_squad.ps1 -Continuous -PollSec 20
```

## Python direct run

```powershell
python scripts/polly_clay_squad.py --orders-file examples/polly_clay_orders.gumroad.sample.json --clays 4 --start-local-service --service-port 8014
```

## Outputs

- Summary: `artifacts/polly_clay/summary_latest.json`
- HITL queue: `artifacts/polly_clay/hitl/queue.jsonl`
- HITL dashboard: `artifacts/polly_clay/hitl/index.html`
- HITL screenshots: `artifacts/polly_clay/hitl/screenshots/*.png`

## Work-order format

```json
{
  "orders": [
    {
      "order_id": "gumroad-recon",
      "workflow_id": "gumroad-polly-clay",
      "dry_run": true,
      "actions": [
        { "action": "navigate", "target": "https://gumroad.com" },
        { "action": "extract", "target": "body" },
        { "action": "screenshot", "target": "full_page" }
      ]
    }
  ]
}
```

For HITL full screenshot on demand, the runtime issues `include_full_data=true` only for escalation snapshots.
## Risk Contracts (MIN/MID/MAX)

Polly routes every order through a contract before any Clay executes.

- `MIN`: read-only recon, forced `dry_run`, no write actions.
- `MID`: bounded write automation for routine jobs.
- `MAX`: high-impact tasks, requires context keys: `task_id`, `change_ticket`, `human_approval_id`.

Contract templates:

- `policies/contracts/polly_clay_min.json`
- `policies/contracts/polly_clay_mid.json`
- `policies/contracts/polly_clay_max.json`

Run with a contract:

```powershell
./scripts/run_polly_clay_squad.ps1 -RiskContract MIN
./scripts/run_polly_clay_squad.ps1 -RiskContract MID
./scripts/run_polly_clay_squad.ps1 -RiskContract MAX
```

Or point directly to a custom contract file:

```powershell
python scripts/polly_clay_squad.py --orders-file examples/polly_clay_orders.gumroad.sample.json --risk-contract policies/contracts/polly_clay_mid.json
```

Summary output now includes:

- `risk_contract` metadata (`contract_id`, `risk_tier`, `path`)
- `blocked_by_contract`
- `routed_orders`
