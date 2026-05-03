---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/consolidate_kaggle_kernels.py"
source_sha256: "de260e0bf132b456968bb015f05dbb96a17c1206523ba2e32f7a648014e36c0b"
---

# Consolidate Kaggle Kernels

## Purpose

Inventory and consolidate Kaggle kernels without deleting by default.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/consolidate_kaggle_kernels.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
