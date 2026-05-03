---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/advanced_ai_dispatch.py"
source_sha256: "58ad5cad3de485f3a1bb8d6113733af70abaa92a349e57063cb7f2beb35ab39b"
---

# Advanced Ai Dispatch

## Purpose

Lease-based AI dispatch spine for SCBE multi-agent work.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/advanced_ai_dispatch.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
