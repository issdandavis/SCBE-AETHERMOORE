---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "RU"
script_language: "Rust"
script_path: "scripts/system/preflight_zero_cost_training.py"
source_sha256: "00dafd6f8bf45d7597b719f4fe1fe74b536f3ac589c071fe84fd90f7665a8699"
---

# Preflight Zero Cost Training

## Purpose

Fail-fast checks for the zero-cost local training profile.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `RU`
- Script language lane: `Rust`
- Route reason: `zero-cost`

## Command

```powershell
python scripts/system/preflight_zero_cost_training.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
