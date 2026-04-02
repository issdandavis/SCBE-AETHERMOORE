---
name: scbe-mcp-systems
description: Use the local SCBE MCP service as the first orientation and discovery layer for SCBE-AETHERMOORE work. Trigger when Codex needs to identify which SCBE system is relevant, find repo-backed command lanes, locate canonical docs for tokenizer/triadic/geometry/training/Sacred Eggs topics, confirm SCBE MCP health, or avoid guessing about SCBE internals before coding.
---

# SCBE MCP Systems

## Overview

Use the SCBE MCP server before shell probing when the task is about SCBE repo orientation, command discovery, or canonical document lookup. Keep the first pass inside MCP so repo identity, commands, and source-of-truth docs come from the service instead of memory.

## Workflow

1. Confirm the server is live.
Call `mcp__scbe__scbe_tokenizer_health` when MCP health is uncertain or the user is troubleshooting SCBE connectivity.

2. Orient to the repo.
Call `mcp__scbe__scbe_system_manifest` at the start of SCBE system work. Use it to identify the repo identity, available MCP tools, command areas, and canonical documents.

3. Resolve the command lane before suggesting or running commands.
Call `mcp__scbe__scbe_command_catalog` with an `area` when the user needs build, test, MCP, Docker, browser, system, skills, or publish commands. Prefer the returned `npm run ...` lanes over inventing shell commands.

4. Resolve canonical documentation before explaining SCBE concepts.
Call `mcp__scbe__scbe_reference_lookup` with focused topics such as `tokenizer`, `sacred eggs`, `triadic`, `harmonic`, `geometry`, `training`, `21d state`, or `source roots`.

5. Use operational context only when needed.
Call `mcp__scbe__scbe_map_room_read_latest` when the task depends on the current handoff state, lane bus context, or recent session notes.

6. Leave MCP discovery mode when the task becomes execution-heavy.
After orientation, switch to repo code inspection, edits, builds, tests, or other SCBE skills as needed. Keep the MCP outputs as the grounding layer.

## Tool Routing

- Use `scbe_system_manifest` for "what system is this repo," "where do I start," "what tools exist," and "what are the main command areas."
- Use `scbe_command_catalog` for "how do I build/test/run MCP/check Docker/start browser services."
- Use `scbe_reference_lookup` for conceptual and canonical questions.
- Use `scbe_tokenizer_health` for server liveness and tool inventory checks.
- Use `scbe_fetch_url`, `scbe_decide_offline`, `scbe_state_emit_21d`, `scbe_sacred_egg_create`, `scbe_sacred_egg_hatch`, and `cymatic-voxel-layout` only after orientation makes it clear they are the right lane.

## Guardrails

- Do not treat `resources/list` failure on the SCBE server as a server outage. This server is tool-oriented and may not implement MCP resources.
- Do not guess SCBE command names from memory when `scbe_command_catalog` can provide repo-backed lanes.
- Do not explain tokenizer, Sacred Eggs, triadic/harmonic symbols, or training-stack claims without checking `scbe_reference_lookup` first.
- Treat missing Docker as an environment problem, not an SCBE MCP problem.

## Examples

- "What SCBE system should I use for this repo?"  
  Start with `scbe_system_manifest`.

- "How do I run the MCP tools here?"  
  Call `scbe_command_catalog` with `area: "mcp"`.

- "Where is the canonical Sacred Eggs doc?"  
  Call `scbe_reference_lookup` with `topic: "sacred eggs"`.

- "Is the SCBE MCP actually working?"  
  Call `scbe_tokenizer_health` and optionally `scbe_system_manifest`.

## References

Read [mcp-first-workflow.md](./references/mcp-first-workflow.md) when you need the canonical topic-to-tool mapping or example topic queries.
Read [claude-handoff.md](./references/claude-handoff.md) when this workflow needs to be handed to Claude or another non-Codex lane.
