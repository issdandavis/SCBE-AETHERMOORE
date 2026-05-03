---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/youtube_transcript_pull.py"
source_sha256: "17e4ccfc1bb730f6c59041a1f5de1ae941847a2e5f27e1ee03b9cd82bc8241b7"
---

# Youtube Transcript Pull

## Purpose

Pull a YouTube transcript by video URL or ID.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `script`

## Command

```powershell
python scripts/system/youtube_transcript_pull.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
