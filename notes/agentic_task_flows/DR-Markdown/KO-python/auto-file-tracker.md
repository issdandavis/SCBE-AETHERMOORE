---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/auto_file_tracker.py"
source_sha256: "f2a14eba5aa5f8adabb97930b6b359aade47643c6969a2eeec9ccd40e4d6fd97"
---

# Auto File Tracker

## Purpose

Hash-only file tracking snapshots for SCBE agent-bus work.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/auto_file_tracker.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
