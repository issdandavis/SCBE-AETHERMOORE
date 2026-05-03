---
schema_version: "scbe_script_markdown_flow_v1"
card_tongue: "DR"
card_tongue_name: "Draumric"
card_language: "Markdown"
script_tongue: "CA"
script_tongue_name: "Cassisivadan"
script_language: "C"
script_path: "scripts/system/nightly_research_pipeline.py"
source_sha256: "2570418ee71d5143956a7022421aad6f403fce004fd893b4eba226dcea1a9c5c"
---

# Nightly Research Pipeline

## Purpose

SCBE Nightly Research Pipeline — Autonomous Research Agent  Runs on a schedule (default: 10PM-6AM local time) Phases every 2 hours:    10PM — Foreign news scan (Asia/Europe daytime news, emerging events)   12AM — American news digest (what happened today, evening/night stories)   2AM  — Category deep dives (AI safety, mechanistic interp, PQC, browser tech)   4AM  — Research article search (arXiv, Semantic Scholar, HuggingFace papers)   6AM  — Synthesis + SFT generation (spin data → training pairs)  Each phase:   1.

## Route

- Card tongue: `DR` (Draumric)
- Card language lane: `Markdown`
- Script tongue: `CA` (Cassisivadan)
- Script language lane: `C`
- Route reason: `c`

## Command

```powershell
python scripts/system/nightly_research_pipeline.py
```

## Agentic Use

- Read this card before invoking the script.
- Keep script execution evidence as a receipt.
- Do not paste the full script body into model context unless debugging requires it.
- Prefer this Markdown card as the compact DR structure packet for handoff.
