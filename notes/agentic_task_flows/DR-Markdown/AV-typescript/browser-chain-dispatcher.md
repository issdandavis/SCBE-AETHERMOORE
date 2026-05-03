---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "AV"
script_language: "TypeScript"
script_path: "scripts/system/browser_chain_dispatcher.py"
source_sha256: "986be1a6309cc8f05f263455c6f8fcd080013208c6d84cafafa503899af32980"
---

# Browser Chain Dispatcher

## Purpose

Simple browser lane dispatcher for SCBE browser skills.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `AV`
- Script language lane: `TypeScript`
- Route reason: `browser`

## Command

```powershell
python scripts/system/browser_chain_dispatcher.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
