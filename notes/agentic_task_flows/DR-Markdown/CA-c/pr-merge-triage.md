---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "CA"
script_tongue_name: "Cassisivadan"
script_language: "C"
script_path: "scripts/system/pr_merge_triage.py"
source_sha256: "7aadce89e2251ca6ee49c31477210af3efd8ef2ae8285ac836e06bcc9b0cf479"
---

# Pr Merge Triage

## Purpose

Agentic task flow wrapper for pr_merge_triage.py.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `CA` (Cassisivadan)
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/pr_merge_triage.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
