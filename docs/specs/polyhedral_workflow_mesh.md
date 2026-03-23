# Polyhedral Workflow Mesh Spec

## Purpose

The polyhedral workflow mesh is a thin coordination pattern built from three real implementation surfaces:

- `scripts/system/workflow_vector.py`
- `scripts/system/goal_race_loop.py`
- `scripts/system/crosstalk_relay.py`

It is not a separate runtime today. It is a governed composition of:

1. a vector-to-action activation surface,
2. a lane-and-checkpoint packet generator,
3. a multi-lane relay bus for agent handoff and verification.

This spec defines the mesh using polyhedral terms while staying constrained to the code that already exists.

## Real Surfaces

| Mesh term | Implementation surface | Concrete outputs |
| --- | --- | --- |
| Face activation | `workflow_vector.py` -> `parse_z()`, `workflow_from_z()` | `enabled`, `active`, `workflow_signature` |
| Face packetization | `goal_race_loop.py` -> `build_packets()` | `Packet` records with `task_id`, `owner_role`, `phase_id`, `dependencies`, `checkpoint` |
| Edge scoreboard | `goal_race_loop.py` -> `build_scoreboard()` | `scoreboard.json`, lane status summary, checkpoint counts |
| Relay bus | `crosstalk_relay.py` -> `emit_packet()` | dated JSON packet, JSONL lane bus, Obsidian cross-talk entry |
| Relay verification | `crosstalk_relay.py` -> `verify_packet()`, `ack_packet()`, `pending_for_agent()`, `health_report()` | delivery proof, ACK trail, pending queues, bus health |

## Polyhedron Model

The mesh should be treated as a five-face control polyhedron with one shared relay spine.

### Face 1: Activation Face

`workflow_vector.py` maps a five-dimensional vector `Z` onto the fixed `ACTIONS` list:

- `notion_sync`
- `obsidian_snapshot`
- `git_commit`
- `dropbox_backup`
- `zapier_emit`

Each element becomes active when `z[i] >= threshold`. The script returns:

- `z`
- `threshold`
- `enabled`
- `active`
- `workflow_signature`

This face answers one question: which workflow surfaces should be live for this run?

Current boundary:
- The vector does not automatically invoke the other scripts.
- Operators or higher-level tooling must use `active` and `workflow_signature` to decide whether to create a goal race, snapshot state, emit to Zapier, or persist artifacts elsewhere.

### Face 2: Packet Face

`goal_race_loop.py` turns one user objective into a tracked multi-lane run.

The core packet surface is the `Packet` dataclass with these fields:

- `task_id`
- `owner_role`
- `phase_id`
- `goal`
- `recommended_skills`
- `inputs`
- `allowed_paths`
- `blocked_paths`
- `dependencies`
- `done_criteria`
- `return_format`
- `checkpoint`

This is the mesh face that converts intent into work units. It does not execute agents. It writes coordination artifacts that other agents can consume.

### Face 3: Checkpoint Face

The checkpoint face is compiled directly inside `build_packets()`.

A packet becomes a checkpoint when its `phase_id` is one of:

- `verify`
- `gate`
- `review`
- `followup`
- `repair`
- `ship`

This means checkpointing is deterministic and phase-driven, not inferred from agent behavior.

Operational meaning:

- a checkpoint packet marks a verification boundary,
- downstream relays should preserve proof and next action,
- scoreboard summaries should count these packets separately from ordinary work packets.

### Face 4: Scoreboard Face

`build_scoreboard()` creates the mesh scoreboard for a run. The scoreboard currently tracks:

- `run_id`
- `goal`
- `mode`
- `created_at`
- `lanes`
- `total_tasks`
- `completed_tasks`
- `checkpoint_tasks`
- `status`

Each lane row includes:

- `lane`
- `status`
- `tasks`
- `completed`
- `checkpoints`
- `skills`

This face is the current state plane for the mesh. It is generated at run creation time and gives operators a stable reference for ownership and relay order.

Current boundary:
- The scoreboard is written once at generation time.
- There is no automatic mutation of `completed_tasks` or lane `status` based on later relay ACKs.
- Any live scoreboard behavior must be layered on top of the current artifacts, not assumed to exist in the scripts today.

### Face 5: Relay Face

`crosstalk_relay.py` is the transport and verification face for the mesh.

`emit_packet()` writes one cross-talk packet to three lanes:

1. dated JSON in `artifacts/agent_comm/<YYYYMMDD>/`
2. JSONL bus in `artifacts/agent_comm/github_lanes/cross_talk.jsonl`
3. Obsidian mirror in `Cross Talk.md` when the vault is available

The relay packet includes:

- `packet_id`
- `created_at`
- `session_id`
- `codename`
- `sender`
- `recipient`
- `intent`
- `status`
- `repo`
- `branch`
- `task_id`
- `summary`
- `proof`
- `next_action`
- `risk`
- `where`
- `why`
- `how`
- `gates`
- `_integrity`

This face is the mesh transport plane. It is how work crosses from one face owner to the next without requiring a shared process.

## Edges

In this mesh, edges are the concrete handoff paths between faces.

### Edge A: Vector -> Packet

This edge is procedural today.

- `workflow_vector.py` chooses which action surfaces are active.
- an operator or wrapper decides whether that activation justifies running `goal_race_loop.py`
- `workflow_signature` can be recorded beside the generated run artifacts to identify the activation pattern that produced the race

This edge is not automated in the existing codebase, so the spec treats it as a policy edge, not a code-bound edge.

### Edge B: Packet -> Scoreboard

This edge is implemented directly.

- `build_packets()` returns ordered packet records with explicit `dependencies`
- `build_scoreboard()` derives per-lane task ownership and checkpoint counts from those packets
- `main()` writes both `packets.json` and `scoreboard.json` into the same run directory under `artifacts/goal_races/<run_id>/`

This is the strongest implemented edge in the mesh because it is synchronous and artifact-backed.

### Edge C: Packet -> Relay

This edge is implemented by convention rather than automatic wiring.

- each `Packet.task_id` is a valid relay reference for `crosstalk_relay.py emit`
- `summary`, `proof`, and `next_action` from a completed lane packet should be emitted as a cross-talk packet to the next lane owner or integrator
- checkpoint packets should always emit relay proof before a downstream lane continues

The edge is real because the packet schema and relay schema both expose `task_id`, `summary`, `proof`, and `next_action`, even though there is no direct function call from one script into the other.

### Edge D: Relay -> Verification

This edge is implemented directly inside `crosstalk_relay.py`.

- `verify_packet()` confirms that a relay packet landed on all configured lanes
- `ack_packet()` records consumption on `cross_talk_acks.jsonl`
- `pending_for_agent()` shows unconsumed packets per recipient
- `health_report()` provides a system-wide relay scoreboard

This is the mesh integrity edge.

## Relays

The relay model is tri-lane plus ACK:

- data lane: dated JSON packet file
- bus lane: append-only JSONL event bus
- mirror lane: Obsidian markdown mirror
- receipt lane: ACK JSONL log

Relay guarantees provided by the current implementation:

- deterministic packet IDs based on sender, task slug, and UTC stamp
- content integrity hash via `_packet_hash()`
- multi-lane delivery accounting through `delivered`, `total_lanes`, and `all_delivered`

Relay guarantees not currently provided:

- automatic retry
- scoreboard mutation after ACK
- packet-to-goal-race reconciliation
- lane-specific backoff or rate control

## Checkpoints

Checkpoints are not abstract review ideas in this mesh. They are explicit artifact markers.

### Compile-time checkpoint trigger

`goal_race_loop.py` marks packet checkpoints from phase membership.

### Relay-time checkpoint proof

When a checkpoint packet completes, the relay payload should include:

- `task_id`
- one short `summary`
- one or more `proof` paths
- a concrete `next_action`

### Consumption checkpoint

The checkpoint is not operationally closed until the receiving agent or owner ACKs the packet through `ack_packet()`.

## Scoreboards

The mesh has two scoreboards today.

### Run scoreboard

Source: `artifacts/goal_races/<run_id>/scoreboard.json`

Use for:

- lane ownership
- task count
- checkpoint count
- initial race status

### Relay scoreboard

Source: `crosstalk_relay.py health`

Use for:

- total bus packets
- latest packet timestamp and task
- dated JSON packet counts
- Obsidian lane health
- ACK totals by agent
- pending packet counts for known agents

The run scoreboard tracks planned work. The relay scoreboard tracks delivery health. Together they form the current mesh scoreboard system.

## Triggers

The mesh has four trigger classes grounded in current code.

### 1. Threshold trigger

Defined in `workflow_vector.py`.

Condition:
- `z[i] >= threshold`

Effect:
- corresponding action face is enabled

### 2. Run creation trigger

Defined in `goal_race_loop.py main()`.

Condition:
- operator invokes `--goal`
- optional `--mode`
- optional `--lanes`

Effect:
- writes `packets.json`
- writes `scoreboard.json`
- writes `README.md`

### 3. Checkpoint trigger

Defined in `build_packets()`.

Condition:
- packet phase is one of the checkpoint phases

Effect:
- packet `checkpoint` is set to `true`
- checkpoint counts are surfaced in the scoreboard

### 4. Relay trigger

Defined in `crosstalk_relay.py` CLI subcommands.

Condition and effect:

- `emit`: create and distribute a packet
- `verify`: confirm delivery
- `ack`: record receipt
- `pending`: show outstanding packets for an agent
- `health`: inspect overall relay bus health

## Reference Operating Sequence

The mesh should currently be operated in this order:

1. Compute action activation with `workflow_vector.py`.
2. Generate the run mesh with `goal_race_loop.py`.
3. Distribute completed packet state between owners with `crosstalk_relay.py emit`.
4. Verify high-value relays with `verify`.
5. Close receipt loops with `ack`.
6. Use `health` and the run scoreboard together when debugging stalls or missed handoffs.

## Concrete Command Pattern

Vector activation:

```bash
python scripts/system/workflow_vector.py --z 1,1,0,1,0 --threshold 0.5
```

Goal race generation:

```bash
python scripts/system/goal_race_loop.py --goal "Launch governed browser workflow" --mode browser
```

Relay handoff:

```bash
python scripts/system/crosstalk_relay.py emit --sender agent.alpha --recipient agent.beta --intent sync --task-id browser-verify --summary "Checkpoint passed" --proof artifacts/goal_races/<run_id>/scoreboard.json --next-action "Advance to repair or ship."
```

Relay verification:

```bash
python scripts/system/crosstalk_relay.py verify --packet-id <packet-id>
```

Receipt ACK:

```bash
python scripts/system/crosstalk_relay.py ack --packet-id <packet-id> --agent agent.beta
```

## Non-Goals and Present Gaps

This spec intentionally does not claim the following exist today:

- automatic chaining from workflow vector output into goal race generation
- automatic relay emission from packet completion
- automatic scoreboard updates from relay ACKs
- autonomous task execution inside `goal_race_loop.py`
- dynamic rebalancing of lanes from relay health data

Those are integration opportunities, not current behavior.

## Skill Contract

The polyhedral workflow mesh skill should be treated as a documentation-backed operating pattern with these rules:

- use `workflow_vector.py` to decide which workflow faces are active,
- use `goal_race_loop.py` to compile the run into owned packets and checkpoints,
- use `crosstalk_relay.py` to move state between owners with proof,
- treat `scoreboard.json` as the planned race state,
- treat relay health and ACKs as the delivery state,
- never describe automatic coupling that is not present in the current scripts.

That is the concrete mesh available in the repository now.
