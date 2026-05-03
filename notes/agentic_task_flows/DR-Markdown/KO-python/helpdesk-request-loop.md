---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/helpdesk_request_loop.py"
source_sha256: "9e16ef9c136ad74ac134e8dc30d499e81f97b6325fe2176f0b2a5af81540ec25"
---

# Helpdesk Request Loop

## Purpose

Local help-desk queue for tester requests and fix plans.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/helpdesk_request_loop.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
