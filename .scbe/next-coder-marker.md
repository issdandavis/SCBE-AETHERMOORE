# Self-Improvement Next-Coder Marker

Last updated by the self-improvement agent loop setup.

Run sequence for next maintenance cycle:
1. Open `artifacts/self_improvement_manifest.json` and `artifacts/notion_pipeline_gap_review.json`.
2. Triage all `critical` tasks first, then `high`.
3. Confirm `training/vertex_pipeline_config.yaml` still expresses funnel stream goals.
4. Confirm `scripts/notion_pipeline_gap_review.py` has no new blockers.
5. Confirm `scripts/agentic_web_tool.py` outputs exist under `artifacts/web_tool`.
6. Confirm `scripts/agentic_antivirus.py` risk levels are acceptable.
7. Run `.github/workflows/self-improvement-loop.yml` with `mode=all` after each change.

Modes available:
- `code-assistant`: converts reliability signals to patch tasks
- `ai-nodal-dev-specialist`: maps tasks to execution lanes
- `fine-tune-funnel`: checks dual technical/emotional stream health for training
