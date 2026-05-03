---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/force_delete.py"
source_sha256: "50efdaac56da4491e8291b947b860d1bbfde057e43d0e20c3c80a60fb5f4fa26"
---

# Force Delete

## Purpose

Force-delete a directory, handling Windows reserved names (nul, con, etc).

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/force_delete.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
