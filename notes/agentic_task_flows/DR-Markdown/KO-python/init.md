---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/__init__.py"
source_sha256: "40db1d31a10dc93b883048b31780ecf82fba643e6b3be5d85254106cce2a1cf7"
---

# Init

## Purpose

System-level automation and audit helpers for SCBE.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `helper`

## Command

```powershell
python scripts/system/__init__.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
