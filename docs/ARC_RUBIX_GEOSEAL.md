# ARC Rubix GeoSeal Loop

This lane turns the NeuroGolf/ARC lesson into a reusable local harness:
deterministic scripts do the repetitive work, and LLM calls are reserved for
short review notes.

## Commands

```powershell
node bin/geoseal.cjs arc-solve --json
node bin/geoseal.cjs arc-score --json
node bin/geoseal.cjs arc-dashboard --json
node bin/geoseal.cjs arc-loop --mode eval --iterations 1 --json
node bin/geoseal.cjs arc-loop --mode eval --ollama --ollama-model openclaw:latest --json
```

## Outputs

- `C:\Users\issda\kaggle\arc_agi2_2026\eval_submission.json`
- `C:\Users\issda\kaggle\arc_agi2_2026\submission.json`
- `C:\Users\issda\kaggle\arc_agi2_2026\arc_rubix_report.json`
- `C:\Users\issda\kaggle\arc_agi2_2026\arc_rubix_dashboard.html`
- `C:\Users\issda\kaggle\arc_agi2_2026\arc_rubix_loop_receipt.json`
- `C:\Users\issda\kaggle\arc_agi2_2026\arc_rubix_ollama_notes.md`

## Operating model

The loop is intentionally simple:

1. `arc_rubix_solver.py` applies compact rule templates to ARC challenge files.
2. `arc_rubix_score.py` scores visible evaluation submissions when solutions are present.
3. `arc_rubix_dashboard.py` renders a local HTML inspection board.
4. `arc_rubix_loop.py` coordinates the run, writes a receipt, and optionally asks Ollama for cheap local review notes.

The solver is not meant to be the final ARC system. It is the stable stencil:
add exact rule templates, run the local loop, inspect the dashboard, and only
spend cloud model tokens on decisions that need broader reasoning.
