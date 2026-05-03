---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/hand_tune.py"
source_sha256: "b393afaa807f81692e3af6051e6b4835badc7a1a5f83db260ab0053f2b21e478"
---

# Hand Tune

## Purpose

Hand-tune a LoRA adapter on SmolLM2-360M or Qwen2.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/hand_tune.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
