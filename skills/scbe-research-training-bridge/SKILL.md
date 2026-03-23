---
name: scbe-research-training-bridge
description: Stage arXiv evidence and Obsidian markdown into source-grounded Hugging Face training bundles for research, review, and later SFT runs.
---

# SCBE Research Training Bridge

## Purpose

Use this skill when research material already exists as:
- AetherBrowser or Playwright arXiv evidence JSON in `artifacts/page_evidence/`
- Obsidian or repo markdown notes that should become training inputs
- source-grounded bundles for later Hugging Face SFT work

This skill stages evidence, copies the source files into a deterministic bundle, writes `research_corpus.jsonl`, and emits a lightweight Hugging Face training handoff manifest.

## Workflow

1. Confirm the source lanes.
- arXiv evidence: `artifacts/page_evidence/playwriter-arxiv.org-*.json`
- markdown notes: repo notes or exported Obsidian markdown

2. Build the bundle.
- Default run:
  - `python scripts/system/research_training_bridge.py --json`
- With explicit note roots:
  - `python scripts/system/research_training_bridge.py --note-input "C:\path\to\vault" --note-input "docs\research" --json`
- With the active Obsidian vault:
  - `python scripts/system/research_training_bridge.py --use-active-vault --vault-subdir "SCBE Research" --json`

3. Review the outputs.
- `training-data/research_bridge/<bundle>/research_corpus.jsonl`
- `training-data/research_bridge/<bundle>/source_manifest.json`
- `training-data/research_bridge/<bundle>/hf_training_manifest.json`
- `training-data/research_bridge/<bundle>/bundle_report.md`

4. Hand off to the training lane.
- Use the generated `hf_training_manifest.json` with `$hugging-face-model-trainer`
- Keep the bundle source-grounded; do not invent synthetic claims before review

## Rules

- Prefer `arxiv.org/abs/...` evidence over raw PDFs for compact metadata capture.
- Never rewrite source markdown in-place; copy it into the bundle.
- Keep the bundle deterministic and reviewable.
- Treat the bridge as a staging layer, not the final dataset merge.
- Use `--vault-subdir` to keep active-vault ingestion scoped to the folders you actually want.

## Good Triggers

- "Turn these arXiv pulls and vault notes into training data."
- "Make a Hugging Face-ready bundle from tonight's research."
- "Stage markdown notes for source-grounded SFT."
- "Build a review packet before we fine-tune the model."
