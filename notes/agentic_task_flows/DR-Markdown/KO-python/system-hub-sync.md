---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/system_hub_sync.py"
source_sha256: "661aba2c5ce7d042fa1c0825a26bca4da2bb6bdd3884f54b0e80150d8d8acc3f"
---

# System Hub Sync

## Purpose

Unified connector sync: Notion -> Obsidian -> GitHub -> Dropbox.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/system_hub_sync.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
