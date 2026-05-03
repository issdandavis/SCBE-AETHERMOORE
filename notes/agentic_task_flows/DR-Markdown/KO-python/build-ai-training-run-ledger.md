---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/build_ai_training_run_ledger.py"
source_sha256: "cf0ab55f36a6559c9121183af964235ed981b16da4d4a489352022151c6742d4"
---

# Build Ai Training Run Ledger

## Purpose

Build a platform-split ledger of SCBE AI training runs and next conversions.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/build_ai_training_run_ledger.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
