---
title: The First Agent Product Surface Is a Local MCP
tags: [ai, mcp, governance, multiagent]
series: SCBE Research Notes
---
# The First Agent Product Surface Is a Local MCP

**By Issac Davis** | April 1, 2026

---

Most agent failures do not start with reasoning. They start with orientation drift. A model opens a large repo, guesses what matters, and then explains or executes against stale context.

The practical SCBE change this week is a local MCP surface for repo orientation:

- `scbe_system_manifest`
- `scbe_command_catalog`
- `scbe_reference_lookup`
- `scbe_tokenizer_health`

Those tools move repo identity, command lookup, and canonical document retrieval out of prompt memory and into a queryable operator surface.

That works well with the existing SCBE terminal control plane described in `docs/TERMINAL_OPS_QUICKSTART.md`.

The cleaner split is:

- MCP for orientation
- CLI for execution

That is the product boundary I trust more for multi-agent systems.

## Sources

- `mcp/scbe-server/README.md`
- `mcp/scbe-server/server.mjs`
- `docs/map-room/scbe_source_roots.md`
- `docs/TERMINAL_OPS_QUICKSTART.md`
- `skills/scbe-mcp-systems/SKILL.md`
- `CLAUDE.md`
