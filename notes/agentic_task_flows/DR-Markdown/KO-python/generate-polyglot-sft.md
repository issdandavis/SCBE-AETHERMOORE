---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/generate_polyglot_sft.py"
source_sha256: "35bf3b3071d6b9cba8763e75f3159c0499fb686cefada2f7b3ba980635464636"
---

# Generate Polyglot Sft

## Purpose

Generate polyglot cross-language SFT training data using the ca_lexicon as the swap table.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/generate_polyglot_sft.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
