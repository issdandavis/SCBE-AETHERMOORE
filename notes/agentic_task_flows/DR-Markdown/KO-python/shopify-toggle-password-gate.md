---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/shopify_toggle_password_gate.py"
source_sha256: "a3b63e817081030bb4b0615dbf6f6efb999c4aa1d6efe490c6bc31f7eb681901"
---

# Shopify Toggle Password Gate

## Purpose

Inspect or toggle Shopify storefront password protection via Playwright.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/shopify_toggle_password_gate.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
