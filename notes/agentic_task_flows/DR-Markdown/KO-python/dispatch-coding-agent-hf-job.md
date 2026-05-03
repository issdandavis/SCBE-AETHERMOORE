---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "KO"
script_tongue_name: "Kor'aelin"
script_language: "Python"
script_path: "scripts/system/dispatch_coding_agent_hf_job.py"
source_sha256: "dcc2aecc27e0207dfa3303623aaf967e7475e873bad94a50923cc5d2cd3d4927"
---

# Dispatch Coding Agent Hf Job

## Purpose

Dispatch a real SCBE coding-agent LoRA training job through Hugging Face Jobs.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `KO` (Kor'aelin)
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/dispatch_coding_agent_hf_job.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
