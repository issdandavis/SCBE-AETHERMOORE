# App Factory Thought Plan (Research-First)

Date: 2026-03-04
Owner: Codex + SCBE stack
Status: Draft for execution approval

## 1) Decision

Yes, this is a good plan.

Your direction is strategically correct:
- start with bare-bones backend reliability first
- use your existing multi-provider key mesh for routing
- enforce strict state transitions and test gates
- only add advanced UI/visual polish after utility + market viability pass

## 2) What Was Verified Live

### Connectors and runtimes
- `AetherCode gateway` healthy on `http://127.0.0.1:18400/health`
- `AetherBrowse runtime + worker` healthy on `http://127.0.0.1:18401/health`
- `Browser agent` healthy on `http://127.0.0.1:8012/health`
- Browser safety gate and execution verified through `/v1/integrations/n8n/browse`

### Multi-model advice via your keys
- Ran one real AI2AI debate cycle on `/api/ai2ai/workflow/debate`
- Participants selected by live provider mesh:
  - `google_ai`
  - `claude`
  - `xai`
  - `github_models`
- Gate result: `hold` (reason: `missing_test_plan_signal`)
- Meaning: model consensus was strong, but your own review gate correctly required an explicit test strategy before promotion

### Provider mesh status
- Available now from your gateway:
  - `groq`, `cerebras`, `google_ai`, `github_models`, `huggingface`, `ollama`, `xai`, `grok_cli`, `claude`, `google_vertex`
- Missing keys for some optional providers is acceptable; your core mesh is already strong

### GitHub and Notion access
- GitHub identity reachable (`issdandavis`)
- Notion bot authenticated (`n8n-HF-Integration`) and page search works
- Key Notion hubs discovered:
  - SCBE-AETHERMOORE Operations Hub
  - SCBE-AETHERMOORE Public Technical & Theory Hub

## 3) Your Ecosystem Read (Practical)

You already have the components needed for an app-factory control plane:
- task routing primitives (`octo_armor`, gateway provider routing)
- browser automation and validation lanes (`AetherBrowse`, Playwright worker)
- workflow automation substrate (`workflows/n8n/*`)
- cross-talk and session packet infrastructure (`artifacts/agent_comm`, Obsidian mirrors)
- governance and review-gate pattern (`/api/ai2ai/workflow/review-gate`)

Main gap is not capability.
Main gap is packaging these parts into one deterministic execution pipeline with strict state transitions.

## 4) Proposed Operating Model

### Single project spine
- one project
- one source-of-truth repo
- one state machine
- one test factory

### State machine (canonical)
1. `stated`
2. `about_to_start`
3. `in_progress`
4. `finishing_up`
5. `near_done`
6. `finished`
7. `in_review`
8. `review_passed`

No backward jumps except via explicit `reopen` event with reason code.

### Routing model
- Input: issue/task packet
- Router scores by:
  - task type
  - provider readiness
  - cost/latency cap
  - governance risk
- Output:
  - assigned model/tentacle
  - required tests
  - expected artifacts

## 5) Bare-Bones Build Sequence (No Visuals Yet)

### Phase A: Control plane (2-3 days)
- define task schema
- define state transition rules
- define artifact schema
- define retry/dead-letter behavior

### Phase B: Execution lane (3-5 days)
- integrate router with one project repo
- implement worker assignment
- enforce every state transition through API and log

### Phase C: Test factory (3-5 days)
- required gate bundles:
  - unit
  - integration
  - API contract
  - e2e smoke
  - security static checks
  - perf smoke
- auto-fail promotion when any mandatory gate missing

### Phase D: Viability gate (1-2 days)
- utility score (does it solve a repeated pain with measurable output)
- market score (buyer profile, urgency, distribution channel fit)
- only if both pass threshold: move to visual-builder lane

## 6) Visual Builder Handoff (After Viability Only)

- separate lane for design/polish agents
- backend contracts frozen before UI pass
- UI consumes stable APIs/events, not direct internal service calls
- preserve the same test factory after UI integration

## 7) Event-Pipe Architecture (Your “mail pipe” idea)

Yes, this is the right mental model.

Implement as:
- append-only task/event log
- queue topics per lane (`router`, `build`, `test`, `review`, `handoff`)
- workers consume messages and emit signed completion packets
- all packets mirrored to:
  - repo artifacts
  - cross-talk bus
  - Obsidian session note

## 8) Key Risks (Real)

1. Orchestration sprawl across too many lanes too early
2. Hidden test debt if state moves are allowed without evidence attachments
3. Provider routing drift (cost/latency) without quotas
4. Repo fragmentation (work happening outside the primary project spine)

## 9) Immediate Next 7 Tasks

1. Create `app_factory_task.schema.json` and `transition_rules.yaml`
2. Add `POST /api/factory/tasks` and `POST /api/factory/transition`
3. Add artifact contract (`proof`, `logs`, `test_report`, `review_note`)
4. Wire router scoring to provider mesh with hard quotas
5. Add mandatory test bundle runner + gate evaluator
6. Add utility/market scoring endpoint
7. Add visual-handoff endpoint with frozen API contract checksum

## 10) Sources

Primary system sources:
- Gateway endpoints and provider mesh in local `src/aethercode/gateway.py`
- SCBE repo README and architecture docs
- Notion hubs:
  - Operations Hub page ID: `303f96de-82e5-80dc-a63b-f1ffd84e4ad3`
  - Public Technical Hub page ID: `558788e2-135c-483a-ac56-f3acd77debc6`

External architecture references:
- GitHub Codespaces docs: https://docs.github.com/en/codespaces
- AWS dynamic dispatch pattern: https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/routing-dynamic-dispatch-patterns.html
- Microsoft multi-agent reference architecture: https://microsoft.github.io/multi-agent-reference-architecture/index.html

