---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/refresh_universal_skill_synthesis.py"
source_sha256: "9e3c0f1bbadb8a6c272b5e45201dc138331714de2220c3302a352b662e0d85ec"
---

# Refresh Universal Skill Synthesis

## Purpose

Build an auto-updating skill synthesis matrix + Sacred Tongues lexicon.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/refresh_universal_skill_synthesis.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
