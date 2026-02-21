# SCBE-AETHERMOORE System CLI Guide

This CLI is the operational control point for the production system tools that were added for
self-improvement, notion/pipeline drift review, web intelligence, and lightweight antivirus checks.

## Entry Point

```bash
python scripts/scbe-system-cli.py --repo-root C:/Users/issda/SCBE-AETHERMOORE-working <command> [args]
```

`--repo-root` defaults to the current checkout and can usually be omitted.

## Commands

### `tongues ...`

Pass-through to `six-tongues-cli.py` (tokenizer + GeoSeal toolkit).

```bash
python scripts/scbe-system-cli.py tongues encode --tongue KO --in input.bin
python scripts/scbe-system-cli.py tongues decode --tongue KO --in <(printf "tok1 tok2 ...")
python scripts/scbe-system-cli.py tongues xlate --src KO --dst AV
python scripts/scbe-system-cli.py tongues blend --pattern KO:2,AV:1,DR:1 --in secret.txt
python scripts/scbe-system-cli.py tongues geoseal-encrypt --context "[0.2,-0.3,0.7]" --kem-key <base64> --dsa-key <base64> --in payload.bin
python scripts/scbe-system-cli.py tongues selftest
```

This command gives you the "core protocol CLI" from your technical spec.

### `notion-gap`

Run the Notion/pipeline gap audit used in the self-improvement loop.

```bash
python scripts/scbe-system-cli.py notion-gap \
  --sync-config scripts/sync-config.json \
  --pipeline-config training/vertex_pipeline_config.yaml \
  --training-data training-data
```

Outputs:
- `artifacts/notion_pipeline_gap_review.json`
- `artifacts/notion_pipeline_gap_review.md`

### `self-improve`

Run mode-based task synthesis from coherence/gap artifacts.

```bash
python scripts/scbe-system-cli.py self-improve --mode all
python scripts/scbe-system-cli.py self-improve --mode fine-tune-funnel --run-gap
```

If `--run-gap` is passed, this command executes the gap review first and then runs the orchestrator with that report.

Outputs:
- `artifacts/self_improvement_manifest.json`
- `artifacts/self_improvement_summary.md`

### `web search` and `web capture`

```bash
python scripts/scbe-system-cli.py web --engine auto search --query "SICA self-improving coding agent arxiv"
python scripts/scbe-system-cli.py web --engine auto capture --url "https://duckduckgo.com"
```

Outputs are written under `artifacts/web_tool`.

### `antivirus`

Run quick static safety scan for high-signal issues.

```bash
python scripts/scbe-system-cli.py antivirus
```

Outputs:
- `artifacts/agentic_antivirus_report.json`
- `artifacts/agentic_antivirus_report.md`

### `status`

Quick artifact presence check:

```bash
python scripts/scbe-system-cli.py status
```

### `pollypad` (Agent personal “Kindle” storage)

Create and manage per-agent personal pads for notes, books, and utilities.

```bash
# Create a pad for one agent
python scripts/scbe-system-cli.py pollypad init --agent-id agent-001 --name "Rex Codex" --role CODER --owner "Isaac"

# Add notes and list them
python scripts/scbe-system-cli.py pollypad note add --agent-id agent-001 --title "Mission Notes" --text "Start from trust radius checks first."
python scripts/scbe-system-cli.py pollypad note list --agent-id agent-001

# Add a book file into the pad
python scripts/scbe-system-cli.py pollypad book add --agent-id agent-001 --title "Operations" --path "./notes/ops.md"

# Install and list agent apps/utilities
python scripts/scbe-system-cli.py pollypad app install --agent-id agent-001 --name "scbe-checker" --entrypoint "python scbe.py check" --description "Local validation utility"
python scripts/scbe-system-cli.py pollypad app list --agent-id agent-001

# Export a snapshot for handoff/sync
python scripts/scbe-system-cli.py pollypad snapshot --agent-id agent-001
```

Pads are stored under `.scbe/polly-pads/<agent-id>/`:
- `manifest.json`
- `notes/`
- `books/`
- `apps/`

### `agent` (Squad Orchestration)

Create and use a small AI squad from the CLI. This is the "call my agents like Codex" path.

```bash
# Bootstrap default squad (Codex + NotebookLM)
python scripts/scbe-system-cli.py agent bootstrap

# Register a custom OpenAI agent
python scripts/scbe-system-cli.py agent register \
  --agent-id code-reviewer \
  --provider openai \
  --display-name "Code Reviewer" \
  --description "Specialized for PR review" \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY

# List squad members
python scripts/scbe-system-cli.py agent list

# Quick ping everyone in registry
python scripts/scbe-system-cli.py agent ping --max-tokens 64

# Run one agent with prompt text
python scripts/scbe-system-cli.py agent call \
  --agent-id codex \
  --prompt "Give a 3-step plan to harden an API endpoint against replay risk."

# Broadcast to all enabled agents and save artifacts
python scripts/scbe-system-cli.py agent call --all --show-output --output-dir artifacts/agent_calls
```

Agent calls are stored in `artifacts/agent_calls/`:
- `codex_agent_call.json`
- `notebooklm-main_agent_call.json` (manual fallback artifact)
- `agent_call_summary.json`

Notes:
- `agent bootstrap --append` keeps existing entries and adds defaults.
- `agent bootstrap --force` replaces current registry.
- `agent register` supports `openai` and `notebooklm` provider entries.

## Mapping to Your Notes + Workflow

- The `notion-gap` + `self-improve` path is the implementation of your **notion-to-pipeline gap triage**.
- `tongues` is the concrete CLI for the **Six Tongues + GeoSeal** spec.
- `web` and `antivirus` provide the **agentic tool layer** for environment-scope automation and safety triage.
- `status` aligns with the `.scbe/next-coder-marker.md` handoff flow.
- `pollypad` aligns with your “Kindle for AI” concept (agent-local note/books/app bundle with manifest).

## Suggested Daily Run Sequence

1. `status`
2. `self-improve --run-gap`
3. `tongues selftest`
4. `web search --query "<topic>"` (as needed)
5. `antivirus`
6. `pollypad list`
7. `pollypad snapshot --agent-id <id>`

If any `CRITICAL`/`HIGH` items remain, pause release actions and fix before scheduling deployment workflows.
