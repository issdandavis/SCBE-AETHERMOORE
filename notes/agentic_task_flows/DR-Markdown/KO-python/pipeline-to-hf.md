---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/pipeline_to_hf.py"
source_sha256: "eeb539149affc8da23be02c6185c6beb2b4e2211c5779325a674eeaa5160be98"
---

# Pipeline To Hf

## Purpose

Push news-pipeline SFT data to HuggingFace dataset.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/pipeline_to_hf.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
