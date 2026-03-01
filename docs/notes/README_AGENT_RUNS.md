# SCBE Run Notes Index

This folder stores lightweight continuity notes for AI-to-AI operations.

- `agent_roundtable.py` writes:
  - `agent_roundtable_latest.md` (latest run summary)
  - one run directory under `artifacts/agent_roundtable/<run-id>/run.json`
  - one run directory under `artifacts/agent_roundtable/<run-id>/run.md`

- `money_ops_nightly.py` writes:
  - logs under `artifacts/money_ops/nightly/<timestamp>_money_ops_nightly.log`
  - latest summary under `artifacts/money_ops/nightly/latest.json`
  - optional markdown notes under `--note-dir` when provided

### Discovery
Any AI process can recover state by:
1. Reading this file first.
2. Reading `artifacts/agent_roundtable/*/run.json` for latest conversations.
3. Reading `artifacts/money_ops/nightly/latest.json` for last monetization run outcome.
4. Loading Obsidian workspace notes from `scripts/obsidian_ai_hub.py` if available.
