---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "CA"
script_tongue_name: "Cassisivadan"
script_language: "C"
script_path: "scripts/system/verify_docs_publish_surface.py"
source_sha256: "f6166ba2fb82886868918815779386e6b7dd0041154c090224fe029477aa23fd"
---

# Verify Docs Publish Surface

## Purpose

Verify the static docs surface has required pages and live checkout links.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `CA` (Cassisivadan)
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/verify_docs_publish_surface.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
