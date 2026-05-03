---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/model_server.py"
source_sha256: "b6718497fb5f9f4b37ba798394bfa50d074bb180535f89d5725ab80092ed9f5e"
---

# Model Server

## Purpose

Local model server — loads SmolLM2-360M once, swaps LoRA adapters per request.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/model_server.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
