---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "CA"
script_tongue_name: "Cassisivadan"
script_language: "C"
script_path: "scripts/system/agentbus_self_review.py"
source_sha256: "6666e70aa1de5a5c763bb8e98658d38eb9128293509c48a2c43693e118ff9a65"
---

# Agentbus Self Review

## Purpose

Propose-only self-review for the public agent bus.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `CA` (Cassisivadan)
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/agentbus_self_review.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
