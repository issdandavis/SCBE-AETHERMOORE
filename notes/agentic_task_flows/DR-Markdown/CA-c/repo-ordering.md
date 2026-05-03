---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "CA"
script_language: "C"
script_path: "scripts/system/repo_ordering.py"
source_sha256: "df2aadf937a8048c0e2f34a69d6b43d92fb655333cb2cc90d5a6da499ca22040"
---

# Repo Ordering

## Purpose

Agentic task flow wrapper for repo_ordering.py.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `CA`
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/repo_ordering.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
