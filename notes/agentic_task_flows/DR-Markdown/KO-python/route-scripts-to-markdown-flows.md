---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/route_scripts_to_markdown_flows.py"
source_sha256: "93977d472c38f558cc06b4e1d63886f061f896b06051b5fdcc4ca8cc6a2ee918"
---

# Route Scripts To Markdown Flows

## Purpose

Route repo scripts into Markdown task-flow cards for agentic workflows.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
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
