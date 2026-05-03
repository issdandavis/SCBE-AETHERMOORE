---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "CA"
script_language: "C"
script_path: "scripts/system/run_github_sweep.py"
source_sha256: "d2989076f7824a67fcff2ef058f3bb72c1b8c63352f13776e6e1d4d8a1f1cd7c"
---

# Run Github Sweep

## Purpose

Agentic task flow wrapper for run_github_sweep.py.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `CA`
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/run_github_sweep.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
