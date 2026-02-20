# SCBE Round Table Map Room

Purpose: persistent, auditable handoff notes so work survives session resets.

## Concept

The Map Room is the "heart of the castle":

- `session_handoff_latest.md`: current operational state.
- `session_handoff_template.md`: standard handoff format.
- Optional timestamped handoffs for historical chain.

## Rules

1. Every substantial work session should end with a handoff update.
2. Handoff should include actionable restart commands.
3. Keep notes deterministic and minimal: facts, decisions, next steps.
4. Do not store raw secrets; only reference environment variable names.

## Access Pattern

- "Outer wall": general context (what is being built).
- "Inner keep": exact state and blockers.
- "Heart room": resume commands and immediate next actions.

## Resume Protocol

In a new session, ask:

`continue from docs/map-room/session_handoff_latest.md`

