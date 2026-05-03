---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/dispatch_aligned_foundations_hf_job.py"
source_sha256: "4986b2e78f7f1ef79b7df74bede87df8dfee9d5991367636901ab54033f6a2e9"
---

# Dispatch Aligned Foundations Hf Job

## Purpose

Dispatch a real SCBE aligned-foundations LoRA training job through Hugging Face Jobs.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/dispatch_aligned_foundations_hf_job.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
