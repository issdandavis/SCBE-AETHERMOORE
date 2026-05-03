---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/run_core_python_checks.py"
source_sha256: "4179c8b05cfb7a80734cbb4188ed288c4fb3c0b57df28d6301513f182eea415e"
---

# Run Core Python Checks

## Purpose

Agentic task flow wrapper for run_core_python_checks.py.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `python`

## Command

```powershell
python scripts/system/run_core_python_checks.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
