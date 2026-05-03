---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "DR"
script_language: "Markdown"
script_path: "scripts/system/build_card_stack.py"
source_sha256: "6b491761351aba9a1f4495d083b722edddd36c406b22f77c962bdb1fc519be08"
---

# Build Card Stack

## Purpose

Regenerate the SCBE AI card stack — one card per dataset / model config / run / experiment artifact, written to ``data/cards/ai_card_stack.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `DR`
- Script language lane: `Markdown`
- Route reason: `stack`

## Command

```powershell
python scripts/system/build_card_stack.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
