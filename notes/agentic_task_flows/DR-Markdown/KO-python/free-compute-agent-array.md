---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/free_compute_agent_array.py"
source_sha256: "f1eb26b56e5c71ac540c3bd5b8cae7a1df99a744aff2f4ff987c9ea1364a1124"
---

# Free Compute Agent Array

## Purpose

Build a governed free-compute agent array plan for coding work.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/free_compute_agent_array.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
