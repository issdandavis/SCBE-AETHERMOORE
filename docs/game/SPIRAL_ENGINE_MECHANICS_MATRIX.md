# Spiral Engine Mechanics Matrix (Aethermoor)

## Core Loop

1. Navigate the Poincare Ball.
2. Route intent packets through Polly Pads and Sacred Tongues.
3. Accumulate trust/coherence while avoiding edge drift.
4. Resolve quarantine/deny pressure before exile thresholds.

## Modular Systems

1. Exploration and Map:
- Hyperbolic world with center-safe topology.
- Fog-of-war voxel discovery `[X,Y,Z,V,P,S]`.
- Safe highways built by repeatedly clearing low-risk routes.

2. Skill Trees and Leveling:
- Six Sacred Tongue branches (`KO AV RU CA UM DR`).
- Polly Pad specializations (`ENGINEERING NAVIGATION SCIENCE COMMS SYSTEMS MISSION_PLANNING`).
- XP currencies are trust and coherence.

3. Inventory and Crafting:
- Sacred Eggs as rare identity anchors.
- Craftables: audit proofs, consensus seals, spectral filters, quarantine resolvers.
- Leyline configuration loadouts combine tongue and pad boosts.

4. Procedural Generation:
- Deterministic seeded missions with region/faction/risk variation.
- Adversarial rhythms push embeddings toward edge pressure.
- Triadic watcher patterns create emergent threat cycles.

## Formula -> Mechanic Mapping

| Symbol | Formula | Mechanic | Player Feedback |
|---|---|---|---|
| `d` | `acosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))` | Distance from safe center | Heat/fog on map |
| `x` | `min(3, (0.5 + intent*0.25) * (1 + (1-trust)))` | Intent persistence | Rising heat meter |
| `H_eff` | `1.5^(d^2*x)` | Cost wall | Latency/friction storm |
| `harm` | `1/(1+log(max(1,H_eff)))` | Safety inversion | Green-to-red permission dial |
| `d_tri` | `(0.3*I_fast^phi + 0.5*I_memory^phi + 0.2*I_governance^phi)^(1/phi)` | Triadic pressure | Three guardian rings |
| `obs` | `Tarski postfixpoint obstruction from lattice sheaf flow` | Sheaf fracture pressure | Fault lines / instability seams |
| `sheaf_stability` | `1/(1+obs)` | Sheaf lock recovery | Sixth lock stabilizer |
| `Omega` | `pqc_valid*harm*drift_factor*triadic_stable*spectral_score*sheaf_stability` | Final gate | Door with six locks |

## Lock Semantics (Omega HUD)

`Omega` is shown as six lock channels:

1. `pqc_valid`
2. `harm`
3. `drift_factor`
4. `triadic_stable`
5. `spectral_score`
6. `sheaf_stability`

If any lock collapses toward zero, gate pressure increases and quarantine/deny risk rises.

## Visual Direction

- Tonal style: whimsical Aethermoor fantasy with deep governance mechanics.
- Poincare disc should glow and distort with curvature pressure.
- Polly raven acts as mission narrator and warning guide.
- Ring HUD displays watcher states and lock stability in real time.

## Runtime Contract (HUD)

The simulator now emits HUD payload per tick in `StateVector.hud`:
- `poincare_heat`
- `wall_pressure`
- `watcher_rings.fast`
- `watcher_rings.memory`
- `watcher_rings.governance`
- `watcher_rings.triadic`
- `gate_locks.pqc_valid`
- `gate_locks.harm`
- `gate_locks.drift_factor`
- `gate_locks.triadic_stable`
- `gate_locks.spectral_score`
- `gate_locks.sheaf_stability`
