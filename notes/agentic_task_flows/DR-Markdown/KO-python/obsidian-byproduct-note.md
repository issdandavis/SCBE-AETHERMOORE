---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/obsidian_byproduct_note.py"
source_sha256: "62862b7530d40142a3989c764b6d5d4b93ba84968c8ef6444a7a6856b85be40f"
---

# Obsidian Byproduct Note

## Purpose

Write a work-session byproduct note into Obsidian.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/obsidian_byproduct_note.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
