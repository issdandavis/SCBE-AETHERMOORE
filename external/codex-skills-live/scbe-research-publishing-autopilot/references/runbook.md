# SCBE Research Publishing Runbook

## Purpose
Operate multi-hour research-to-post cycles that are accurate, monetizable, and monitorable.

## Principle
- Context of self is king.
- Start from your prior post history and your dataset inventory before writing new copy.

## Inputs
- `campaign.json`
- `past_posts.jsonl`
- `datasets_manifest.json`
- `campaign_posts.json`
- `retrigger_rules.json`
- Local source repo (docs/code/lore)

## Execution Order
1. Build context-of-self pack.
```powershell
python scripts/context_packer.py --posts-history .\artifacts\past_posts.jsonl --dataset-manifest .\artifacts\datasets_manifest.json --out .\artifacts\self_context_pack.json
```

2. Build and validate claim map.
```powershell
python scripts/claim_gate.py --posts .\artifacts\campaign_posts.json --repo-root C:\Users\issda\SCBE-AETHERMOORE --out .\artifacts\claim_gate_report.json
```
- Stop on failure.
- Fix claim/source/anchor and rerun.

3. Build multi-hour dispatch plan.
```powershell
python scripts/campaign_orchestrator.py --campaign .\artifacts\campaign.json --out .\artifacts\dispatch_plan.json
```

4. Run posting agent according to `dispatch_plan.json`.
- Keep every post linked to source-backed claims.
- Write send logs and per-post metric snapshots.
```powershell
python scripts/publish_dispatch.py --plan .\artifacts\dispatch_plan.json --posts .\artifacts\campaign_posts.json --connectors .\artifacts\connectors.json --approval .\artifacts\approvals.json --claim-report .\artifacts\claim_gate_report.json --out-log .\artifacts\dispatch_log.jsonl --state .\artifacts\dispatch_state.json
```

5. Evaluate retrigger actions.
```powershell
python scripts/retrigger_monitor.py --metrics .\artifacts\metrics.jsonl --rules .\artifacts\retrigger_rules.json --state .\artifacts\retrigger_state.json --out .\artifacts\retrigger_actions.json
```

6. Apply retrigger actions.
- Rewrite hook, change CTA, or switch channel window based on rule output.
- Re-run evidence gate if any claims changed.

7. Write daily Obsidian report.
```powershell
python scripts/write_obsidian_report.py --vault-dir "C:\Users\issda\OneDrive\Documents\DOCCUMENTS\A follder" --dispatch-log .\artifacts\dispatch_log.jsonl --claim-report .\artifacts\claim_gate_report.json --retrigger-actions .\artifacts\retrigger_actions.json --self-context .\artifacts\self_context_pack.json --campaign-id scbe-autopilot
```

## 2.5-Party Monitoring Pattern
Treat this as your in-house control layer over external platforms:
- First party: your repo/docs/lore + datasets + offers.
- Third party: social/web platforms and their metrics.
- 2.5 party: your automation observability and governance glue.

Required 2.5-party artifacts:
- `dispatch_plan.json`
- `dispatch_log.jsonl`
- `metrics.jsonl`
- `retrigger_actions.json`
- `claim_gate_report.json`

## Minimum Daily QA
- Confirm zero failed claims.
- Confirm all posts have valid CTA path.
- Confirm no duplicate posting window collisions.
- Confirm cooldown respected for retriggered items.
