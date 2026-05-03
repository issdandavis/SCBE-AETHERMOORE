---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/storage_compaction_lab.py"
source_sha256: "a033db8669b42c4bff148c0d9bde506de0fb7edea37c8758509df8c230caa171"
---

# Storage Compaction Lab

## Purpose

Run controlled storage-compaction sweeps for SCBE storage surfaces.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/storage_compaction_lab.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
