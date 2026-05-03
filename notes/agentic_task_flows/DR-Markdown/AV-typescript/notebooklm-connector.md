---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "AV"
script_tongue_name: "Avali"
script_language: "TypeScript"
script_path: "scripts/system/notebooklm_connector.py"
source_sha256: "5f51c4d547f95752ed02294531a517cbe52ca44ff4ba2b9d53d4ececf6ce06e5"
---

# Notebooklm Connector

## Purpose

NotebookLM connector (browser-first) for SCBE terminal workflows.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `AV` (Avali)
- Script language lane: `TypeScript`
- Route reason: `browser`

## Command

```powershell
python scripts/system/notebooklm_connector.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
