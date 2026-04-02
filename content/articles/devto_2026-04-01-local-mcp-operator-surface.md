---
title: The First Agent Product Surface Is a Local MCP
tags: [ai, mcp, governance, multiagent]
series: SCBE Research Notes
---
# The First Agent Product Surface Is a Local MCP

**By Issac Davis** | April 1, 2026

---

Most agent failures do not start with bad model weights. They start with bad orientation. A team opens a large repo, guesses which subsystem matters, invents a command from memory, and only later discovers that the real entrypoint was somewhere else.

The useful SCBE shift this week is a small one: repo orientation is moving into a local MCP surface with explicit tools for health, manifest discovery, command lookup, and canonical document search.

## What the repo already proves

The local server in `mcp/scbe-server/README.md` now exposes more than tokenizer and governance helpers. It exposes system discovery tools:

- `scbe_system_manifest`
- `scbe_command_catalog`
- `scbe_reference_lookup`
- `scbe_tokenizer_health`

Those tools answer four practical questions:

1. Is the service alive?
2. What repo and tool surface am I actually standing in?
3. What command lane is real?
4. Which document is canonical for the concept I am about to explain?

That is a better operator surface than asking the model to remember the repo.

## Why this matters

The usual alternative is prompt memory. That works until it does not. An agent starts speaking confidently about tokenizer geometry, Sacred Eggs, or command entrypoints before checking whether the implementation and the docs still match.

SCBE now has a better posture because the repo includes an explicit anti-drift root map. `docs/map-room/scbe_source_roots.md` says it should be used as the first re-anchor point when a session starts drifting or when partial context makes established components sound speculative.

That is the correct pattern:

- explicit root map
- explicit manifest
- explicit command catalog
- explicit canonical-doc lookup

## Why this pairs well with the CLI

SCBE also already has a terminal control surface. `docs/TERMINAL_OPS_QUICKSTART.md` describes one CLI for connector setup, goal submission, and high-risk approval flow.

The clean split is:

- MCP for orientation
- CLI for execution

That is more reliable than one giant prompt trying to do both jobs.

## Implemented versus proposed

Implemented now:

- local SCBE MCP server with discovery tools
- a source-roots anti-drift map
- a terminal control surface for execution
- repo instructions telling agents to start with MCP before shell guessing

Still not finished:

- live automation lanes for every platform
- a complete runtime-entrypoint map for every subsystem
- full connector coverage

The honest claim is not that SCBE solved agent ops. The honest claim is that the repo now has the right product boundary for orientation.

## Sources

- `mcp/scbe-server/README.md`
- `mcp/scbe-server/server.mjs`
- `docs/map-room/scbe_source_roots.md`
- `docs/TERMINAL_OPS_QUICKSTART.md`
- `skills/scbe-mcp-systems/SKILL.md`
- `CLAUDE.md`
