# Agentic Control Desktop Integration Spec

Date: 2026-05-21
Status: working spec
Inputs:
- Updated Kimi reference zip: `C:\Users\issda\Downloads\Kimi_Agent_Web Linux OS Build.zip`
- Older Kimi reference app: `C:\Users\issda\Downloads\Kimi_Agent_Web_Linux_OS_Build_1\app`
- Governed desktop spec: `docs/superpowers/specs/2026-05-21-aether-desktop-governed-os-design.md`
- Polly Pad runtime surfaces: `src/fleet/polly-pad.ts`, `src/fleet/polly-pad-runtime.ts`,
  `src/fleet/polly-pads/`

## Decision

Use the Kimi app as a **visual/interaction reference only**. Do not ship its source code in a
commercial product. Rebuild the UI cleanly and wire it to original SCBE operation contracts,
Polly Pad runtime state, and governed backend endpoints.

The updated Kimi zip is useful because it added the right product screens:

- Governance Console
- Model Router
- Execution Timeline
- Audit Logs
- Approval Gates
- Multi-Agent Terminal / Terminal shell surfaces

These should become first-class screens in the Aether Desktop product, but with real data and
real gated operations.

## Product Aim

The user sees:

```text
A: what I want
Z: useful output / receipt / artifact
```

The system handles b through y:

- context bins
- role lanes
- model routing
- native commands
- probe moves
- dry runs
- validator checks
- approval gates
- audit logs
- final delivery packet

The front end should not feel like a static CLI. It should feel like a lightweight agentic control
tool that works with the user: suggestions, command rails, next actions, visible receipts, and
reviewable state.

## Core UI Screens

### 1. Command Rail

Purpose: main input surface, not a marketing form.

Visible controls:
- command input
- context bins
- native command palette
- run/dry-run buttons
- current route
- budget/privacy guard
- result receipt

Real backend target:
- `POST /v1/op` once the governed desktop backend exists
- interim Vercel surface: `/v1/polly/hosted-run`

Native command categories:
- `agent.run`
- `agent.review`
- `agent.research`
- `code.probe`
- `code.test`
- `code.patch.preview`
- `model.route`
- `pad.note`
- `pad.tool.save`
- `audit.export`
- `workflow.preview`
- `workflow.execute`

### 2. Governance Console

Reference look: Kimi `GovernanceConsole.tsx`.

Real SCBE wiring:
- agent identity
- trust vector
- drift score
- governance tier
- dimensional state
- current zone
- current restrictions
- last operation decision

Primary sources:
- `src/fleet/polly-pad.ts`
- `src/fleet/polly-pad-runtime.ts`
- `src/governance/decision_envelope_v1.py`
- `src/governance/runtime_gate.py`

### 3. Model Router

Reference look: Kimi `ModelRouter.tsx`.

Real SCBE wiring:
- local Ollama models
- free cloud routes
- paid routes locked by budget guard
- latency/failure/cost counters
- route decision reason

Primary sources:
- `src/api/free_llm_routes.py`
- `src/cli/slm_router.py`
- `src/coding_spine/router.py`
- `api/agent/governed-chat.js`

### 4. Execution Timeline

Reference look: Kimi `ExecutionTimeline.tsx`.

Real SCBE wiring:
- operation lifecycle
- workflow steps
- dependency graph
- probe vs committed moves
- task output references
- before/after audit status

Primary sources:
- future `packages/workflow-engine`
- agent-bus artifacts
- board-kernel receipts
- `src/flow_router/`

### 5. Audit Logs

Reference look: Kimi `AuditLogs.tsx`.

Real SCBE wiring:
- append-only audit rows
- request/decision/result summary
- risk level
- origin app/workflow/agent
- artifact refs
- no raw secrets or full prompt dumps

Primary sources:
- governed desktop operation contract
- `src/governance/audit_ledger.ts`
- `src/harmonic/governance_logger.py`
- `src/fleet/polly-pads/blackout-audit.ts`

### 6. Approval Gates

Reference look: Kimi `ApprovalGates.tsx`.

Real SCBE wiring:
- pending operation requests
- RED/YELLOW route escalations
- manual override
- two-party/quorum vote where needed
- deny reason

Primary sources:
- `src/fleet/polly-pads/decision-envelope.ts`
- `src/fleet/polly-pads/squad.ts`
- `src/fleet/polly-pad-runtime.ts`

## Native Lightweight Agent Loop

This does not need a full autonomous AI inside the browser.

Build a lightweight loop:

```text
observe current command/context
suggest next native command
run dry-run/probe by default
show receipt
ask for approval only when needed
promote successful probe to committed move
record audit/event
suggest next push
```

This can be deterministic at first. It only needs enough intelligence to keep the user on rails.

### Loop State

```ts
interface AgentLoopState {
  activeGoal: string;
  contextBins: Record<string, string>;
  suggestedCommands: NativeCommand[];
  currentRoute: 'local-first' | 'ollama-first' | 'hosted-ok' | 'hosted-required';
  risk: 'low' | 'medium' | 'high' | 'critical';
  lastReceipt?: OperationResult;
  nextPush: string[];
}
```

### Native Command

```ts
interface NativeCommand {
  id: string;
  label: string;
  op: string;
  argsTemplate: Record<string, unknown>;
  defaultDryRun: boolean;
  requiredZone: 'GREEN' | 'YELLOW' | 'RED';
  description: string;
}
```

The loop is useful even without a model because it can:
- propose safe next actions from command templates
- prevent direct tool execution
- surface dry-run first
- connect the user to the real bus
- log receipts

## Polly Pad Concepts To Reuse

The older Polly Pad system has better mechanics than the Kimi reference UI:

- per-agent workspace
- notes, sketches, saved tools
- Sacred Tongue tiers
- HOT vs SAFE code zones
- six specialist pad modes
- tool matrices by mode/zone
- squad quorum
- decision envelopes
- blackout audit chain
- resource-aware harmonic routing

Map those into the desktop:

| Polly Pad concept | Desktop UI use |
|---|---|
| Pad note | context bin / durable session memory |
| Pad tool | saved native command / prompt / script template |
| HOT zone | exploratory draft/probe mode |
| SAFE zone | execution mode after governance approval |
| Pad mode | workspace lane: engineering, navigation, systems, science, comms, mission |
| Decision envelope | approval gate rule |
| Squad quorum | multi-agent approval state |
| Blackout audit | offline/exportable audit receipt |
| Resource harmonic | budget/context/cost pressure meter |

## GeoSeal Legitimacy Trial

GeoSeal is not only a receipt writer. In the high-security version, it is the
attestation layer that decides whether normal CLI/tool use should open at all.
The name should be read literally:

- **Geo** means situated context: time, place, host, workspace, route, environment,
  and the current system state around the request. It does not have to mean precise
  GPS; in local workflows it can mean verified workspace, machine, clock, network,
  and user-confirmed operating context.
- **Seal** means cryptographic or deterministic closure: the request, context,
  decision, reason, and result are bound into an auditable proof that can be checked
  later.

Before a command becomes a regular operation, the desktop should request a small
legitimacy packet:

```ts
interface GeoSealLegitimacyPacket {
  requestId: string;
  requestedAt: string; // trusted timestamp source when available
  localTime: string;
  timezone: string;
  coarseLocation?: {
    source: 'user_confirmed' | 'network' | 'device' | 'simulated';
    label: string;
    confidence: number;
  };
  systemMetrics: {
    hostIdHash: string;
    processId?: number;
    batteryPercent?: number;
    networkState?: 'offline' | 'local' | 'online';
    workspaceHash?: string;
  };
  intentPacket: {
    goal: string;
    origin: 'user' | 'agent' | 'workflow';
    expectedTool: string;
    expectedState?: string;
  };
}
```

The security matrix compares that packet against known system goals, workspace
state, user intent, command risk, location/time plausibility, and recent action
history. The result is a legitimacy decision:

- `ALLOW_CLI`: regular CLI/native command use is allowed inside the scoped workspace.
- `PROBE_ONLY`: dry-run, read-only, or simulated actions only.
- `ESCALATE`: require explicit user approval or stronger attestation.
- `DENY`: refuse the operation and write the reason.

This keeps the rule clean: agents may request time, date, location, and key system
metrics for legitimacy checks, but those checks route through the security matrix
before any broader CLI/tool authority is granted.

Implemented first slice:

```powershell
python -m src.geoseal_cli legitimacy-trial `
  --goal "run focused tests" `
  --tool terminal.command.request `
  --workspace . `
  --location-source user_confirmed `
  --location-label "local dev workstation" `
  --location-confidence 0.95 `
  --network-state local `
  --json `
  -- python --version
```

The subcommand does not execute the command. It parses the command shape, builds
the situated legitimacy packet, evaluates the context, and returns
`ALLOW_CLI`, `PROBE_ONLY`, `ESCALATE`, or `DENY`. The existing `geoseal exec`
layer remains responsible for actual governed execution after authority is
opened.

## Research Navigation Tools

The CLI now has first-slice source navigation commands for agents and users. The
point is not to make every agent "search the web" loosely. The point is to return
stable evidence packets that can be routed, scanned, cited, and sealed.

```powershell
python -m src.geoseal_cli research-nav `
  --url https://example.com/root `
  --content "<title>Inline Evidence</title><p>Research packet test.</p>" `
  --no-fetch `
  --json
```

`research-nav` emits the shared evidence contract:

- `url`
- `resolved_url`
- `status`
- `title`
- `text_excerpt`
- `links`
- `metrics`
- `fetched_at`
- `security`

When content is present, it passes through the semantic antivirus scanner so the
packet carries an early governance/security verdict before an agent treats the
source as trustworthy.

```powershell
python -m src.geoseal_cli youtube-nav `
  https://www.youtube.com/watch?v=dQw4w9WgXcQ `
  --json
```

`youtube-nav` emits a stable YouTube packet with video id, canonical URL, optional
metadata evidence, and optional transcript evidence. It does not fetch transcript
or metadata by default, which keeps agent runs cheap and predictable. Callers must
opt in with `--fetch-metadata` or `--fetch-transcript`.

These commands are gateways. Future connectors for arXiv, GitHub, Hugging Face,
SAM.gov, Notion exports, Obsidian vaults, and browser automation should produce
the same source/evidence shape instead of inventing a new packet format per tool.

## First Build Slice

Do not port the whole desktop.

Build one vertical slice:

1. Clean UI shell with command rail.
2. Model Router panel with real/free/local route metadata.
3. Execution Timeline panel receiving fake-but-shaped events locally.
4. Submit command to `/v1/polly/hosted-run` or future `/v1/op`.
5. Store the returned receipt in Audit Logs panel.
6. Approval Gates panel intercepts high-risk native commands before submit.

Acceptance:
- no raw Kimi source code shipped
- user can enter A and see Z
- b-y appears as timeline/audit/approval state
- dry-run works before commit
- no paid route is used by default

## Merge Strategy

1. Keep the Kimi zip archived as a reference artifact.
2. Do not extract it into the repo as source.
3. Build new clean components in the product repo or a dedicated `apps/aether-desktop/` branch.
4. Copy visual ideas manually, not code.
5. Wire only to existing SCBE endpoints/contracts.

## Open Questions

- Should the desktop live in a separate repo (`aether-desktop`) or under `apps/aether-desktop/`
  until it is stable?
- Should `/console` on Vercel stay the lightweight public hosted bus while the full desktop is
  local-first?
- Which native commands are the first ten that should be wired to real operations?
