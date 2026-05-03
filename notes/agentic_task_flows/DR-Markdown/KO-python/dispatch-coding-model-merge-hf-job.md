---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/dispatch_coding_model_merge_hf_job.py"
source_sha256: "2b5fc71a9c775b82daf52eaf231eec134ffc2dd9e0c3db9093c75344a0db8b44"
---

# Dispatch Coding Model Merge Hf Job

## Purpose

Plan and dispatch a Hugging Face job that merges coding-agent LoRA adapters.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/dispatch_coding_model_merge_hf_job.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
