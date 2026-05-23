---
title: "The Multi-Agent Coordination Problem: Why Physics Beats Queues"
slug: multi-agent-coordination-physics-based-scheduler
date: 2026-05-23
author: Issac Daniel Davis
tags: [multi-agent, scheduling, juggling-scheduler, ai-agents, scbe, fleet]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# The Multi-Agent Coordination Problem: Why Physics Beats Queues

The standard approach to multi-agent task coordination is a queue. Tasks go in, agents pull from the queue, tasks come out. Priority queues, retry queues, dead-letter queues. When something fails, you requeue. When something's overloaded, you have a queue depth problem.

Queue-based coordination is fine when tasks are interchangeable and agents are stateless. AI agent tasks are neither. They have inertia.

---

## What agent inertia is

When you assign a research task to an agent that's been working in a domain for the last 30 minutes, that agent has context. It has loaded tool calls, conversation history, partial results. Handing that task to a fresh agent means rebuilding all of that context — at minimum, re-reading the conversation history; at worst, re-running tool calls that took 10 minutes to complete.

Task inertia is the accumulated context that makes an agent good at a task the longer it's been working on it. High-inertia tasks should get fewer handoffs. Low-inertia tasks can move freely.

A queue doesn't know about inertia. It sees tasks as interchangeable. Every dequeue is a potential context-destroying handoff.

---

## The juggling model

The Juggling Scheduler models task coordination as a physics juggling system:

- **Balls** are task capsules — the task plus its accumulated context.
- **Hands** are agent slots — the execution resources.
- **Throws** are handoffs between agents.
- **Arcs** are deadline windows — the trajectory a task must follow to land on time.
- **Drops** are failures.

Seven rules govern the physics:

1. **Never throw to an unready hand.** Check catch readiness before committing to a handoff.
2. **Predict catch windows.** A handoff at the wrong moment costs more than a brief wait.
3. **Fewer handoffs for high-inertia tasks.** A task that's been in-flight for 20 minutes doesn't want to move.
4. **Higher arcs for risky tasks.** More time in-flight, more observation time, better governance coverage.
5. **Detect phase drift.** A task that's drifting toward its deadline needs intervention, not a handoff.
6. **Interception paths.** When a task is on a bad trajectory, route intervention before it drops.
7. **The ledger catches throws, not drops.** Audit records stamp handoffs, not completions. You know the throw happened even if you don't know the catch result yet.

---

## Flight states

Every task capsule is in one of five states:

```
HELD → THROWN → CAUGHT → VALIDATING → DONE
```

The governance layer observes the entire flight path. A task that goes HELD → THROWN → THROWN → THROWN → DONE has three handoffs. That's a signal. Either the task is unusually complex (which should update the inertia estimate), or something went wrong in the handoffs (which should trigger a review).

The ledger stamps each state transition. You get an audit trail of task flight, not just task completion.

---

## Why this matters for AI agent governance

The governance question in a multi-agent system is: which agent took which action, at which point in the task flight, and what was the governance state of that agent at the time?

A queue gives you: task completed by agent ID. No flight path. No handoff record. No governance state at each handoff.

The juggling model gives you: full flight path, handoff receipts at each state transition, governance ring of the receiving agent at each catch, phase deviation if the task drifted from its expected trajectory. Every throw is a governance event.

This matters when something goes wrong. You want to know not just that a task failed, but whether it failed because the agent receiving it was in QUARANTINE state, or because the handoff happened outside the catch window, or because the task's inertia was too high for the number of handoffs it took.

---

## Implementation

TypeScript: `src/fleet/juggling-scheduler.ts`
Python: `hydra/juggling_scheduler.py`

Both implement the same seven rules. The TypeScript version is canonical — it's the production scheduler. The Python version runs in the HYDRA orchestration layer.

Key types: `FlightState`, `TaskCapsule`, `AgentSlot`, `HandoffReceipt`.

The scheduler integrates with the GeoSeal governance layer — every agent slot has an operator ring (ALLOW / QUARANTINE / ESCALATE / DENY), and handoffs check ring compatibility before committing. A QUARANTINE-ring agent can receive a task, but the receipt is flagged.

Full repo: [issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE)
