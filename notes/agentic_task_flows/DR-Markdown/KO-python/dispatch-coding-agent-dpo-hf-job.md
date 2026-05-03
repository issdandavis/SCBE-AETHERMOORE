---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/dispatch_coding_agent_dpo_hf_job.py"
source_sha256: "ca0c5042179af07f32cbc44cf9384901ac6f38c6a459f793d922897482933217"
---

# Dispatch Coding Agent Dpo Hf Job

## Purpose

Dispatch a Stage 6 DPO repair job through Hugging Face Jobs.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/dispatch_coding_agent_dpo_hf_job.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
