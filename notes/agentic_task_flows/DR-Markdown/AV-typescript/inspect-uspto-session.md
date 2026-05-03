---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "AV"
script_tongue_name: "Avali"
script_language: "TypeScript"
script_path: "scripts/system/inspect_uspto_session.py"
source_sha256: "95c2cb22819fbece8ce24dd97436dfedc79798ed73497a400d76c7560f5aefe7"
---

# Inspect Uspto Session

## Purpose

Inspect a live USPTO browser session through the AetherBrowser CDP lane.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `AV` (Avali)
- Script language lane: `TypeScript`
- Route reason: `browser`

## Command

```powershell
python scripts/system/inspect_uspto_session.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
