---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/pilot_demo_to_decision.py"
source_sha256: "c168d340ed1246faee792326a9afb8fb790fc4eea528ed4fb289681b5515225d"
---

# Pilot Demo To Decision

## Purpose

Run a compact SCBE pilot evidence path and emit a decision packet.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/pilot_demo_to_decision.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
