---
name: scbe-longform-work
description: Execute long-running implementation and research tasks with checkpointed handoffs, compact status artifacts, and deterministic resume points. Use when work spans many steps, multiple sessions, or multiple agents and requires durable continuity.
---

# SCBE Longform Work

Use this workflow for deep tasks that must survive context limits and session boundaries.

## Execution Pattern

1. Break the objective into phases with clear done criteria.
2. Keep one active phase at a time.
3. Emit compact checkpoint artifacts at phase boundaries.
4. Resume from checkpoint instead of re-deriving state.

## Checkpoint Contract

1. Write current status to `docs/map-room/session_handoff_latest.md`.
2. Include `objective`, `completed`, `in_progress`, `blocked`, `next_actions`.
3. Include exact file paths changed and pending.
4. Include command history required for deterministic resume.

## Reliability Rules

1. Prefer append-only operational logs.
2. Preserve evidence for major decisions.
3. Record assumptions and invalidation triggers.
4. Keep rollback path for each risky change.

## Output Contract

1. `phase_plan.md` with execution stages.
2. `session_handoff_latest.md` updated at every checkpoint.
3. `decision_log.jsonl` for governance and tradeoff traceability.
