# DARPA and Government Systems Transfer Map For SCBE Agent Bus

Date: 2026-04-26

## Scope

This is a proposal-support source map for the SCBE agent bus and HYDRA coordination layer. It uses public official government sources only. The intent is to improve software architecture, evaluation, assurance, training, and proposal framing. It does not describe weaponization, targeting, tactical deployment, evasion, or physical drone operations.

## When To Use This

Use this after the first agent-bus feature branches begin landing. The immediate branch roadmap is in:

- `docs/specs/AGENT_BUS_VALUE_AND_FEATURE_BRANCHES_2026-04-26.md`
- `config/system/agent_bus_feature_branches_v1.json`

This file is the second-stage map: once the bus has stronger gates, mission envelopes, simulation mode, traces, and scoreboards, these government systems give us credible language and evaluation patterns for DARPA proposals.

## Transfer Targets

### 1. DARPA Assured Autonomy

Relevant public concept: continual assurance for learning-enabled cyber-physical systems.

Transfer to SCBE:

- continuous assurance for agent-bus routes;
- operation-time monitoring as models and providers evolve;
- explicit treatment of learned components as less predictable than deterministic software;
- design-time and run-time assurance artifacts.

SCBE feature branches affected:

- `feat/agentbus-default-rehearsal-gate`
- `feat/agentbus-durable-checkpoints`
- `feat/agentbus-result-judges`

Proposal angle:

SCBE is not just a multi-agent launcher; it is an assurance layer for learning-enabled software workflows.

### 2. DARPA CyPhER Forge

Relevant public concept: real-time digital twin plus AI test agent with statistical safety guarantees for accelerated test and evaluation.

Transfer to SCBE:

- build a digital twin of an agent-bus mission before dispatch;
- use simulation mode to reduce the number of expensive/live test points;
- turn gate reports and traces into a test agent that proposes the next best evaluation;
- add uncertainty and confidence fields to mission scoring.

SCBE feature branches affected:

- `feat/agentbus-simulation-mode`
- `feat/agentbus-scoreboard-routing`
- `feat/agentbus-training-exporter`

Proposal angle:

SCBE can present agent workflows as testable digital-twin missions where each dispatch is preceded by a rehearsal and followed by measurable evidence.

### 3. DARPA CASTLE

Relevant public concept: realistic learning environments for defensive cyber agents, reinforcement-learning exploration, repeatable measurement, and public benchmark datasets.

Transfer to SCBE:

- create realistic coding/governance/security task environments;
- train operator agents on repeatable route/gate/score loops;
- publish scrubbed benchmark-style datasets from synthetic bus missions;
- separate training data from independent frozen evaluation records.

SCBE feature branches affected:

- `feat/agentbus-simulation-mode`
- `feat/agentbus-result-judges`
- `feat/agentbus-training-exporter`

Proposal angle:

SCBE can be framed as a repeatable training and evaluation environment for defensive coding and agent coordination, not a one-off chatbot workflow.

### 4. DARPA EMHAT

Relevant public concept: digital twins of human-AI teams for modeling and evaluating team behavior in proxy operational settings.

Transfer to SCBE:

- model providers as players, watchers, rest lanes, and human approval roles;
- build simulated user/operator profiles for stress testing;
- measure team completion rate, adaptation, and failure modes;
- turn the mirror room into a human-AI team evaluation surface.

SCBE feature branches affected:

- `feat/agentbus-scoreboard-routing`
- `feat/agentbus-human-approval-tripwires`
- `feat/agentbus-trace-spans`

Proposal angle:

SCBE’s mirror-room bus can become a measurable human-AI team simulator for coding and research operations.

### 5. DARPA RACER

Relevant public concept: repeated develop-test-develop-test cycles, simulation plus field testing, and autonomy algorithms evaluated under complex conditions.

Transfer to SCBE:

- use repeated bus missions as training laps;
- score resilience under noisy inputs, failed providers, missing files, or budget constraints;
- test algorithms in progressively harder software environments instead of static prompts.

SCBE feature branches affected:

- `feat/agentbus-scoreboard-routing`
- `feat/agentbus-result-judges`
- `feat/agentbus-durable-checkpoints`

Proposal angle:

SCBE can borrow the "repeated evaluation under complexity" structure without copying any vehicle tactic or physical deployment behavior.

### 6. DARPA HACMS

Relevant public concept: high-assurance software, formal methods, secure parsers, partitioning, least privilege, defense in depth, and machine-checkable evidence.

Transfer to SCBE:

- harden HYDRA packet parsing;
- validate all bus inputs against schemas;
- isolate dispatch, watcher, scoring, and file mutation privileges;
- add parser tests and machine-checkable packet invariants.

SCBE feature branches affected:

- `feat/agentbus-mission-envelope`
- `feat/agentbus-human-approval-tripwires`
- `feat/agentbus-trace-spans`

Proposal angle:

SCBE can claim a high-assurance control plane direction: typed packets, parser validation, least privilege dispatch, and auditable proof artifacts.

### 7. DARPA AIxCC

Relevant public concept: AI systems to secure critical open-source software, with competitive evaluation and open-source cyber reasoning systems.

Transfer to SCBE:

- focus bus evaluations on coding-agent repair, bug finding, and regression protection;
- create AIxCC-style challenge tasks for internal model promotion;
- compare model adapters by executable repair success instead of only perplexity.

SCBE feature branches affected:

- `feat/agentbus-result-judges`
- `feat/agentbus-training-exporter`
- `feat/agentbus-scoreboard-routing`

Proposal angle:

SCBE can frame its coding-agent bus as a cyber reasoning and repair evaluation harness for open-source software maintenance.

### 8. DARPA SABER

Relevant public concept: operational AI red teaming for deployed AI-enabled autonomous systems, including robustness under distribution shift and adversarial conditions.

Transfer to SCBE:

- red-team agent-bus outputs before adapter promotion;
- test prompt drift, time-over-intent steering, recall failures, and unsafe tool calls;
- maintain explicit robustness metrics under constrained/stressed deployment contexts.

SCBE feature branches affected:

- `feat/agentbus-human-approval-tripwires`
- `feat/agentbus-result-judges`
- `feat/agentbus-training-exporter`

Proposal angle:

SCBE can present a controlled AI red-team lane for agentic coding systems, with measurable pre-deployment robustness checks.

## Proposal Language To Preserve

- continual assurance;
- learning-enabled components;
- operationally representative test contexts;
- digital twin mission rehearsal;
- automated, repeatable, measurable evaluation;
- human-AI team modeling;
- high-assurance parsers;
- typed packets and least privilege;
- independent frozen test sets;
- robustness under distribution shift;
- red-team evaluation before promotion.

## Near-Term Work Items

1. Add `mission_id`, `risk_class`, and `lease_seconds` to the bus mission envelope.
2. Add a typed HYDRA packet exporter from `agentbus run`.
3. Add schema validation for bus input and summary output.
4. Add simulation-mode records to the training exporter.
5. Add independent frozen evals for bus routing decisions.
6. Add time-over-intent drift tests to the result judges.
7. Add a red-team prompt set for recall and unsafe escalation contexts.
8. Add proposal-ready evidence tables from real bus runs.

## Official Sources

- DARPA Assured Autonomy: https://www.darpa.mil/research/programs/assured-autonomy
- DARPA CyPhER Forge: https://www.darpa.mil/research/programs/cypher-forge
- DARPA CASTLE: https://www.darpa.mil/research/programs/cyber-agents-for-security-testing-and-learning-environments
- DARPA EMHAT: https://www.darpa.mil/research/programs/exploratory-models-of-human-ai-teams
- DARPA RACER: https://www.darpa.mil/research/programs/robotic-autonomy-in-complex-environments-with-resiliency
- DARPA HACMS case study: https://www.darpa.mil/news/resources/case-studies/hacms
- DARPA AIxCC: https://www.darpa.mil/research/programs/ai-cyber
- DARPA SABER: https://www.darpa.mil/research/programs/saber-securing-artificial-intelligence
