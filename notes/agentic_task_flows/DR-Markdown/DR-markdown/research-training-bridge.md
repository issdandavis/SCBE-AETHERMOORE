---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "DR"
script_language: "Markdown"
script_path: "scripts/system/research_training_bridge.py"
source_sha256: "7a1445344307c36e7c0807b7b3cddbfcc06aa11fa130cefb7a4818c081569867"
---

# Research Training Bridge

## Purpose

Stage arXiv evidence and markdown notes into Hugging Face-ready training bundles.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `DR`
- Script language lane: `Markdown`
- Route reason: `markdown`

## Command

```powershell
python scripts/system/research_training_bridge.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
