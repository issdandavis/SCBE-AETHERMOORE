# Self-Improvement Agents

This repository now includes a repo-native self-improvement loop that emits actionable tasks
for your CI, training, and Notion/Hugging Face flow.

## What was added

- `scripts/self_improvement_orchestrator.py`
  - Implements three modes:
    - `code-assistant`
    - `ai-nodal-dev-specialist`
    - `fine-tune-funnel`
- `scripts/notion_pipeline_gap_review.py` (new)
  - Reviews Notion sync + notion exports + fine-tune pipeline configuration.
  - Produces actionable tasks for missing exports, stream imbalance, and config mismatch.
- `scripts/agentic_web_tool.py` (new)
  - Agentic web/search helper with optional Playwright capture.
  - Supports `search` and `capture` commands with JSON artifacts.
- `scripts/agentic_antivirus.py` (new)
  - Lightweight repo antivirus pass for suspicious patterns and token leaks.
  - Produces risk score, severity counts, and summary markdown.
- `scripts/agentic_aetherauth.py` (new)
  - Geometric, context-bound access gate with trust rings:
    - `core` (full access), `outer` (read-only), `blocked` (deny/fail-to-noise).
  - Verifies optional HMAC signature against context for tighter envelope-style access control.
- `training/vertex_pipeline_config.yaml`
  - Adds `fine_tune` section with a dual-stream (technical / isekai-emotive) funnel.
- `.github/workflows/self-improvement-loop.yml`
  - Nightly + manual orchestration workflow with optional issue creation.
  - Supports `--notion-gap-report` from gap review artifact.
- `.github/workflows/notion-to-dataset.yml`
  - Adds `notion_pipeline_gap_review` generation and artifact upload.
- `docs/AGENTS.md` and `.scbe/next-coder-marker.md` updates for handoff visibility.

## Artifacts

- `artifacts/self_improvement_manifest.json`
- `artifacts/self_improvement_summary.md`
- `artifacts/fine_tune_funnel_manifest.json`
- `artifacts/fine_tune_funnel_summary.md`
- `artifacts/notion_pipeline_gap_review.json`
- `artifacts/notion_pipeline_gap_review.md`
- `artifacts/agentic_antivirus_report.json`
- `artifacts/agentic_antivirus_report.md`
- `artifacts/aetherauth_decision.json`
- `artifacts/aetherauth_decision.md`
- `artifacts/web_tool/*.json`
- `artifacts/web_tool/*.png` (Playwright screenshots when available)

## Workflow usage

### Run all modes

`workflow_dispatch` input: `mode=all`

### Run only one mode

Use `mode=code-assistant`, `mode=ai-nodal-dev-specialist`, or `mode=fine-tune-funnel`.

### Run gap review standalone

```bash
python scripts/notion_pipeline_gap_review.py \
  --output artifacts/notion_pipeline_gap_review.json \
  --summary-path artifacts/notion_pipeline_gap_review.md
```

### Use web tool (search + capture)

```bash
python scripts/agentic_web_tool.py search --query "SCBE Notion API" --output-dir artifacts/web_tool
python scripts/agentic_web_tool.py capture --url "https://github.com" --output-dir artifacts/web_tool
```

### Run antivirus pass

```bash
python scripts/agentic_antivirus.py \
  --repo-root C:/Users/issda/SCBE-AETHERMOORE-working \
  --output artifacts/agentic_antivirus_report.json \
  --summary artifacts/agentic_antivirus_report.md

Use GeoSeal trust mode for phase/ring style quarantine telemetry:

```bash
python scripts/agentic_antivirus.py \
  --repo-root C:/Users/issda/SCBE-AETHERMOORE-working \
  --geoseal \
  --ring-core 0.70 \
  --ring-outer 0.45 \
  --output artifacts/agentic_antivirus_report.json \
  --summary artifacts/agentic_antivirus_report.md
```

### Run AetherAuth decision check

```bash
python scripts/agentic_aetherauth.py \
  --action update_secret \
  --context-json '{"time":1707700000000,"latitude":47.25,"longitude":-122.4,"cpu":19.3,"memory":61.0,"intent":0.74,"history":0.58}' \
  --reference-vector "0.0,0.0,0.0,0.0,0.0,0.0" \
  --output artifacts/aetherauth_decision.json \
  --summary artifacts/aetherauth_decision.md
```

For a fail-to-noise deny, the output includes a `noise` field and `decision=DENY`.
```

### Notes

- `pipeline-config` parsing in the self-improvement orchestrator is dependency-light:
  - tries `pyyaml` if available
  - falls back to minimal parser for `fine_tune` stream metadata
- `mode=all` in self-improvement loop can include notion-gap tasks when a gap report is provided.
