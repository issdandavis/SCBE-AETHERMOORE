---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "AV"
script_tongue_name: "Avali"
script_language: "TypeScript"
script_path: "scripts/system/ai_bridge_streamlit.py"
source_sha256: "41467951debad05d95251b168227b27a5babfe9ebcd5b64839daf917c7e004a2"
---

# Ai Bridge Streamlit

## Purpose

Browser UI for AI Bridge.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `AV` (Avali)
- Script language lane: `TypeScript`
- Route reason: `browser`

## Command

```powershell
python scripts/system/ai_bridge_streamlit.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
