---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "CA"
script_language: "C"
script_path: "scripts/system/octoarms_dispatch.py"
source_sha256: "cc88c02e0b755f83d7d24a75e4a6f9f43db0ce3dc2432f892c222874db212f2b"
---

# Octoarms Dispatch

## Purpose

Agentic task flow wrapper for octoarms_dispatch.py.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `CA`
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/octoarms_dispatch.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
