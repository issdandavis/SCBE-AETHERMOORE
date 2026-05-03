---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/polly_cross_model_bootstrap.py"
source_sha256: "8a96a6e8eeb514aa75b447452773bb8a14c10a0000950e31e296d4bdd1433ae8"
---

# Polly Cross Model Bootstrap

## Purpose

Polly cross-model training bootstrap.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/polly_cross_model_bootstrap.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
