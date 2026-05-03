---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/stripe_simulator.py"
source_sha256: "2ff422327be6467642e6d68adfd815ee5b9c608f4f0901a2a589a7fa515211de"
---

# Stripe Simulator

## Purpose

Stripe sandbox transaction simulator — generates JSONL training pairs.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/stripe_simulator.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
