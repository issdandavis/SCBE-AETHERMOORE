---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/monetization_connector_push.py"
source_sha256: "6bafd7428aa61ff8a41c96657cef31e35c0b96d453527eda09eccd0d002593a4"
---

# Monetization Connector Push

## Purpose

Push monetization leads and checkout offers into configured connectors.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/monetization_connector_push.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
