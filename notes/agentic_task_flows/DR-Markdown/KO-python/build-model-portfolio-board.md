---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/build_model_portfolio_board.py"
source_sha256: "ba1fc20a6a16dddc71d5523d2103358da47990c083c27dc582c4ce1385d259ab"
---

# Build Model Portfolio Board

## Purpose

Build a model portfolio board for SCBE Hugging Face + local training profiles.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/build_model_portfolio_board.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
