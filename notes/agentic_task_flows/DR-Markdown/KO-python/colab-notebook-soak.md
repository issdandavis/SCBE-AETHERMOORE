---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/colab_notebook_soak.py"
source_sha256: "f328084a64aa49e4e227f040d2a7d421c7978db50cb3059cf00c671b7e9a4c76"
---

# Colab Notebook Soak

## Purpose

Run a long-form Colab smoke sweep across one or more SCBE notebooks.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/colab_notebook_soak.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
