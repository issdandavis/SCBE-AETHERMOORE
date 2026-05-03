---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/gather_test_corpus.py"
source_sha256: "1a80c8118f3e2a42a36f9519a3c710b80a358578ad4b4ae0008ffc599d45ffae"
---

# Gather Test Corpus

## Purpose

Gather Test Corpus — Pull records from all data sources into one corpus =========================================================================  Scans: training-data JSONL, Notion export, lore sessions, game sessions, OneDrive lore files, Obsidian vault, and HF funnel data.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/gather_test_corpus.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
