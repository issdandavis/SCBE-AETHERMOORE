---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "AV"
script_tongue_name: "Avali"
script_language: "TypeScript"
script_path: "scripts/system/daily_revenue_check.py"
source_sha256: "c918d462b3746650721e9201b956c42430986a7c9959ab3826d74e707b079818"
---

# Daily Revenue Check

## Purpose

Daily revenue check — Stripe balance, npm/PyPI downloads, GitHub stars.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `AV` (Avali)
- Script language lane: `TypeScript`
- Route reason: `npm`

## Command

```powershell
python scripts/system/daily_revenue_check.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
