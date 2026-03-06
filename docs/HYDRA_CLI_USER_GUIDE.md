# HYDRA CLI User Guide

This guide covers the local HYDRA command-line interface for orchestration, memory, research, and switchboard operations.

## 1. What HYDRA CLI helps with

Use HYDRA CLI when you want to:

- run governed agent actions from terminal JSON packets,
- run multi-agent research (`httpx`, local browser, or cloud worker mode),
- store and recall lightweight memory facts,
- coordinate role-based tasks/messages through switchboard,
- query arXiv and generate related-work outlines from terminal,
- run branching workflow exploration with council path recommendations.

## 2. Install a global `hydra` command (Windows)

From repo root:

```powershell
.\scripts\install_hydra_cli.ps1
```

Then open a new terminal and verify:

```powershell
hydra --help
```

Notes:
- The installer writes shims to `$HOME\.scbe\bin\hydra.ps1` and `hydra.cmd`.
- It updates user PATH unless `-NoPathUpdate` is provided.

## 3. Quick start

```powershell
hydra status
hydra stats
hydra --json status
```

Run a direct action:

```powershell
hydra execute "{\"action\":\"navigate\",\"target\":\"https://example.com\"}"
```

Or pipe JSON (auto-routes to `execute` when no command is provided):

```powershell
echo '{"action":"navigate","target":"https://example.com"}' | hydra
```

## 4. Command reference

### Core

```powershell
hydra status
hydra stats
hydra execute "<json-object>"
```

### Research

```powershell
hydra research "quantum computing 2025"
hydra research "AI safety" --mode httpx
hydra research "AI safety" --mode local --providers claude,gpt
hydra research "AI safety" --max-subtasks 3 --discovery 4
```

### Workflow templates

```powershell
hydra workflow list
hydra workflow show <name>
hydra workflow run <name>
hydra workflow save <name> "{\"phases\": [...], \"description\": \"...\"}"
```

### Memory

```powershell
hydra remember objective "ship AetherBrowse reliability patch"
hydra recall objective
hydra search reliability patch
```

### arXiv retrieval

```powershell
hydra arxiv search "hyperbolic governance" --cat cs.AI --max 5
hydra arxiv get 2501.00001v1,2501.00002
hydra arxiv outline "multi-agent retrieval" --cat cs.AI --max 8
```

### Canvas workflows

```powershell
hydra canvas list
hydra canvas show full_loop
hydra canvas run full_loop --topic "swarm navigation"
hydra canvas run article --topic "AI governance" --steps 8
```

### Branch workflows

```powershell
hydra branch list
hydra branch show research_pipeline --topic "swarm systems"
hydra branch run research_pipeline --topic "swarm systems" --strategy all_paths
hydra branch run training_funnel --strategy scored --providers claude,gpt,gemini
hydra branch run content_publisher --export-n8n workflows/n8n/branch.workflow.json
```

### Switchboard

```powershell
hydra switchboard stats
hydra switchboard enqueue pilot "{\"action\":\"navigate\",\"target\":\"https://example.com\"}"
hydra switchboard post researcher "new task packet posted"
hydra switchboard messages researcher 0
```

## 5. Helpful flags

- `--json` returns machine-readable JSON output where supported.
- `--no-banner` disables startup banner in interactive mode.
- `--version` prints CLI version.
- `--mode`, `--providers`, `--max-subtasks`, `--discovery` tune research behavior.
- branch tuning: `--strategy`, `--max-paths`, `--max-depth`, `--context`, `--export-n8n`, `--export-choicescript`.

## 6. Fast Research Presets

Quick command patterns for live research loops:

```powershell
hydra arxiv search "AI safety" --cat cs.AI --max 3
hydra research "autonomy market update" --mode httpx --max-subtasks 2 --discovery 3
hydra switchboard stats
hydra remember stripe_live true
hydra recall stripe_live
```

Install shortcut aliases:

```powershell
.\scripts\install_hydra_quick_aliases.ps1
```

Aliases added to your PowerShell profile:
- `hstatus`
- `hresearch <topic>`
- `harxiv <topic>`
- `hqueue`

## 7. Aliases

These aliases are supported:

- `st` -> `status`
- `statistics` -> `stats`
- `exec` -> `execute`
- `wf` -> `workflow`
- `sb` -> `switchboard`
- `cv` / `paint` -> `canvas`
- `br` -> `branch`

## 8. Troubleshooting

- `Unknown command`: run `hydra --help`; CLI now suggests close command names.
- `Invalid JSON`: ensure payload is valid JSON object (`{...}`), not an array/string.
- `python not found`: install Python 3.11+ and ensure `python` is on PATH.
- `hydra not recognized`: re-open terminal after running install script, or run `.\scripts\hydra.ps1 --help`.

## 9. Can this help your workflow?

Yes, if your flow is terminal-first and automation-heavy. HYDRA CLI is strongest at:

- fast orchestration loops (status, execute, switchboard),
- repeatable research collection/synthesis,
- auditable command history and structured memory usage,
- integrating JSON-based packets from other agents/tools,
- evaluating multiple workflow branches before picking one production path.

For GUI-heavy browser tasks, keep using AetherBrowse directly and use HYDRA CLI as the backend control surface.
