# Profit Autopilot Reference

## Success Criteria
- `fact_gate` is `ok`
- Shopify launch pack command exits with `returncode=0`
- If `--publish-live` is used, `live_sync.ok=true`

## Common Blockers
- Missing Shopify token (`SHOPIFY_ACCESS_TOKEN` or `SHOPIFY_ADMIN_TOKEN`)
- Storefront password gate still enabled
- Playwright profile not authenticated in Shopify admin

## Artifact Paths
- `artifacts/profit-autopilot/<timestamp>/profit_autopilot_report.json`
- `artifacts/shopify-launch-pack/<timestamp>/shopify-launch-pack.json`

## Recovery Commands
```powershell
# Dry-run path
pwsh -ExecutionPolicy Bypass -File scripts/system/run_profit_autopilot.ps1

# Live attempt
pwsh -ExecutionPolicy Bypass -File scripts/system/run_profit_autopilot.ps1 -PublishLive
```
