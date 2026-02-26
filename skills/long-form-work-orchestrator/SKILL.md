---
name: long-form-work-orchestrator
description: Run long-form engineering work in checkpointed phases with deterministic artifacts, resilience handling, and end-of-run reliability reporting.
---

# Long-Form Work Orchestrator

## Purpose

Use this skill for multi-hour or high-surface-area tasks that need:
- staged execution,
- periodic progress checkpoints,
- resumable artifacts,
- boundary/risk reporting at the end.

## Workflow

1. Define a run manifest:
- `goal`
- `scope`
- `in-scope files`
- `out-of-scope files`
- `success criteria`
- `stop criteria`

2. Split work into phases:
- `stabilize` (fix blockers)
- `improve` (feature/test hardening)
- `evaluate` (full run and boundaries)
- `handoff` (summary + next steps)

3. Write checkpoints every phase:
- timestamp
- phase status (`pending|in_progress|done|blocked`)
- files changed
- key metrics
- blockers and decisions

4. Enforce deterministic outputs:
- scripts
- tests
- JSON/YAML reports
- no hidden/manual-only state

5. Handle failures with policy:
- `environment` (permissions, missing toolchain): isolate and report separately
- `regression` (new breakage): stop and patch immediately
- `legacy debt` (pre-existing failures): log with severity and ownership hint

## Reliability/Growth Reporting Contract

At run end, produce:
- `baseline_counts`: pass/fail/error/skip/xfail
- `post_counts`: pass/fail/error/skip/xfail
- `delta`: net improvement/regression
- `new_boundaries`: discovered weak points
- `hardened_boundaries`: weak points that now have tests/guards

## Multi-Agent / Swarm Addendum

For swarm/browser/autonomy work:
- require membrane scan before high-risk actions
- map membrane result to turnstile action by domain
- persist events to primary + replicas (decentralized write path)
- never rely on a single hub path for critical artifacts

## Required End Output

Return:
- concise change summary
- explicit paths changed
- unresolved blockers
- tri-fold YAML `action_summary` with:
  - `build`
  - `document`
  - `route`
