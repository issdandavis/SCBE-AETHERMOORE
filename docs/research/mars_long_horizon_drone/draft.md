# Mars Long Horizon Drone Source Map

## Purpose

This map consolidates the scattered Mars, drone, NPC, spatial movement, and governed-training notes into one build frame for AetherDesk and MAHSS.

The core idea is simple: agent workflows are game actors. An NPC and an AI workflow both read world state, choose an action, mutate state, and report what happened. The useful difference is the world they operate in. For AetherDesk, the world is files, tests, tools, models, cloud lanes, local storage, and receipts. For the Mars drone work, the world is terrain, hazards, power, comms, home route, science targets, repair state, and nested carriers.

## Main Thesis

Build a Mars long-horizon game gym where free local LLMs are routed through systems like game NPCs:

```text
world_state
-> actor_observation
-> route / intent
-> policy gate
-> move/action
-> world_delta
-> receipt
-> next tick
```

The pasted notes add the missing long-horizon architecture:

```text
micro drones -> meso carriers/builders -> macro Mars vehicles
```

Micro drones are fast, cheap, and surgery-scale. Meso drones carry, relay, build, and repair. Macro vehicles execute long-horizon Mars mission objectives. The same movement and governance machinery can also model medical dual-use, but that lane must stay explicitly safety-gated and clearly separated from prototype game/simulation work.

## Source Clusters

### Mars Mission Compass

`docs/specs/GEOSEAL_MARS_MISSION_COMPASS_v1.md` and `src/geoseal_mission_compass.py` are the strongest Mars anchor. They already define terrain samples, hazard/risk metrics, minimap cells, routes, action packets, home/base navigation, science sampling, fault stabilization, and compressed handoff.

Use this as the task compiler for the Mars game gym. A mission packet becomes a board state; each agent action becomes a move; each result emits a receipt.

### Mars Long Horizon Simulation

`scripts/sim_mars_47step.py` is the closest local "long horizon" source. It models multi-step state, trust, memory, breaches, and recovery. It should become the blackout/resumption and mission-aging layer for the Mars gym.

### Drone Actors

`src/fleet/polly-pads/drone-core.ts` and `src/fleet/polly-pads/modes/navigation.ts` already provide drone identity and movement behavior: drone classes, trust radius, capability loading, route planning, terrain analysis, and obstacle detection.

These can become the actor templates:

```text
RECON -> map terrain
CODER -> patch / automate
DEPLOY -> release or recover drones
RESEARCH -> science sampling
GUARD -> safety and authorization
```

### Game And NPC Layer

`game/godot/scripts/companion/companion_ai.gd` gives the local NPC model: follow, idle, assist, autonomous. `game/godot/scripts/scbe/scbe_client.gd` gives the event bridge. `src/symphonic_cipher/scbe_aethermoore/game/training_pipeline.py` already knows event types like `npc_dialogue`, `exploration_action`, `companion_command`, and `tower_strategy`.

This is the evidence for the user's point: the difference between an NPC and an AI workflow is mostly the place. The scheduler, state, action, and receipt shape are the same.

### Spatial And Movement Layer

`examples/spatial_engine.py` and the Obsidian `3D Spatial Engine.md` define the 3D vector and tongue-space basis: `Vec3`, `Mat4`, `SpatialArray`, spiral traversal, and tongue ownership.

`packages/agent-bus/docs/PATHFINDING_HARNESS_EVIDENCE.md` adds governed pathfinding: projection board, vector-field nav, hidden lattice state, heat maps, pressure sensing, and evidence scoring.

`src/neurogolf/move_family.py` gives a compact move algebra: named moves, inverses, composition, cost, and topology vectors.

Together these are the movement vocabulary for the Mars/NPC gym.

### Governed Training Loop

`python/helm/verified_trajectory.py` is the bridge into training. It captures verified trajectories rather than static answers. This matters because the Mars gym should train agents on procedure:

```text
observe -> choose route -> act -> verify -> repair -> receipt
```

The pasted notes also point to the next small code step: a Poincare distance helper. That helper should not start as a giant governance system. It should start as a tested math primitive:

```text
poincare_distance(u, v)
authorize_radius(point, center, radius)
```

Then the Mars gym can attach hyperbolic authorization metadata to each route, move, repair, and training trajectory.

### Formation, Squad, And Flight Doctrine

The fleet documents add the clone-trooper-style command layer. The important parts are not military aesthetics; they are role discipline, formation geometry, mission phase, and bounded command authority.

`docs/specs/MASTER_ARCHITECTURE_CONTRACT_21D_M4_SQUAD.md` freezes the 21D/M4/squad deployment backbone. `docs/specs/SCBE_FLEET_GOVERNANCE_GATE.md` defines the command-authority gate: operation class, actor clearance, fleet posture, quorum, and fail-closed decision. `src/fleet/polly-pads/squad.ts` gives the BFT squad abstraction, while `src/fleet/polly-pads/mission-coordinator.ts` adds mission phases, mode assignment, voting, and crisis response.

The Obsidian `Gacha Squad System Design.md` gives the leader/follower doctrine:

```text
leader model -> squad members -> adversaries
```

and maps the six tongues to battlefield-style roles:

```text
KO scout
AV sniper/sensor
RU support
CA tank/shield
UM stealth/flank
DR adjutant/validator
```

For MAHSS and AetherDesk, these become software mission roles, not literal combat orders:

```text
scout -> map unknown workspace/terrain
sensor -> detect hazards and drift
support -> route resources and recovery
shield -> enforce policy and rollback
stealth -> isolate risky or private lanes
adjutant -> validate receipts and command chain
```

`src/ai_brain/swarm-formation.ts` is the runtime formation manager. It tracks formation type, position, role, health, coherence, and trust-weighted votes. `external/codex-skills-live/scbe-github-sweep-sorter/references/formations.md` adds the practical collaboration formations, with an explicit note that they are for software collaboration, not literal military automation.

The actual flight-specific modules are:

- `src/fleet/drone-fleet/sacredTonguesFlight.ts`: maps six-tongue commands to flight behavior and compact command encoding.
- `src/fleet/drone-fleet/gravitationalBraking.ts`: measures divergence from an authorized flight path and emits braking/neutralization factors for simulation.
- `src/fleet/drone-fleet/dimensionalLifting.ts`: lifts control-flow graphs into higher-dimensional structures for repeatable security checks.

This is the missing bridge between Mars mission packets and fleet doctrine:

```text
mission_phase -> formation -> squad roles -> flight/move command -> authorization -> receipt
```

### Endless Sky And Other GitHub Game Repos

The local Endless Sky research note and the public `issdandavis/endless-sky` fork are high-value because Endless Sky is already a space exploration, trading, combat, faction, mission, and fleet game with data-driven behavior. The note identifies:

- 699 star systems and 1,637 hyperspace links
- 131 factions/governments
- 310 planets/stations
- 14 fleet formations
- NPC AI methods for formation flying, escorting, mining, patrol, surveillance, route planning, help coordination, and strength tracking

This is a better source for mission/flight game mechanics than inventing everything from scratch. The safe use is to parse it as a simulation/game substrate and generate original receipts/training traces from agent play. Licensing matters: the fork is GPL-3.0, so derived redistributed datasets or code need proper handling.

### Materials, PUF, And Physical Identity

The materials docs are a separate but important evidence cluster. They do not prove flight hardware, but they give the hardware-identity and measurement lane that can support autonomous drones later.

`research/materials/README.md`, `research/materials/source-inventory.md`, and `research/materials/product-map.md` consolidate the local materials work into a product/research surface. The repo already has AI-facing surfaces for this work:

- `docs/ai-materials-bench.html`
- `docs/ai-waves-lab.html`
- `docs/ai-chemistry-set.html`
- `research/materials/waves/research_brief.md`

For the Mars/space gym, these are not just documents. They can become science-set adapters: wave propagation checks, chemistry constraints, material selection tasks, optical/transistor simulations, and physics receipts.

The PUF lane is especially useful because the repo already contains the hard correction from the user's pasted notes:

```text
deterministic seeded topology != standalone PUF
```

`docs/specs/AETHERFAB_PUF_NEGATIVE_RESULT.md` parks the raw seeded-topology approach as a negative result. At realistic printer tolerances, same-seed clone pairs are too close to the original; deterministic geometry alone is not unclonability.

`docs/specs/SACRED_EGG_CRP_PUF_HARNESS.md` is the forward path. It reframes the problem as challenge-response physical measurement:

```text
device_id + challenge_id + physical read
-> response vector
-> genuine / impostor / cross-challenge distances
-> entropy estimate
-> verdict
```

The corresponding experiment files are:

- `scripts/experiments/puf_measurement_analysis.py`
- `scripts/experiments/sacred_egg_crp_puf_analysis.py`

This maps cleanly onto drone trust. A simulated drone can carry a hardware identity receipt, and later a physical drone could enroll measured response distributions. The safe build lane is a synthetic materials identity gym first:

```text
challenge_id -> response vector -> quantize -> compare -> entropy floor -> sealed receipt
```

The conductive polymer aerogel and bio-interface notes from the current chat should be treated as research intent until they are converted into a local literature-backed doc or experiment. They belong under the materials bench as porous conductive material research, with explicit claim boundaries.

### Space Systems

The space docs are another source cluster, not a single implementation. `docs/research/topics/space-systems.html` is the local topic index. It groups:

- M-TEF research
- chemistry-native space systems
- GeoSeed orbital analogy
- life-support animals, husbandry, and micro-energy concepts

The strongest implementation-facing space files are:

- `src/physics_sim/orbital.py`: orbital period, velocity, energy, transfer, plane change, hyperbolic trajectory, J2, and Lagrange helpers.
- `src/crypto/flight_dynamics.py`: QHO-style excitation mapped into flight energy, flight-envelope checks, and tongue-to-control-surface mapping.
- `src/scbe_spaceflight.py`: delay-tolerant bundles, hyperbolic trajectory analogy, docking, reentry, star tracking, and constellation formation voting.
- `src/geoseed/orbital_model.py`: deterministic Sacred Tongue / Sacred Egg orbital-shell analogy.
- `src/harmonic/vacuumAcoustics.ts`: vacuum/acoustics model surface.

The research-facing space files add claim boundaries:

- `docs/research/chemistry_cli_space_systems_2026-05-31.md` frames a governed chemistry CLI bridge to RDKit/Open Babel/ASE/DeepChem and NASA-adjacent data sources, but not official certification or autonomous instrument control.
- `docs/research/mtef_research_compendium_2026-06-17.md` supports component-level plausibility for harvesters, ferrofluids, liquid metals, microgravity fluids, and power-management circuits, but not an integrated flight-ready M-TEF device.
- `research/mtef-cell/README.md` and `research/mtef-cell/docs/space-use-case.md` frame M-TEF as distributed recovery for sensors, telemetry, emergency micro-actuation, and exercise-equipment energy recovery, not station-scale power.
- `docs/research/space_life_support_animals_husbandry_energy_2026-06-17.md` is a research scaffold for habitat telemetry, husbandry, welfare boundaries, and micro-energy recovery, not a claim that animals power spacecraft.
- `docs/research/vr_ai_operations_game_substrate.md` defines a playable spatial operations substrate with rooms, tools, drones, tethers, and verified task loops, while explicitly avoiding claims of physical drone capability, aerospace certification, or NASA endorsement.

This space cluster should become the `space_mission_gym`: a simulation board where orbital and flight constraints are evidence checks, not marketing claims.

## Build Lanes

### Lane 1: Mars Scenario For MAHSS Game Gym

Add a `mars` scenario to `scripts/system/mahss_game_gym.py` that uses `build_mars_mission_compass` output as world state.

The first scenario should score:

- terrain cells mapped
- hazards avoided
- home route preserved
- science target sampled
- fault stabilized
- receipt completeness

### Lane 2: Nested Drone Orchestrator

Create a small orchestrator that models:

- micro drone: inspect, repair, sample, dock
- meso drone: carry, deploy, recover, relay, build
- macro vehicle: navigate, host, power, handoff

The important relationship is containment and dispatch:

```text
macro.deploy(meso)
meso.deploy(micro)
micro.repair(target)
micro.return_to(meso)
meso.return_to(macro)
```

### Lane 3: Spatial Move Vocabulary

Unify `NavigationMode`, vector-field pathfinding, and `Move` into one schema:

```text
move_id
actor_scale
from_state
to_state
cost
risk
inverse
receipt
```

This is where the game analogy becomes concrete: local LLMs do not need to "understand Mars"; they need to pick legal moves against a world-state API.

### Lane 4: Poincare Authorization

Implement the math helper first, then wire it into trajectory records.

Candidate receipt fields:

```json
{
  "auth_space": "poincare_ball_v1",
  "intent_radius": 0.42,
  "safe_radius": 0.75,
  "decision": "allow"
}
```

### Lane 5: Godot Event Bridge

Mirror the same scenario into Godot event packets through the existing client/event pipeline. This lets the Mars gym be visualized as a game world and harvested as training data.

### Lane 6: Mission And Formation Controller

Add a small controller table that maps mission phase to formation, roles, update cadence, and safety gate:

```text
survey -> spread/search formation -> scout + sensor + validator
transit -> convoy/escort formation -> navigator + shield + comms
repair -> containment formation -> support + engineer + validator
sample -> precision formation -> scout + science + shield
blackout -> fallback formation -> validator + comms + home-route
```

The controller should only change formation at phase boundaries or after a receipt-backed trigger. That keeps latency down and prevents the fleet from thrashing.

### Lane 7: Materials Identity Gym

Add a synthetic hardware identity lane using the Sacred Egg CRP-PUF harness shape. The first implementation does not need physical sensors. It should generate deterministic-but-noisy response vectors and test whether the harness can separate:

- genuine repeated reads
- impostor devices
- cross-challenge responses

The receipt should report:

```json
{
  "device_id": "drone_001",
  "challenge_id": "geo_window_017",
  "verdict": "auth_candidate",
  "max_genuine": 0.04,
  "min_impostor": 0.19,
  "entropy_bits": 12.8
}
```

This directly supports the user's autonomous space-drone security direction without claiming that seeded material geometry is already a proven PUF.

### Lane 8: Space Mission Gym

Use the orbital, flight, M-TEF, chemistry, and spaceflight protocol files as constraint adapters:

```text
mission tick
-> orbital / flight constraint check
-> power and telemetry constraint check
-> chemistry/materials evidence check
-> spaceflight receipt
```

The first goal is a simulated mission board, not physical certification. That keeps the Mars/space work useful to AetherDesk immediately: local LLMs can be routed through tools, constraints, and receipts, like NPCs in a game world.

## What To Build First

The highest-leverage first implementation is small:

1. Add `mars` to the MAHSS game gym.
2. Feed it one deterministic Mars mission payload.
3. Emit a per-tick receipt with drone actions and world-state deltas.
4. Add a mission/formation controller table.
5. Add a Poincare helper as a separate tested primitive.
6. Add a CRP-PUF synthetic identity board after the Mars loop is working.
7. Add a space mission constraint adapter after the Mars loop is emitting stable receipts.

That gives the project a real loop:

```text
Mars packet -> game world -> NPC/drone actions -> receipts -> verified trajectory data
```

## Uncertainties

The current chat history title `Mars Long Horizon Drone Build` was visible in the user paste, but the full external chat transcript is not directly available from the filesystem. This map uses the current-turn pasted notes plus local repo/Obsidian files. Any claim from the pasted notes that is not backed by a repo file is treated as design intent, not verified implementation.
