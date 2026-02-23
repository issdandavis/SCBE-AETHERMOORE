# arXiv Automation Pipeline (SCBE-AETHERMOORE)

This pipeline creates a deterministic, CI-runnable arXiv submission package from repository documentation.

## What was added

- `scripts/arxiv_aggregate_docs.py` — collects repo docs into `aggregated_bundle.json`.
- `scripts/arxiv_synthesize_paper.py` — deterministic LaTeX draft synthesis from bundle.
- `scripts/arxiv_generate_manifest.py` — generates metadata manifest.
- `scripts/arxiv_bundle.py` — produces `arxiv-submission.tar.gz`.
- `scripts/arxiv_submit_playwright.py` — optional browser-assisted submit helper (dry-run safe).
- `.github/workflows/arxiv-paper-gen.yml` — CI workflow to generate and upload artifacts on tag `paper-v*` or manual run.

## Local usage

```bash
python scripts/arxiv_aggregate_docs.py --output artifacts/arxiv/aggregated_bundle.json
python scripts/arxiv_synthesize_paper.py --bundle artifacts/arxiv/aggregated_bundle.json --output artifacts/arxiv/paper.tex
python scripts/arxiv_generate_manifest.py --title "Hyperbolic Lattice Cross-Stitch: Geometric AI Governance with Post-Quantum Security" --authors "Issac Davis" --category "cs.CR" --output artifacts/arxiv/manifest.json
python scripts/arxiv_bundle.py --input-dir artifacts/arxiv --output artifacts/arxiv/arxiv-submission.tar.gz
```

Optional (requires Playwright + credentials):

```bash
python scripts/arxiv_submit_playwright.py --dry-run
# Remove --dry-run only when ARXIV_USER / ARXIV_PASS are set and final human review is ready.
```

## Security notes

- No credentials are hardcoded.
- Browser submission script requires explicit env vars (`ARXIV_USER`, `ARXIV_PASS`).
- Workflow generates artifacts only; it does not auto-submit to arXiv.

## AI-to-AI Retrieval Add-on

A retrieval service is now available for paper discovery and handoff packets:

- Module: `hydra/arxiv_retrieval.py`
- CLI: `python -m hydra arxiv search "query" --cat cs.AI --max 5`
- API service: `uvicorn scripts.arxiv_ai2ai_service:app --host 127.0.0.1 --port 8099`

This is designed to bridge research retrieval into drafting workflows before `arxiv_synthesize_paper.py`.
