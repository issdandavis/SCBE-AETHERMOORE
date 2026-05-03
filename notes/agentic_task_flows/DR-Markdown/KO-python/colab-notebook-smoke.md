---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/colab_notebook_smoke.py"
source_sha256: "abf51704647f92661028ae2986074236babc4ff57a0d0231d380f632109550ed"
---

# Colab Notebook Smoke

## Purpose

Smoke-test a Colab notebook through Playwright with a safe scratch cell.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/colab_notebook_smoke.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
