# Headless-First Research Spine Pipeline

Date: 2026-03-03  
Status: active execution plan

## Mission

Build a headless-first research system that retrieves high-signal data from arXiv, Google-discovered web sources, government domains, and niche sites, then converts governed outputs into an LLM-ready research spine.

## Pipeline Pseudo Anatomy

1. Discovery Layer
- Sources:
  - Google News RSS discovery via `scripts/web_research_training_pipeline.py`
  - arXiv/gov/niche seed URLs via `--urls-file`
- Output:
  - `training/runs/web_research/<run_id>/discovered_urls.json`

2. Headless Retrieval Layer
- Engine:
  - `scripts/hydra_headless_mmx_coordinator.py`
  - Browser backends: `playwright|selenium|chrome_mcp|cdp`
- Behavior:
  - parallel tab fan-out
  - antivirus scan + matrix reduction per URL
- Output:
  - `training/runs/web_research/<run_id>/hydra_scan.json`

3. Governance Reduction Layer
- Decision classes:
  - `ALLOW | QUARANTINE | DENY`
- Records:
  - `curated_allowed.jsonl`
  - `curated_quarantine.jsonl`
  - `audit.json`
  - `decision_record.json`

4. LLM Spine Intake Layer
- Base spine file:
  - `training/intake/web_research/web_research_<run_id>.jsonl`
- Canonical event:
  - `event_type=web_research_chunk`

5. Obsidian Nodal Logging Layer
- Auto-written per run by `scripts/web_research_training_pipeline.py`:
  - `AI Workspace/Nodal Network/<YYYYMMDD>/node-web-research-<run_id>.md`
  - `AI Workspace/Nodal Network/Network Index.md`
  - `AI Workspace/Nodal Network/Edge Ledger.md`
  - `AI Workspace/Cross Talk.md` append

## Source Tiering Policy

1. Tier 0: solved memory and prior route cache.
2. Tier 1: laminar trusted sources (official docs/repos/reference sites).
3. Tier 2: structured research pools (curated technical/regulatory sources).
4. Tier 3: turbulent wild-web findings held in quarantine until validated.

## First-Run Commands

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
python -m pip install playwright
playwright install chromium
.\scripts\system\run_headless_research_spine.ps1 -Backend playwright -MaxTabs 8 -MaxPerTopic 8
```

Optional custom topic set:

```powershell
.\scripts\system\run_headless_research_spine.ps1 `
  -Topics "site:arxiv.org trusted AI identity", "site:.gov AI safety standards", "niche agent governance frameworks" `
  -Query "federal and academic AI governance evidence"
```

## Implementation Anchors

- `scripts/web_research_training_pipeline.py`
- `scripts/system/run_headless_research_spine.ps1`
- `scripts/hydra_headless_mmx_coordinator.py`
- `src/browser/headless.py`
- `src/browser/research_funnel.py`
- `scripts/cloud_kernel_data_pipeline.py`
