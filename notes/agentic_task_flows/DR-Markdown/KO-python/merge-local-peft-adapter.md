---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/merge_local_peft_adapter.py"
source_sha256: "de076db69cdc360bd3f1134fb9a3f71317731a243258fc37e4f61302fb4a62fa"
---

# Merge Local Peft Adapter

## Purpose

Merge a PEFT LoRA adapter into its base model locally.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/merge_local_peft_adapter.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
