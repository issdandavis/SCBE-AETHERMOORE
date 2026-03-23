# Shopify Management Ops Reference

## Modes
- `audit`: runs launch-pack in test mode (`--run-both-side-test`)
- `publish`: launch-pack + live publish
- `gate-audit`: inspects storefront password protection state
- `gate-disable`: attempts to disable password gate in Shopify Admin
- `images-dry` / `images-upload`: image mapping and upload
- `full-live`: full profit autopilot with live publish

## Success Checks
- Launch pack result JSON exists
- For live runs: `live_sync.ok=true`
- For storefront visibility: password gate not detected

## Typical Blockers
- Missing Shopify API token in active process
- Admin auth session required for gate toggling
- Storefront still set to password protected
