---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/cleanup_local_github_hygiene.py"
source_sha256: "1d9308e82fe9eab8dd8ebdf919540422531d1ba92445a9d60842a05109f1c8ad"
---

# Cleanup Local Github Hygiene

## Purpose

Safe repo hygiene cleanup for local artifacts + remote ref pruning.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/cleanup_local_github_hygiene.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
