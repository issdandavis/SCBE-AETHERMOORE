# Mars Long Horizon Drone Outline

## 1. Mission Thesis

Nested micro, meso, and macro drone systems should be trained and governed like game-world actors: each actor observes local state, chooses a permitted move, changes world state, emits a receipt, and returns to the scheduler.

## 2. Source Clusters

### 2.1 Mars Mission Compass

Terrain, hazard, home routing, science sampling, code patching, and compressed handoff packets.

### 2.2 Nested Drone Notes

User-provided current chat notes describe micro surgery-scale drones, meso carrier/builders, macro Mars vehicles, a physical diorama, and medical dual-use.

### 2.3 Godot And NPC World Loop

Godot companion scripts, event logging, training pipeline, and Aethermoor Spiral engine provide the game/NPC substrate.

### 2.4 Movement And Spatial Relations

Spatial engine, search-space router, vector-field pathfinding, move algebra, and drone navigation modes define movement primitives.

### 2.5 Governed Training Loop

Verified-Trajectory Curriculum and hyperbolic authorization turn agent solves into execution-verified and policy-checked training data.

### 2.6 Formation, Squad, And Flight Doctrine

Fleet documents supply the clone-trooper-style hierarchy: leader, squad members, roles, formations, mission phases, consensus, and flight safety controls.

### 2.7 External Game Repos

The archived `issdandavis/endless-sky` fork and its local research note provide a data-driven space game substrate: galaxy graph, missions, factions, fleet formations, and NPC AI behavior.

### 2.8 Materials, PUF, And Physical Identity

Materials notes supply the hardware substrate lane: AI Materials Bench, Waves Lab, Chemistry Set, wave/optics research, M-TEF, and PUF harnesses. The repo already records the key guardrail: raw deterministic seeded topology is not a standalone PUF; the forward path is challenge-response physical measurement with entropy and separation checks.

### 2.9 Space Systems

Space systems docs supply orbital mechanics, flight dynamics, space chemistry, M-TEF, life-support/husbandry research boundaries, vacuum acoustics, delay-tolerant spaceflight protocols, and VR/spatial operations game substrate concepts.

## 3. Build Lanes

### 3.1 Mars Scenario For MAHSS Game Gym

Use Mars mission compass packets as game-world tasks.

### 3.2 Nested Drone Orchestrator

Represent micro, meso, and macro actors as layered agents with carrier/deploy/repair relations.

### 3.3 Spatial Move Vocabulary

Unify drone navigation, vector-field pathfinding, and move-family operations.

### 3.4 Poincare Authorization Gate

Add a small, testable hyperbolic distance helper and use it as an authorization receipt field.

### 3.5 Godot Bridge

Emit and ingest Godot-style event packets for companion/NPC behavior and world-state deltas.

### 3.6 Mission And Formation Controller

Map mission phase to formation, squad roles, update cadence, and flight authorization.

### 3.7 Materials Identity Gym

Turn PUF/CRP and materials measurement docs into a synthetic hardware-identity game lane: challenge, response vector, quantization, genuine/impostor separation, entropy floor, and sealed receipt.

### 3.8 Space Mission Gym

Use orbital mechanics, flight dynamics, spaceflight protocols, and M-TEF/space chemistry docs as adapters for mission constraints and evidence checks.

## 4. Open Questions

Which lane should be implemented first: Mars scenario, nested orchestrator, Poincare helper, Godot event ingestion, materials identity gym, or space mission gym?
