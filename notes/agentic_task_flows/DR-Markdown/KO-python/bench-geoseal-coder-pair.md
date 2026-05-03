---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_language: "Markdown"
script_tongue: "KO"
script_language: "Python"
script_path: "scripts/system/bench_geoseal_coder_pair.py"
source_sha256: "019acb3842be0f1aae833b07eae04fbaddc21391adf9bac014882314bfb7e8c1"
---

# Bench Geoseal Coder Pair

## Purpose

Side-by-side benchmark: scbe-geoseal-coder:q8 vs qwen2.

## Route

- Card tongue: `DR`
- Card language lane: `Markdown`
- Script tongue: `KO`
- Script language lane: `Python`
- Route reason: `trit-aggregate`

## Command

```powershell
python scripts/system/bench_geoseal_coder_pair.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
