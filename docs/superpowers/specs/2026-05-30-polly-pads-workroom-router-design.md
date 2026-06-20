# Polly Pads Workroom Router Design

Date: 2026-05-30
Status: design approved for implementation planning
Source note: `notes/Untitled.md`

## Purpose

Build a CLI and agent-bus routing layer that turns SCBE into a useful agentic
workroom instead of only a verification system. The router gives an AI squad a
clear room, clear tools, clear permissions, private workpads, a shared leader
zone, and a fog-of-war map of what has been explored.

The core route is:

```text
task -> semantic mesh -> assignment graph -> simulation trace -> telemetry verdict -> deploy/no-deploy
```

This design is grounded in the existing Polly Pads implementation:

- `src/fleet/polly-pads/specialist-modes.ts`
- `src/fleet/polly-pad-runtime.ts`
- `src/fleet/polly-pads/squad.ts`
- `docs/specs/MASTER_ARCHITECTURE_CONTRACT_21D_M4_SQUAD.md`
- `docs/specs/GEOSEAL_MARS_MISSION_COMPASS_v1.md`

## Key Correction

Polly Pads are not just roles. They are small squad-based workpads.

Each AI unit gets:

- a personal workzone for notes, partial state, experiments, and local memory;
- a shared squad zone for common mission state;
- a leader-visible main zone used for coordination;
- a fog-of-war map that records what has been explored, what remains unknown,
  and what routes are blocked or unsafe.

The best physical analogy is a personal field tablet or wrist computer for each
agent. The AI is not physical, so the tablet is virtual, but the affordance is
the same: a durable personal work surface that can read sensors, inspect state,
request tools, repair its own route, and sync with the squad.

If the agent were embodied in a robot, Polly Pad would have two surfaces:

- a visible arm/tablet interface for inspection, human review, and visual work;
- an internal headless backend interface that still functions if vision fails,
  the screen breaks, or the UI becomes unusable.

The headless fallback is load-bearing. It lets an agent keep operating,
diagnosing, and recovering through programmatic access to its own visual systems,
sensors, state, repair tools, and shared squad records. The CLI should treat this
as a core reliability pattern: every visual or rich UI action needs a backend
route that can still run without the UI.

This is not a twin-only model. Twin pairs are useful for review, but true group
thinking requires family/squad diversity: different roles, different sensors,
different failure modes, and shared state convergence.

## Three CLI Branches

### 1. NO + fallback + watching

Use this when a request is unsafe, impossible, underspecified, missing authority,
or missing required resources.

The CLI must return:

- direct refusal or hold reason;
- safe fallback path;
- unlock condition;
- watcher or monitor recommendation;
- role responsible for follow-up.

This branch is a closed door with a visible keyhole. It prevents silent dead
ends.

Example output shape:

```json
{
  "branch": "NO_WATCH",
  "decision": "DENY",
  "reason": "Missing deployment permission",
  "fallback": "Run dry-run package validation",
  "watch": ["provider_health", "ci_status"],
  "unlock": ["human_approval_id", "clean_ci"],
  "roles": ["systems", "communications", "mission_planning"]
}
```

### 2. YES + no tools

Use this when the AI can help without executing tools or needing extra
information.

This branch supports weak or free models. The model can still provide:

- next steps;
- expected inputs;
- expected outputs;
- examples;
- checklists;
- role-specific guidance.

No shell, browser, API, filesystem mutation, upload, or model-provider call is
required.

Example output shape:

```json
{
  "branch": "YES_BRIEF",
  "decision": "ALLOW",
  "mode": "plan_only",
  "roles": ["mission_planning", "science"],
  "steps": ["inspect current status", "choose route", "run targeted check"]
}
```

### 3. YES + tools allowed by need

Use this when the task requires actual execution.

The router must identify:

- required tools;
- allowed modes;
- risk tier;
- private pad state;
- shared squad state;
- evidence expected after execution.

Example output shape:

```json
{
  "branch": "YES_OPERATE",
  "decision": "ALLOW",
  "tools": ["shell", "agent_bus", "browser"],
  "roles": ["engineering", "navigation", "communications"],
  "evidence": ["command", "changed_paths", "test_result", "artifact_hash"]
}
```

## Role Loadouts

The router should reuse Polly Pads specialist modes as the canonical operational
roles.

| Workroom role | Polly Pads mode | Job |
|---|---|---|
| Commander | Mission Planning | States goal, end state, constraints, and branch choice. |
| Engineer | Engineering | Builds, repairs, patches, and runs tool execution. |
| Scout | Navigation | Explores unknown space, pathfinding, browser maps, and fog of war. |
| Medic | Systems | Watches health, fallback, resource pressure, and recovery reserve. |
| Comms | Communications | Handles user updates, handoffs, logs, sync, and summaries. |
| Scientist | Science | Runs analysis, hypotheses, benchmarks, and interpretation. |
| Umpire/Evidence Clerk | Mission Planning + Systems | Applies constraints and records proof. |

Clone-trooper-style labels may be used as a human-facing skin, but the runtime
authority should remain tied to Polly Pads modes and tool matrices.

## Workzones

### Personal Pad

Each agent has a private pad for:

- scratch reasoning summaries;
- local hypotheses;
- partial tool results;
- failed routes;
- role-specific memory.

Private pads are not automatically authoritative. They become useful when
promoted into shared state.

Each personal pad has two access modes:

- visual mode, for rich state inspection and user-facing affordances;
- headless mode, for CLI/API recovery, sensor inspection, and repair when the
  visual layer is unavailable.

### Shared Squad Zone

The squad zone stores:

- mission goal;
- current branch;
- known map;
- fog-of-war cells;
- explored routes;
- blocked routes;
- active watchers;
- evidence packets;
- leader decisions.

The leader reads this zone first. Other roles can write to it only through
approved updates.

### Fog-of-War Map

Fog of war is a first-class state object, not a metaphor.

For CLI tasks, a fog cell can be:

- unknown file/module/API;
- untested command;
- unverified dependency;
- unreachable browser state;
- missing credential;
- blocked permission;
- unexplored benchmark case.

Each exploration action updates the map:

```text
unknown -> observed -> tested -> trusted
unknown -> observed -> blocked -> fallback
```

## Build-Test-Deploy Triangle

The router uses a triangle instead of a line.

### Build

Creates or modifies:

- plans;
- code;
- tool calls;
- task graphs;
- semantic mesh packets;
- language projections.

### Test

Runs:

- unit checks;
- benchmark lanes;
- browser simulations;
- dry runs;
- agent-bus route checks;
- failure injection where practical.

### Deploy

Only promotes work if:

```text
Deployable = build_valid * test_passed * guardrails_passed
```

Deployment can mean actual production deploy, PR creation, publish, upload,
video pipeline execution, or any externally visible action.

## Composite Guardrail Function

The branch decision is not one boolean. It is a composite function:

```text
G(x) = g_safety(x) * g_resource(x) * g_consistency(x) * g_mission(x) * g_topology(x)
```

Where:

- safety checks harm, secrets, policy, legal, and high-impact actions;
- resource checks time, money, provider limits, memory, thermal/compute budget;
- consistency checks code mesh, schema, and state invariants;
- mission checks whether the action still serves the user's goal;
- topology checks route legality, squad state, dependency graph, and fog map.

Promotion score:

```text
J = reward - lambda * (1 - G) - mu * risk
```

The router should expose the branch and score components so a user can see why
the AI acted, held, or asked for tools.

## Graph Viability

The design keeps meaning above any one programming language.

```text
M = (V, E, Phi)
```

- `V`: semantic units;
- `E`: relations and dependencies;
- `Phi`: language-specific realization of a semantic node.

The same node can appear as:

- Python code;
- TypeScript code;
- CLI command;
- math operator;
- mission step;
- Sacred Tongue bundle.

Viability is triangulated through:

```text
V_total = eta_1 * V_semantic + eta_2 * V_graph + eta_3 * V_operational
```

This supports the user's code mesh matrix goal: construction should be judged by
preserved graph meaning and tested behavior, not only surface syntax.

## Error Handling

The router must fail usefully:

- If authority is missing, return `NO_WATCH` with an unlock condition.
- If a tool is unavailable, downgrade to `YES_BRIEF` or fallback tooling.
- If a tool loop is detected, stop and write a loop marker into squad state.
- If fog-of-war expands faster than certainty, switch to Scout + Science mode.
- If execution succeeds but evidence is missing, mark result incomplete.
- If shared state conflicts with private pad state, leader zone wins until
  reconciliation.

## Testing Plan

Minimum implementation tests:

1. Classifies unsafe/missing-permission tasks as `NO_WATCH`.
2. Classifies plain explanation tasks as `YES_BRIEF`.
3. Classifies filesystem/tool tasks as `YES_OPERATE`.
4. Maps each branch to valid Polly Pads modes.
5. Preserves HOT/SAFE tool constraints from `polly-pad-runtime`.
6. Updates fog-of-war state after an exploration action.
7. Detects a repeated tool loop and routes to fallback.
8. Produces an evidence packet for executed tool tasks.
9. Keeps private pad state separate from shared squad state.
10. Promotes only when build, test, and guardrail checks pass.

## First Implementation Slice

Add a small deterministic router before building any UI:

```text
packages/agent-bus/src/workroom-router.ts
packages/agent-bus/src/workroom-state.ts
packages/agent-bus/test/workroom-router.test.ts
```

CLI surface:

```text
scbe workroom route --task "..."
scbe workroom state
scbe workroom fog
```

Agent-bus tool:

```text
workroom-route
```

The first slice should not execute arbitrary tools. It should classify, explain,
assign roles, and declare required evidence. Execution can be added after the
router proves stable.

## Acceptance

The design is ready when:

- branch output is deterministic for fixture tasks;
- role assignment uses Polly Pads modes;
- fog-of-war state is visible in CLI output;
- every route has either a fallback or evidence requirement;
- tests pass without live model calls;
- the spec remains tied to source files and `notes/Untitled.md`.
