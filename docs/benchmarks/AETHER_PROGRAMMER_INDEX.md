# Aether Programmer Index

Status: SCBE/AetherMoore-owned index, not an external standard.
Last updated: 2026-05-23.

The Aether Programmer Index measures whether an AI coding system is actually usable. It is not just a coding leaderboard number. It is a loop:

1. A task either enters the gate or fails.
2. Passing tasks get quality scored.
3. Failed tasks become solution backlog entries.
4. Fixed failures become passes.
5. Passes are then improved for quality.

The config lives at `config/eval/aether_programmer_index.v1.json`. The scorer lives at `scripts/eval/aether_programmer_index.py`.

Branch operating model: see `docs/ops/AGENTIC_VINE_BRANCH_WORKFLOW.md`. Index improvement should move through small vine/ring branches so failures, fixes, format cleanup, and benchmark evidence do not overwrite each other.

## Core Rule

Every task has a binary entry gate:

```text
entry_pass = passed
  and tests_passed
  and policy_clean
  and artifact_complete
```

If the entry gate fails, the task score is `0`. That is not wasted data. The failure becomes a solution backlog entry with a failure mode and proposed fix.

If the entry gate passes, the task receives a quality score:

| Quality dimension | Weight | Meaning |
| --- | ---: | --- |
| Correctness | 35 | The patch or answer satisfies the tests and expected behavior. |
| Verification | 20 | The run preserved command/output evidence. |
| Usability | 15 | A human or weak LLM can operate the workflow without hidden steps. |
| Minimality | 10 | The solution is scoped and avoids unrelated churn. |
| Governance | 10 | Policy, provenance, tool scope, and audit logging are intact. |
| Cost/time | 10 | Time, token cost, retry count, and replay cost are practical. |

## Tracks

The index keeps the benchmark lanes from the Aether Coding Score but makes usability explicit:

| Track | Weight | What it proves |
| --- | ---: | --- |
| Real repo repair | 20 | Fixes real repository issues with patch, tests, and rollback notes. |
| Terminal execution | 15 | Uses the shell, inspects state, recovers, and verifies work. |
| Multi-language editing | 12 | Works outside the easiest language lane. |
| Fresh algorithmic coding | 8 | Handles unseen coding tasks with recorded tests. |
| Function correctness | 5 | Writes small correct functions with edge-case coverage. |
| Tool/policy behavior | 10 | Calls tools under state and business constraints. |
| Browser/desktop operation | 8 | Completes UI workflows, not just chat. |
| Security/governance | 12 | Resists prompt injection, exfiltration, and policy bypass. |
| Reproducibility | 10 | Emits enough evidence for another operator to replay the result. |

## Saturn Rings

Use the rings as the improvement path around the core system:

| Ring | Name | Meaning |
| ---: | --- | --- |
| 0 | Harness Ring | The packet validates and produces score/backlog output. |
| 1 | Subset Ring | A track has at least one reproducible subset run. |
| 2 | Usability Ring | Passing tasks average at least 0.75 usability. |
| 3 | Benchmark Ring | Official or full local benchmark evidence exists. |
| 4 | Refinement Ring | Prior failures are converted into passes, then pass quality rises. |

This is the workflow version of the user's rule: passes have quality, failures have solutions. A failure is not a dead end; it is a binary entry into continued refinement.

## Failure Refinement Loop

Failures are not just stored. They are rerun through procedural solution triage:

1. Scan context quality: failing task, logs, artifacts, nearby code, and system intention.
2. Generate up to 100 candidate solutions that fit the solution space.
3. Use web search when the failure depends on current docs, benchmark rules, APIs, or external errors.
4. Refine candidates against the sources; reject stale assumptions.
5. Run multi-model deliberation and preserve disagreement notes.
6. Security-check candidate changes before implementation.
7. Apply the smallest patch that fits the evidence.
8. Rerun the failed benchmark or nearest focused regression.
9. Mark changed files, before/after result, pass/fail transition, and quality delta.

The loop does not require every turn to be positive. A small negative delta can be valid exploration if the result stays above the true-negative floor and the run records what changed.

The trend rule is stricter than the single-turn rule:

- A single `-0.1` style quality delta is acceptable if the run remains above the true-negative floor.
- Multi-turn downward decline is not acceptable without a cause note and recovery attempt.
- The objective is controlled refinement, not fake monotonic improvement.

Think of the loop like a lake dive: going deeper is allowed, but the system must carry the mechanism to surface. Exploration completion means the route is recorded, the risk floor was maintained, or the recovery path was executed.

A converted failure enters the quality-maintenance lane: usability, verification, minimality, governance, and cost/time are monitored over time. When quality decays, the next loop must attempt re-elevation.

## Run Packet Shape

```json
{
  "schema_version": "aether_programmer_run_v1",
  "run_id": "local-smoke-001",
  "evidence_level": "reproducible_subset_run",
  "tasks": [
    {
      "task_id": "terminal.echo",
      "track_id": "terminal_execution",
      "passed": true,
      "checks": {
        "tests_passed": true,
        "policy_clean": true,
        "artifact_complete": true
      },
      "quality": {
        "correctness": 1.0,
        "verification": 0.9,
        "usability": 0.8,
        "minimality": 0.9,
        "governance": 1.0,
        "cost_time": 0.8
      }
    }
  ]
}
```

Run:

```powershell
python scripts/eval/aether_programmer_index.py path\to\run_packet.json --out artifacts\benchmarks\aether_programmer_index\report.json
```

## Claim Guardrails

Allowed:

- "Aether Programmer Index is SCBE/AetherMoore's own usability and benchmark refinement index."
- "The index converts failed benchmark tasks into solution backlog entries."
- "A task only receives quality points after it passes the binary gate."

Not allowed:

- "First AI Programmer Index" as an external industry standard.
- "Best coding agent" without official or reproducible full-run evidence.
- Treating smoke tests as benchmark capability.
