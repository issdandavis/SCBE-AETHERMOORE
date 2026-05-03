---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/local_git_hygiene.py"
source_sha256: "764df4cbe820d145462fafb20d75eefeebb54e591be0ffbe77dd1750b6d61f42"
---

# Local Git Hygiene

## Purpose

Local-only git hygiene lane for intentionally noisy repo paths.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/local_git_hygiene.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
