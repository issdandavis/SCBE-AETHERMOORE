---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/crosstalk_reliability_manager.py"
source_sha256: "f666e951d3a5d1d9b2859aafa17db65bf9477975dcf6cbf9794eb631e11c2b12"
---

# Crosstalk Reliability Manager

## Purpose

Cross-talk reliability checker and repair utility.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/crosstalk_reliability_manager.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
