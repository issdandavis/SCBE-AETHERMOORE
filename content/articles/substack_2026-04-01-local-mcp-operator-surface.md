---
title: The First Agent Product Surface Is a Local MCP
tags: [ai, mcp, governance, multiagent]
series: SCBE Research Notes
---
# The First Agent Product Surface Is a Local MCP

**By Issac Davis** | April 1, 2026

---

Most agent teams still fail in the same boring way: they get lost before they get useful. The models are not always the weak point. The weak point is orientation. Someone opens a large repo, guesses which subsystem matters, invents a command from memory, and only later finds out that the right entrypoint was already there.

The useful SCBE change this week is that repo orientation is becoming a local MCP surface instead of a vibe.

## What changed

The local server documented in `mcp/scbe-server/README.md` now exposes explicit discovery tools:

- `scbe_system_manifest`
- `scbe_command_catalog`
- `scbe_reference_lookup`
- `scbe_tokenizer_health`

That tool set matters because it turns orientation into a protocol.

Instead of hoping the assistant remembers the repo, the operator can ask:

1. Is the service alive?
2. What repo and tool surface am I actually in?
3. Which command lane is real?
4. Which document is canonical before I explain this concept?

## Why this is the right product boundary

The older pattern was prompt memory. That works until the context thins out. Then the assistant starts talking confidently about tokenizer geometry, Sacred Eggs, training stack details, or command entrypoints without checking whether the implementation and the docs still match.

SCBE has a direct answer to that problem now. `docs/map-room/scbe_source_roots.md` explicitly says it should be used as the first re-anchor point when a session starts drifting or when partial context makes established components sound speculative.

That is the point. If drift is predictable, anti-drift infrastructure should be explicit.

## MCP for orientation, CLI for execution

The repo also already has a terminal control surface. `docs/TERMINAL_OPS_QUICKSTART.md` describes one CLI for connector setup, goal submission, and high-risk approval.

That means the split can stay clean:

- MCP for orientation and canonical lookup
- CLI for execution

That is a better operator pattern than asking one giant assistant prompt to do both jobs.

## What is implemented now

- a local MCP surface for SCBE discovery
- a source-roots map for re-anchoring
- a terminal control plane for execution
- repo instructions that tell agents to use MCP before shell guessing

## What is not implemented yet

- live automation for every publication or external platform
- a complete runtime-entrypoint map for every subsystem
- full connector coverage across every lane

That distinction matters. The honest claim is not that the problem is solved. The honest claim is that the repo now has the right first boundary for reliable agent operations.

## Sources

- `mcp/scbe-server/README.md`
- `mcp/scbe-server/server.mjs`
- `docs/map-room/scbe_source_roots.md`
- `docs/TERMINAL_OPS_QUICKSTART.md`
- `skills/scbe-mcp-systems/SKILL.md`
- `CLAUDE.md`
