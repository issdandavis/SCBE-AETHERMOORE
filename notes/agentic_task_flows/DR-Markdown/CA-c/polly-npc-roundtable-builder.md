---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "CA"
script_language: "C"
script_path: "scripts/system/polly_npc_roundtable_builder.py"
source_sha256: "62d172011b0a9653fe6146fe3b7a8f7a5bdc6746435d9a58fb871e9e0b01caee"
---

# Polly Npc Roundtable Builder

## Purpose

Build NPC training rows from Aetherlore using a Round Table format.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `CA`
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/polly_npc_roundtable_builder.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
