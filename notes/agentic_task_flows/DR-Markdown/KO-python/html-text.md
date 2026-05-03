---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/html_text.py"
source_sha256: "f005c4983aca01fd3309654704976407a7e718a57365eeea3c8aefc2f7630b43"
---

# Html Text

## Purpose

HTML-to-text helpers for script-safe extraction.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `helper`

## Command

```powershell
python scripts/system/html_text.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
