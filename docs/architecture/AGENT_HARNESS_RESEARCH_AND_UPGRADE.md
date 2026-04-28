# Agent Harness Research and Upgrade

Date: 2026-04-28

## Research Inputs

The upgrade follows four current agent-harness patterns:

- Durable execution: save progress at checkpoints so a workflow can pause or recover without repeating completed side effects.
- Guarded boundaries: validate workflow/tool inputs and outputs at the point where side effects happen, not only at the start or final response.
- Explicit termination: every multi-agent or workflow run needs stop conditions so loops cannot continue forever.
- Structured observability: trace events should be sequenced per run and labeled by surface so operators can reconstruct what happened.

Primary external references:

- LangGraph durable execution: persistence, thread identity, deterministic replay, and idempotent side effects.
- OpenAI Agents SDK guardrails and handoffs: guardrail boundaries and structured handoff metadata.
- Microsoft AutoGen termination conditions: max messages, timeout, handoff, external stop, and other run limits.
- AgentTrace: structured telemetry across operational, cognitive, and contextual surfaces.

## Local Inputs

Local surfaces reviewed:

- `src/ai_orchestration/tasks.py`
- `src/ai_orchestration/orchestrator.py`
- `src/ai_orchestration/agents.py`
- `src/ai_orchestration/logging.py`
- `src/agent_comms/message.py`
- `src/agent_comms/router.py`
- `agents/agent_bus.py`
- `external/openclaw/src/infra/agent-events.ts`

The OpenClaw event stream was the most directly reusable reference: it keeps monotonic per-run sequence numbers and a small event payload. The SCBE Python workflow harness now applies that idea without importing the TypeScript stack.

## Implemented Upgrade

`WorkflowExecutor` now supports:

- `WorkflowCheckpointStore`: JSON checkpoint files using schema `scbe_workflow_checkpoint_v1`.
- `TerminationPolicy`: max event, max duration, and external stop controls.
- Per-run monotonic event sequence numbers.
- Event `surface` labels, starting with `operational`.
- Resume from checkpoint when the same workflow ID is executed again.
- Stalled workflow detection when dependencies cannot be satisfied and no task is running.

## Remaining Gaps

- Tool-level guardrails still live mostly in `security.py`; task execution should eventually support per-task input/output guard callbacks.
- Handoff metadata is present in message protocols, but workflow steps do not yet have a first-class `handoff_reason` or `handoff_summary` field.
- Event surfaces are implemented as generic labels; future cognitive/contextual events should be emitted from agent decision and memory code, not only the workflow executor.
