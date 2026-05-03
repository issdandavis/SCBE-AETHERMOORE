---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "AV"
script_language: "TypeScript"
script_path: "scripts/system/aetherbrowser_search.py"
source_sha256: "688bbd693d77ec0836f456d1cfa7f30618bd7a5201793f6dd5728fbbaa524636"
---

# Aetherbrowser Search

## Purpose

Unified AetherBrowser search entrypoint.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `AV`
- Script language lane: `TypeScript`
- Route reason: `browser`

## Command

```powershell
python scripts/system/aetherbrowser_search.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
