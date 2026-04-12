---
name: aetherbrowse-logs
description: View and analyze AetherBrowse governance logs, run history, search queries, and cost tracking
argument-hint: "[governance|runs|search|cost|all] [--tail N]"
allowed-tools:
  - Bash
  - Read
  - Grep
---

View AetherBrowse operational logs. Specify a log type or use `all` for a summary across all logs.

## Instructions

1. Parse the argument to determine which log(s) to show. Default to `all` if no argument given. The `--tail N` flag controls how many recent entries to show (default 10).

2. For each requested log type, read the corresponding file:

   - **governance**: `artifacts/aetherbrowse/governance.jsonl` — governance decisions (ALLOW/QUARANTINE/DENY)
   - **runs**: `artifacts/agent_comm/aetherbrowse/runs.jsonl` — plan execution history
   - **search**: `artifacts/agent_comm/aetherbrowse/search_queries.jsonl` — search query log
   - **cost**: `artifacts/aetherbrowse/cost_log.jsonl` — LLM cost tracking
   - **hydra**: `artifacts/aetherbrowse/hydra_usage.jsonl` — Hydra Armor API usage
   - **training**: `training-data/aetherbrowse/governance_pairs.jsonl` — SFT training pairs generated

3. For `all` mode, show a brief summary of each log:
   - Total entries in each file
   - Last 3 entries from governance and runs
   - Total search queries today
   - Cost summary if cost log exists

4. Format the output as a readable table or summary. Parse JSON entries and present key fields (timestamp, decision, status, query, etc.).

5. If a log file doesn't exist yet, note it as "No data yet" rather than erroring.
