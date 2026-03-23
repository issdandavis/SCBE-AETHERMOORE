# Context Broker And Memory

This guide covers session continuity, memory retrieval, and tongue-based routing.

## Core Files

- `src/mcp/context_broker_mcp.py`
- `CLAUDE.md`
- `notes/_inbox.md`
- `notes/round-table/`
- `.scbe/crosstalk_session_state.json`

## What The Broker Does

The Context Broker MCP server provides:

- hot context injection
- deep memory retrieval
- tongue classification
- session summary / journal support
- persistent context across sessions

## Start The Broker

```powershell
python src/mcp/context_broker_mcp.py
```

## Main MCP Tool Concepts

- `context_inject`: get relevant context for an intent
- `context_retrieve`: pull memory files by topic
- `memory_update`: append or write memory entries
- `session_summarize`: capture a session handoff
- `tongue_classify`: map the task to a Sacred Tongue domain and tier

## When To Use This Lane

- A session needs continuity across tools or across agents.
- You want the correct task lane selected automatically.
- You want research, code, and notes to stop drifting apart.

## Practical Rule

If the task spans multiple surfaces, start with context and routing before you start execution. That keeps browser, CLI, notes, and training outputs aligned.
