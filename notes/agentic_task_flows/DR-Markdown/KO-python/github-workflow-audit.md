---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/github_workflow_audit.py"
source_sha256: "78a1beb36dc3cfec9f3c4135b30f3397a3d2a3b6ad8721d9c87f298d2ab8aa08"
---

# Github Workflow Audit

## Purpose

GitHub Workflow Audit & Self-Healing Dashboard ================================================  Maps all workflow health into a single view.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/github_workflow_audit.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
