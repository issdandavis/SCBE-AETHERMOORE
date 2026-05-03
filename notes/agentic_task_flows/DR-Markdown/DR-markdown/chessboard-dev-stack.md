---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "DR"
script_language: "Markdown"
script_path: "scripts/system/chessboard_dev_stack.py"
source_sha256: "f4c5bbe67deeb5f35a734d4d752caef78b6db658b9750fe563b94cfc0d4f2d14"
---

# Chessboard Dev Stack

## Purpose

Agentic task flow wrapper for chessboard_dev_stack.py.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `DR`
- Script language lane: `Markdown`
- Route reason: `stack`

## Command

```powershell
python scripts/system/chessboard_dev_stack.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
