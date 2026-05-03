---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/route_scripts_to_markdown_flows.py"
source_sha256: "db678812d81bab8f9aeb6c6cfd068eb4ea1f4c7b2d5b24f6bbc51b59db0be62b"
---

# Route Scripts To Markdown Flows

## Purpose

Route repo scripts into Markdown task-flow cards for agentic workflows.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `script`

## Command

```powershell
python scripts/system/route_scripts_to_markdown_flows.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
