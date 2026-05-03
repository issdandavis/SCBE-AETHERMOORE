---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/phone_navigation_telemetry.py"
source_sha256: "685154a75b638a21ce159160be881f07f7630b1c018da402c6e3391aaa2ea082"
---

# Phone Navigation Telemetry

## Purpose

Build route/text/tap-target telemetry from Android UI dumps.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/phone_navigation_telemetry.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
