# Spiral Engine Build Plan (Aethermoor)

## Vision

Build a strategy simulation where SCBE-AETHERMOORE governance math is the core gameplay loop.

Player fantasy:
- Route intent through curved space.
- Use Sacred Tongues + Polly Pad specializations to keep throughput high.
- Survive adversarial drift pressure without triggering deny/exile paths.

## MVP Scope (Confirmed)

1. Poincare ball arena with real hyperbolic distance.
2. Player movement with live `H_eff` and `Omega` computation.
3. Mission system with timed objectives.
4. Sacred Tongue selector affecting spectral score.
5. Triadic Watcher HUD (three-ring display).
6. Quarantine events with resolution choices.
7. Basic progression via trust/coherence accumulation.

## Canonical + Runtime Math

Canonical SCBE wall is preserved for governance parity:

`H(d*,R) = R * pi^(phi * d*)`

Runtime gameplay wall for heat/friction feedback:

`H_eff = 1.5^(d^2 * x)`

Safety conversion:

`harm = 1 / (1 + log(max(1, H_eff)))`

Triadic Watchers:

`d_tri = (0.3*I_fast^phi + 0.5*I_memory^phi + 0.2*I_governance^phi)^(1/phi)`

Final gate:

`Omega = pqc_valid * harm * drift_factor * triadic_stable * spectral_score * sheaf_stability`

## Sheaf Cohomology for Lattices (Gameplay Use)

We treat mission consistency as a cellular sheaf over a small lattice (nodes + edges):

- 0-cochains: local watcher/tongue values on nodes.
- 1-cochains: edge disagreements.
- Coboundary residual (`delta0`) approximates obstruction to global consistency.

Gameplay mapping:
- low obstruction => stable global section => easier ALLOW.
- high obstruction => fractured local patches => QUARANTINE/DENY pressure.

Implementation metric:

`sheaf_obstruction = mean(abs(delta0(edge)))`

`sheaf_stability = 1 / (1 + sheaf_obstruction)`

## Modular Systems

### Exploration and Map
- Poincare arena with fogged voxel claims.
- Deterministic voxel key format:
  - base: `base/X:Y:Z:V:P:S`
  - per tongue: `KO/X:Y:Z:V:PL:S`
- Deterministic shard:
  - `shard = sha256(base_key) % 64`

### Skill Trees and Leveling
- Tongue branches: `KO AV RU CA UM DR`.
- Polly Pad sub-trees:
  - `ENGINEERING`
  - `NAVIGATION`
  - `SCIENCE`
  - `COMMS`
  - `SYSTEMS`
  - `MISSION_PLANNING`
- XP currencies: trust XP + coherence XP.

### Inventory and Crafting
- Sacred Eggs as identity anchors.
- Craftables: consensus seals, spectral filters, quarantine resolvers, audit proofs.

### Procedural Generation
- Mission generation deterministic from seed.
- Adversarial rhythm modulates watcher intensities and drift pressure.

## Runtime Output Contract

Each tick emits:
- `StateVector` (deterministic technical state)
- `DecisionRecord` (action, signature, timestamp, reason, confidence)

## Build Artifacts

- Simulator: `scripts/spiral_engine_game_sim.py`
- Tests: `tests/test_spiral_engine_game_sim.py`
- Route chain: `scripts/route_spiral_engine_chain.yaml`
- World profile: `config/game/worlds/aethermoor.json`
- Module config: `config/game/modules/aethermoor_modules.json`
- Mechanics matrix: `docs/game/SPIRAL_ENGINE_MECHANICS_MATRIX.md`
