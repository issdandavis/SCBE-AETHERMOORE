---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "CA"
script_tongue_name: "Cassisivadan"
script_language: "C"
script_path: "scripts/system/build_training_hub.py"
source_sha256: "b65a04dcb7a3a532011309b209b85d75408190a5413d073ce0b6c514eea55a4a"
---

# Build Training Hub

## Purpose

Build the SCBE training hub manifest and static website page.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `CA` (Cassisivadan)
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/build_training_hub.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
