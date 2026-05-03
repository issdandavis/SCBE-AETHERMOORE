---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/build_cross_language_lookup.py"
source_sha256: "ec17ff08062953cd57962daea9145383b3902eed7a1a248e07fabc7e4482aac9"
---

# Build Cross Language Lookup

## Purpose

Compose the cross-language lookup view into a single inspection artifact.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/build_cross_language_lookup.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
