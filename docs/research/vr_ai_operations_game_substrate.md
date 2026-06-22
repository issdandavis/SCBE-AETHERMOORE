# VR AI Operations Game Substrate

Date: 2026-06-18

Status: Concept note / product direction. This is not a claim of physical drone capability, aerospace certification, or deployed robotics readiness.

## Core Idea

Build a real playable game/simulation world that can also serve as an AI training and operations substrate.

The first product can be a game-like VR or 3D operations room. The deeper product is a shared world where a user and AI agents can inspect state, manipulate tools, run tasks, verify outcomes, and emit receipts.

```text
game world = visible state
player body = human control surface
AI NPC / armband = assistant and agent operator
objects = tasks, files, drones, tools, tests, permissions
rooms = work domains
tethers = dependencies, constraints, force paths, power/data lines
missions = real or simulated work objectives
receipts = audit trail of every move
```

The game layer is the interface. The real artifact is the action map, verifier, backend execution system, and training loop.

## Product Framing

This should not be marketed as a blank VR sandbox. It should be a prebuilt operational pattern:

```text
A playable spatial operations sim where humans and AI agents collaborate through rooms, tools, drones, tethers, and verified task loops.
```

The user can:

- code directly on a virtual desktop,
- point, grab, connect, approve, and route objects,
- type or talk to an armband assistant,
- assign work to AI NPCs,
- review and approve AI actions,
- learn from explanations when desired.

The AI can:

- act as an armband assistant,
- appear as an NPC coworker,
- inspect world state,
- propose routes and actions,
- operate simulated tools,
- run bounded backend commands,
- explain what it did,
- stop at approval gates.

Learning can be a mode, but the main goal is building real products and workflows.

## Why A Game

A game gives AI and humans a shared perceptual workspace.

Instead of:

```text
text prompt -> tool call -> text result
```

the system becomes:

```text
visible world -> embodied action -> feedback -> verification -> receipt
```

That gives small models and users a structured action surface. It also creates replayable training traces.

## Steam / Game Release Strategy

The product can be built as a playable game first, with AI as an optional, guarded layer.

Recommended release path:

1. Local prototype or itch.io build first.
2. Stable playable sim loop without requiring AI.
3. Steam demo only after the base game works.
4. AI features as opt-in experimental mode.
5. Clear disclosure for any AI-generated player-facing content.

Steam-relevant design boundary:

- The game should be playable without live AI.
- AI should operate through fixed actions and constrained tools.
- Live-generated AI content should have guardrails.
- Avoid unrestricted public text/image generation.
- Keep backend access sandboxed and approval-gated.

## First MVP

Build a small simulated operations room:

```text
Room 1: repo / mission map
Room 2: virtual desktop / code panel
Room 3: test console / verification gate
Room 4: drone/tether simulator
AI NPC: proposes and performs bounded actions
Armband: command palette and chat assistant
```

Minimal world objects:

- task board,
- simulated drone,
- tether line,
- target panel,
- tool crate,
- test gate,
- receipt printer,
- emergency stop.

Minimal actions:

```text
inspect
move_to
extend_tether
retract_tether
anchor
release
scan
run_test
patch
approve
rollback
return_home
emergency_stop
```

Minimal safety checks:

```text
power budget
tether tension
collision envelope
reachable zone
return path
permission gate
human approval requirement
```

Every run should emit a receipt:

```json
{
  "goal": "inspect panel A",
  "actions": [],
  "violations": [],
  "power_remaining": 0.73,
  "return_path_valid": true,
  "approved_by_user": true
}
```

## Space / Drone Direction

The long-range concept is a VR-supervised, AI-assisted tethered micro-robotics system for exterior inspection, maintenance, and dexterous work in constrained environments.

High-level abstraction:

```text
astronaut = supervisor / body-in-loop operator
VR visor = spatial command interface
AI = route planner + safety copilot + task assistant
main robot = mobile work platform
micro-drones = dexterous endpoint workers
tethers = power/data/force/scaffold/control geometry
ship exterior = constrained worksite
```

The tether is the strongest mechanical idea. It can act as:

- recovery line,
- power/data path,
- force reaction path,
- known geometry,
- travel envelope limiter,
- temporary rail,
- slack reach tool,
- stiffened boom,
- retractable guide,
- branched multi-tool limb.

This should be tested as simulation first, not hardware first.

## Safety Ladder

Safety comes from progressive evidence, not a single claim.

```text
1. deterministic sim tests
2. physics/tether stress tests
3. replayable mission traces
4. AI action constraints
5. human approval gates
6. hardware-in-the-loop only later
7. emergency stop and rollback
8. telemetry receipts
```

This mirrors the existing SCBE autonomy-training pattern:

```text
simulation -> instrumented range -> trust calibration -> runtime assurance -> live demo -> repair from failures
```

## Existing Local Anchors

Related local documents and code:

- `docs/research/drone_autonomy_training_patterns_2026-05-02.md`
- `docs/research/research_catalog.json`
- `src/fleet/drone-fleet/index.ts`
- `tests/fleet/drone-fleet.test.ts`
- `docs/hardware/CUBE_BRIDGE.md`
- `python/scbe/cube_bridge.py`
- `docs/benchmarks/RUBIX_BROWSER_HYPERCUBE_BENCHMARK.md`

These already provide pieces of the pattern: autonomy training stages, drone-fleet simulation modules, cube/controller input grammar, and permission-hypercube routing.

## Claim Boundary

This concept does not claim:

- physical drone capability,
- aerospace certification,
- NASA endorsement,
- safe real-world robot control,
- mature VR product readiness.

It claims a practical build direction:

```text
Start with a playable spatial operations simulator.
Use it to train, test, and operate AI agents through constrained actions.
Keep real-world robotics as a later adapter behind safety gates.
```
