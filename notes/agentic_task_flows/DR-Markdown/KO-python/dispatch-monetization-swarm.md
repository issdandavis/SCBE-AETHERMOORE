---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/dispatch_monetization_swarm.py"
source_sha256: "6c21f7ec94ae115abbc34fe94fa6b8f4e59b003525cd819b36fe5b90566bd641"
---

# Dispatch Monetization Swarm

## Purpose

Emit monetization lane assignments onto the SCBE cross-talk bus.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/dispatch_monetization_swarm.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
