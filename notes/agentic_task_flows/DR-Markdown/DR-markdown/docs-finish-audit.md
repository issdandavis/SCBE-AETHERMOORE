---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "DR"
script_tongue_name: "Draumric"
script_language: "Markdown"
script_path: "scripts/system/docs_finish_audit.py"
source_sha256: "ce67bbaeffd69c1ef8891a7772e1e0dff76d974915407f7394151641f8aee293"
---

# Docs Finish Audit

## Purpose

Audit unfinished docs and local markdown link integrity.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `DR` (Draumric)
- Script language lane: `Markdown`
- Route reason: `markdown`

## Command

```powershell
python scripts/system/docs_finish_audit.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
