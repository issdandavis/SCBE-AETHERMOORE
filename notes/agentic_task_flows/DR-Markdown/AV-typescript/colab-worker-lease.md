---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "AV"
script_language: "TypeScript"
script_path: "scripts/system/colab_worker_lease.py"
source_sha256: "f2a10c9418381e7ef6c85750c30420901e9e77706a4765bac3ca03af5eb0b313"
---

# Colab Worker Lease

## Purpose

Provision a browser-backed Colab worker lease with HYDRA relay packets.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `AV`
- Script language lane: `TypeScript`
- Route reason: `browser`

## Command

```powershell
python scripts/system/colab_worker_lease.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
