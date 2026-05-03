---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/import_hf_model_to_ollama.py"
source_sha256: "65e58ce21f3b0570ff7d4aba305ce20d0f957ac1ab03cfc4e800605ffb328a37"
---

# Import Hf Model To Ollama

## Purpose

Download a Hugging Face causal LM, convert it to GGUF, and import into Ollama.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/import_hf_model_to_ollama.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
