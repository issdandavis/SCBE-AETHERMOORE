# SCBE Fleet Governance Gate

Status: implemented as a deterministic guardrail, not a certification claim.

The fleet governance gate sits after the agent move packet:

```text
model output
  -> command extraction
  -> GeoSeal policy compile
  -> agent move packet
  -> fleet governance gate
  -> harness execution / block / escalation
```

## Purpose

This advances SCBE toward higher-assurance fleet operation by making every
agent command answer four questions before it is treated as runnable:

1. What operation class is this move?
2. Is the actor cleared for that class?
3. Does the fleet posture require quorum?
4. Does the current fleet state force quarantine or denial?

The gate is deliberately fail-closed. If a move packet is missing, not
bijective, carries secret material, lacks quorum, or targets a degraded remote
lane, it is not silently accepted.

## Operation Classes

| Class | Examples | Default Meaning |
| --- | --- | --- |
| `observe` | `ls`, `cat`, `rg` | Read-only inspection. |
| `measure` | `pytest`, `npm test`, `gh pr checks` | Verification or scoring. |
| `modify` | `patch`, `git add`, formatters | Local workspace changes. |
| `network` | `curl`, `gh api`, `ssh` | Remote I/O or external calls. |
| `deploy` | `git push`, `npm publish`, `gh pr merge` | Release or shared-state change. |
| `destructive` | `rm -rf`, `kubectl delete`, `drop database` | Destructive action. |

## Fleet Postures

| Posture | Intended Use |
| --- | --- |
| `training` | Local/default harness development. |
| `canary` | Limited-scope external or pre-release run. |
| `production` | Shared system state or public release lanes. |
| `mission_critical` | Highest caution profile for fleet orchestration. |

## Outputs

The gate emits:

- `StateVector`: operation class, posture, clearance, quorum, BFT minimum node
  count, degraded-comms state, command hash, and move ID.
- `DecisionRecord`: `ALLOW`, `QUARANTINE`, `ESCALATE`, or `DENY`, with reason,
  confidence, deterministic signature, timestamp, and findings.

## Boundary

This is not a military certification, FedRAMP authorization, weapons system, or
deployment approval by itself. It is a deterministic command-authority layer
that can be composed with DCP receipts, GeoSeal policy, CI evidence, and fleet
health monitoring.
