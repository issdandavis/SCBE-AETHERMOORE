---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/terminal_ai_router.py"
source_sha256: "f4620da8b0bc2e3f20e2127b2fff4b26a07fa14088348d19a4d7f1fbb8e47830"
---

# Terminal Ai Router

## Purpose

Cheap-first terminal router for OpenAI/Anthropic/xAI with daily spend caps.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/terminal_ai_router.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
