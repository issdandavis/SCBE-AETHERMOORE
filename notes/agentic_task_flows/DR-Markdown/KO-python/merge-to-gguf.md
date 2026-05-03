---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/merge_to_gguf.py"
source_sha256: "f19ffa45f76c0859913432059e5fce24477deb1105fd149037a39a136f362d4f"
---

# Merge To Gguf

## Purpose

Merge a trained LoRA adapter into the base model, then export to GGUF for Ollama.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/merge_to_gguf.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
