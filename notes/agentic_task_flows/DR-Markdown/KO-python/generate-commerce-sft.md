---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/generate_commerce_sft.py"
source_sha256: "3330ba62e56e9bfb12a9f0f72e0b3e202b7d52a733c2c4cc3a974ae953cdd422"
---

# Generate Commerce Sft

## Purpose

Generate SCBE-format SFT training data for the commerce LoRA adapter.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/generate_commerce_sft.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
