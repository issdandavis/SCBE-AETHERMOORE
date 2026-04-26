# Agent Bus Value and Feature Branches

Date: 2026-04-26

## What The SCBE Agent Bus Can Do Now

The current SCBE agent bus is a local-first coordination layer for AI operations. It can:

- route one task through player, watcher, and rest lanes;
- keep private work local by default through `privacy=local_only`;
- dispatch through the offline/local control-plane path without remote model calls;
- attach deterministic operation-shape metadata from a command such as `korah aelin dahru`;
- emit binary and hexadecimal operation signatures for route verification;
- write watcher state, tracker snapshots, latest-round packets, run summaries, and rehearsal reports;
- enforce a mission rehearsal gate with budget, privacy, provider, watcher, anti-amplification, operation-shape, telemetry, and abort checks;
- generate pass/fail gate records that can become training data for the `operator_agent_bus` lane.

## Current Value

The value is not that it is another chat wrapper. The value is that it turns loose agent activity into inspectable workflow state.

- **Control value:** every task gets routed through a visible formation instead of being handled as an invisible ad hoc prompt.
- **Privacy value:** local-only runs stay on local/offline providers unless explicitly moved to remote-compatible lanes.
- **Audit value:** run summaries, watcher state, tracker snapshots, and gate reports leave reviewable evidence.
- **Training value:** each bus round can become a labeled example: dispatch, rehearse, block, ask for telemetry, or create a fix plan.
- **Cost value:** the scheduler already considers estimated provider cost and can be extended into outcome-per-cent routing.
- **Safety value:** watcher anti-amplification and rehearsal gates reduce recursive agent drift.
- **System value:** it is a practical trunk for coding agents, model training, provider routing, help-desk tickets, and future automation flows.

## How To Increase Capability And Value

The bus becomes substantially more valuable when it closes the loop:

```text
task -> route -> rehearse -> dispatch -> observe -> score -> ticket/train -> improve routing
```

That loop should become the default shape for SCBE agent work. The current implementation covers route, dispatch, observe, and rehearse. The next work is score, ticket/train, and learned routing.

## Research Findings From Successful Agent Coordination Systems

The strongest external systems converge on the same operational principles:

- **LangGraph:** durable execution persists workflow progress, supports pause/resume, and requires non-deterministic operations and side effects to be wrapped so replay does not repeat them.
- **Microsoft Agent Framework:** separates open-ended agent work from explicit workflows and emphasizes session state, type safety, middleware, telemetry, and graph-based multi-agent orchestration.
- **CrewAI:** combines crews and flows, with guardrails, memory, knowledge, observability, structured outputs, stateful flow routing, and human-in-the-loop triggers.
- **OpenAI Agents SDK:** makes tracing and guardrails first-class, including spans for agents, generations, function calls, guardrails, and handoffs, plus tripwires that halt execution.
- **NATS:** queue groups provide load balancing, no-responder feedback, work queues, and geo-affinity for distributed service routing.
- **Temporal:** durable execution resumes workflows after crashes, network failures, or outages, which matters for long-running agent work.
- **Ray:** actor/task systems support cancellation, cleanup, task events, and resource-aware distributed execution.

The lesson for SCBE: do not only make agents smarter. Make movement between agents durable, observable, cancelable, gated, and scoreable.

## Ten Feature Branches To Improve Over Time

These are named as feature branches because each can become a focused implementation lane, test suite, and training-data source.

### 1. `feat/agentbus-default-rehearsal-gate`

Make the rehearsal gate the default for `agentbus run`. Local runs use soft mode. Remote/live runs require strict mode with telemetry and abort criteria.

Value increase: prevents ungoverned dispatch and creates labeled gate data for every run.

Acceptance tests:

- local run passes with offline provider and operation shape;
- remote run fails without telemetry and abort rule;
- strict remote run passes with telemetry and abort rule.

### 2. `feat/agentbus-mission-envelope`

Add first-class mission fields: `mission_id`, `expected_artifacts`, `success_metric`, `rollback_path`, `lease_seconds`, and `risk_class`.

Value increase: turns prompts into mission packets that can be audited, replayed, and scored.

Acceptance tests:

- mission envelope serializes into `run_summary.json`;
- missing mission fields trigger gate warnings or failures by risk class;
- HYDRA packet export preserves the same mission identifiers.

### 3. `feat/agentbus-durable-checkpoints`

Add LangGraph/Temporal-style checkpoints around each bus phase: route, rehearse, dispatch, observe, score, ticket, train.

Value increase: long-running work can resume without repeating side effects or losing state.

Acceptance tests:

- interrupted run resumes from last completed phase;
- repeated resume does not duplicate dispatch events;
- idempotency keys are recorded for provider calls and file writes.

### 4. `feat/agentbus-trace-spans`

Emit OpenAI Agents SDK-style spans for agent run, provider dispatch, guardrail check, handoff, tool call, watcher observation, and gate result.

Value increase: every failure becomes diagnosable instead of buried in logs.

Acceptance tests:

- trace contains one span per bus phase;
- trace links to watcher, tracker, and gate artifacts;
- sensitive raw prompt text is omitted or hashed.

### 5. `feat/agentbus-scoreboard-routing`

Track provider and lane performance by pass rate, executable success, latency, cost, retry count, regression failures, and human override count.

Value increase: routing improves from experience rather than static provider strengths.

Acceptance tests:

- scoreboard updates after each completed run;
- low-performing providers are demoted for matching task types;
- high-performing local providers are preferred when privacy and cost match.

### 6. `feat/agentbus-queue-groups`

Add NATS-style queue group semantics locally before adding any external broker: capability queues, no-responder status, worker leases, and fair distribution.

Value increase: the bus can scale from one agent to multiple workers without duplicate work or silent stalls.

Acceptance tests:

- only one worker claims a queued task;
- no-responder status is returned when no capable worker exists;
- expired lease returns work to the queue.

### 7. `feat/agentbus-human-approval-tripwires`

Add guardrail tripwires for risky actions: remote provider use, file mutation, email send, payment/contract action, secret-adjacent content, or destructive shell commands.

Value increase: human-in-the-loop becomes a checkpoint before side effects, not a final apology after damage.

Acceptance tests:

- tripwire blocks dispatch before provider/tool execution;
- approval packet records who approved, what changed, and why;
- denied approval generates a help-desk fix plan.

### 8. `feat/agentbus-simulation-mode`

Add a no-provider simulation mode that runs route, gate, watcher, tracker, and scoring without executing dispatch.

Value increase: cheap training data and safe dry runs for workflows before spending tokens or touching files.

Acceptance tests:

- simulation produces the same packet shape as live run minus dispatch event;
- simulation cannot mutate files outside artifact paths;
- simulation exports SFT and multiple-choice training records.

### 9. `feat/agentbus-result-judges`

Add lane-specific judges: coding uses executable tests, review uses finding quality, research uses source coverage, governance uses gate compliance, training uses frozen evals.

Value increase: each lane is measured by its job, not by one generic LLM score.

Acceptance tests:

- coding judge runs tests and records pass/fail;
- research judge requires citations and freshness flags;
- governance judge requires gate and policy compliance.

### 10. `feat/agentbus-training-exporter`

Export bus traces, gate reports, scoreboard rows, and help-desk outcomes into regularized datasets for the operator/instructor/coder model buckets.

Value increase: the bus teaches future models from actual SCBE operations rather than synthetic prompts alone.

Acceptance tests:

- exporter produces JSONL with source, lane, quality, decision, and provenance metadata;
- raw secrets and raw private prompts are scrubbed or hashed;
- records split into train/eval/independent-test partitions.

## Recommended Build Order

1. Default rehearsal gate.
2. Mission envelope.
3. Simulation mode.
4. Trace spans.
5. Scoreboard routing.
6. Human approval tripwires.
7. Result judges.
8. Training exporter.
9. Durable checkpoints.
10. Queue groups.

This order gives fast value first: better gates, better artifacts, safer tests, better training data. Durable execution and queue groups matter more once the bus has enough volume to justify them.

## Immediate Commands

Current gated local run:

```powershell
python scripts\scbe-system-cli.py agentbus run --task "<goal>" --operation-command "korah aelin dahru" --task-type coding --privacy local_only --budget-cents 0 --dispatch --rehearsal-gate --json
```

Strict remote/live-style rehearsal shape:

```powershell
python scripts\scbe-system-cli.py agentbus run --task "<goal>" --operation-command "korah aelin dahru" --task-type research --privacy remote_ok --budget-cents 2 --strict-rehearsal-gate --telemetry-path artifacts/agent_bus/telemetry/<series>.jsonl --abort-condition "stop on unsafe output, missing citation, or empty result" --json
```

## Sources

- LangGraph durable execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
- Microsoft Agent Framework overview: https://learn.microsoft.com/en-us/agent-framework/overview/
- CrewAI documentation: https://docs.crewai.com/en
- OpenAI Agents SDK tracing: https://openai.github.io/openai-agents-js/guides/tracing/
- OpenAI Agents SDK guardrails: https://openai.github.io/openai-agents-python/guardrails/
- NATS queue groups: https://docs.nats.io/nats-concepts/core-nats/queue
- Temporal documentation: https://docs.temporal.io/
- Ray actors documentation: https://docs.ray.io/en/latest/ray-core/actors.html
