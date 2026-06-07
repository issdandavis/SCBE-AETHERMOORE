# SCBE Operator Experience Plan

Status: research-applied planning surface, 2026-05-09.

SCBE already has unusually deep governance, cryptography, and multi-agent
architecture. The next user-experience step is to make that depth feel like a
single command center instead of many scripts.

This document translates current agent CLI patterns into SCBE-specific product
work. It is intentionally separate from the active `scbe-shell` implementation
lane so it can be routed, reviewed, and merged without colliding with CLI code.

## Research Inputs

The strongest current patterns across Codex CLI, Claude Code, GitHub Copilot
CLI, and similar agent shells are:

- One command starts the daily-driver shell.
- Slash commands expose repeatable workflows.
- Status surfaces show model, account, connectivity, token/cost, and runtime
  state.
- Session resume makes the agent feel continuous.
- Tool output streams visibly, with a way to interrupt or redirect.
- Cloud/background agent tasks resolve into pull requests or reviewable
  artifacts.
- Hooks/guards run before and after tool use.
- Skills or custom commands are stored as files, not hardcoded UI branches.

References:

- Claude Code slash commands: https://docs.claude.com/en/docs/claude-code/slash-commands
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- GitHub Copilot CLI overview: https://docs.github.com/copilot/concepts/agents/copilot-cli/about-copilot-cli
- GitHub Copilot CLI usage: https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-agents/overview
- OpenAI Codex CLI getting started: https://help.openai.com/en/articles/11096431-openai-codex-cli-getting-started
- Hermes Agent docs: https://hermes-agent.nousresearch.com/docs/

## SCBE Product Shape

The target experience is:

```text
scbe
  /status
  /workspace new
  /search
  /providers
  /liboqs
  /gate
  /ship
```

The user should not need to know which repo script, Python module, Vercel
endpoint, or workflow file backs a command. The shell should show the route and
receipt after the action completes.

## Visible Receipts

SCBE should preserve the feeling of progress by printing simple pass/fail
markers for important gates. Examples:

```text
SCBE_LIBOQS_PASS=1
SCBE_STORAGE_EXPORT_READY=1
SCBE_WORKSPACE_OFFLOAD_PASS=1
SCBE_GATE_ALLOW=1
SCBE_BIJECTIVE_TAMPER_SIGNAL=1
```

Rules:

- A `*_PASS=1` marker only prints after the underlying proof succeeds.
- A failed gate prints a named failure marker and a short reason.
- Receipts should also be written into `20_receipts` in bus workspaces.
- Receipts should be friendly enough for a user and exact enough for CI logs.

## Workspace Formation

The bus workspace formation is the user-facing storage shape:

```text
.aethermoor-bus/workspaces/<workspace-id>/
  00_inbox/
  10_work/
  20_receipts/
  30_exports/
  40_refs/
  90_tmp/
```

The shell and mobile app should present this as:

- Inbox: stuff you gave the bus.
- Work: what the agents are editing.
- Receipts: proof and governance.
- Exports: what you can send, download, or sell.
- References: safe source material.
- Temporary: scratch that can be deleted.

## Free-First Provider UX

SCBE should expose provider state as a router, not as a list of API keys.

Default order:

1. Local Ollama or local model if available.
2. Zero-credit public search and browser extraction.
3. Browser/local download storage.
4. User-designated GitHub, Dropbox, OneDrive, or Google Drive handoff.
5. GitHub agent task / Codespaces when useful and within budget.
6. Hugging Face, Kaggle, or Colab free lanes when configured.
7. Paid APIs only when explicitly enabled.

The shell should show:

```text
Mode: local-first
Cost: zero-credit
Fallback: GitHub Agent Task available
Budget: protected
```

No account-stacking or limit evasion. The system should use free tiers hard,
cache aggressively, batch work, and fall back cleanly.

## Mission-Control Flow

The long-term interaction model:

```text
Task
  -> Route
  -> Workspace
  -> Agent lane
  -> Receipts
  -> Export or pull request
  -> Review
  -> Ship
```

This maps the Hydra metaphor into concrete UX:

- Heads are agent lanes.
- Tentacles are tool/provider routes.
- Receipts are the nervous system.
- Workspaces are the body cavities where work happens before shipping.
- GitHub PRs, app bundles, and export packets are the shipping surfaces.

## Priority Backlog

1. `scbe /status`
   - Show current repo, branch, dirty state, provider mode, last CI state, and
     active workspace.

2. `scbe /liboqs`
   - Run the native smoke gate and print `SCBE_LIBOQS_PASS=1` on success.

3. `scbe /workspace new`
   - Create the bus formation locally and write a manifest.

4. `scbe /workspace export <stop>`
   - Package `20_receipts`, `30_exports`, and selected `40_refs` for
     `local_download`, `github`, `dropbox`, `onedrive`, or `gdrive`.

5. `scbe /providers`
   - Show available local/free/cloud providers and budget posture.

6. `scbe /ship`
   - Build a customer handoff packet from `30_exports` plus receipts.

7. `scbe /agent-task`
   - Create a GitHub agent task and track the resulting PR/session as a spoke.

## Done Definition

This plan is successful when a non-coding user can:

1. Open `scbe`.
2. See system status.
3. Start a workspace.
4. Ask for research or a build task.
5. Watch receipts appear.
6. Export the result to a known storage stop.
7. Verify what shipped.

The goal is not to hide SCBE's depth. The goal is to make the depth navigable.
