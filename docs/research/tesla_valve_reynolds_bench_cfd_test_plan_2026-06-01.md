# Tesla-Valve Reynolds Gate Bench and CFD Test Plan

**Status**: decisive physics gate; not flight validation  
**Date**: 2026-06-01  
**Pre-registration (binding eval):** `docs/protocols/PRE_REGISTRATION_TESLA_REYNOLDS_VALIDATION_v1.md` — freeze before bench/CFD  
**Related disclosure**: `docs/legal/patent-workbench/invention-disclosures/DIRECTIONAL_KINETIC_RECTIFIER_TRANSPIRATION_SKIN_DISCLOSURE_DRAFT_2026-06-01.md`

## Purpose

This test plan answers the first load-bearing physics question:

> Does the selected Tesla-style or asymmetric pore geometry produce useful forward/reverse pressure-drop asymmetry at the Reynolds-number range expected for the target transpiration pore?

The current particle model is useful for geometry screening only. It is not Navier-Stokes CFD, not pressure-drop data, and not evidence that a Tesla pore works in a low-Reynolds-number transpiration regime.

## Definitions

Reynolds number:

```text
Re = rho * U * D_h / mu
```

Where:

- `rho` = coolant density
- `U` = mean channel velocity
- `D_h` = hydraulic diameter
- `mu` = dynamic viscosity

Diodicity / rectification can be measured two equivalent ways:

```text
D_pressure(Q) = DeltaP_reverse(|Q|) / DeltaP_forward(|Q|)
D_flow(DeltaP) = Q_forward(|DeltaP|) / Q_reverse(|DeltaP|)
```

Recommended interpretation at target `Re`:

| Result | Interpretation |
|---|---|
| `D < 1.2` | Directional geometry is not load-bearing; pivot away from Tesla-pore broad claims. |
| `1.2 <= D < 1.5` | Weak asymmetry; useful only as a dependent geometry detail. |
| `1.5 <= D < 2.0` | Potentially useful if pressure penalty and manufacturability are acceptable. |
| `D >= 2.0` | Strong enough to keep as a serious embodiment. |
| `D >= 3.0` | Strong result for bench/CFD evidence, still not flight validation. |

## Critical Risk

Tesla valves rely on inertial separation, jetting, and vortex formation. Many transpiration pores operate in low-Reynolds-number or Darcy-like regimes where viscous forces dominate and diodicity may collapse toward 1.0.

If the target operating regime is low-Re and the CFD/bench result shows `D ~= 1`, the invention should pivot toward:

- pressure-biased micro-orifices
- asymmetric compliant cells
- optimized aperiodic pore fields
- MEMS pressure telemetry and FDIR
- active plenum/coolant regulation

## Bench Test A: Macro Geometry Sanity Check

This test proves only that the geometry can rectify at a bench-accessible scale. It does not prove transpiration-scale operation.

### Hardware

- Printed Tesla/labyrinth block, PLA or resin
- Straight-channel control block with matched hydraulic diameter and length
- Tapered/labyrinth control block
- Aquarium pump, small blower, or regulated compressed-air source
- Differential manometer or differential MEMS pressure sensor
- Flow meter or rotameter
- Tubing, clamps, and leak-check fittings

### Procedure

1. Leak-check all blocks and fittings.
2. Measure forward pressure drop through the straight control at multiple flow rates.
3. Measure reverse pressure drop through the same control to confirm symmetry.
4. Repeat for tapered/labyrinth block.
5. Repeat for Tesla/labyrinth candidate.
6. Calculate `Re` for each flow point.
7. Plot `D_pressure(Q)` and `D_flow(DeltaP)` against `Re`.
8. Record photos, block geometry, channel dimensions, raw pressure, raw flow, temperature, and air-density assumptions.

### Controls

- Straight channel: expected `D ~= 1.0`.
- Tapered/nozzle-diffuser channel: expected weak/moderate asymmetry depending on Re.
- Tesla/labyrinth: must outperform both controls at the same `Re` to matter.

### Bench Limitation

A macro printed block usually tests a different `Re`, roughness, and wall-temperature regime than a micro TPS pore. Treat a positive bench result as "geometry can rectify," not "flight pore solved."

## CFD Case B: Reynolds-Matched Channel Sweep

This is the higher-value gate because it can directly sweep the suspected target `Re`.

### Solver

Use SimScale/OpenFOAM, OpenFOAM locally, or another CFD package with laminar incompressible capability.

Start with laminar, isothermal, incompressible flow. Add compressible/hot-gas physics only after the directional pressure-drop gate is passed.

### Geometry

Run at least three geometries:

1. Straight channel control
2. Tapered/labyrinth control
3. Tesla/labyrinth candidate

Keep hydraulic diameter, total length, wall roughness assumptions, and inlet/outlet area comparable.

### Boundary Conditions

Run both matched-flow and matched-pressure cases:

- fixed mass flow or velocity inlet, pressure outlet
- fixed pressure drop, outlet reference pressure
- reverse direction using identical magnitude boundary conditions

### Reynolds Sweep

Minimum sweep:

```text
Re = 0.1, 1, 5, 10, 50, 100, 200, 500
```

If target pore conditions are known, add points bracketing the exact target range.

### Mesh and Convergence

- No-slip walls
- Refine near diverters, bends, and recirculation pockets
- Residual target: `<= 1e-5` where practical
- Mass-balance error: `<= 1%`
- Mesh independence: at least coarse/medium/fine comparison for the final candidate

### Outputs

- `DeltaP_forward`
- `DeltaP_reverse`
- `D_pressure`
- forward/reverse velocity streamlines
- pressure contours
- recirculation zones
- wall shear and stagnant zones
- flow separation onset versus `Re`

## Decision Gate

| Finding | Decision |
|---|---|
| Tesla/labyrinth `D < 1.2` at target Re | Drop Tesla as a load-bearing claim; keep only as optional geometry. |
| `D >= 1.5` but only at high Re outside target | Keep for macro ducts; do not use for micro-transpiration claims. |
| `D >= 2.0` inside target Re | Keep directional pore geometry as a serious embodiment. |
| Straight/tapered control performs as well as Tesla | Broaden to asymmetric microchannel geometry; avoid Tesla-specific dependence. |
| Pressure penalty kills film flow | Pivot to pressure-regulated plenum + MEMS/FDIR + quasi-lattice layout. |

## Filing and Pitch Rule

Do not present the Tesla-valve pore as solved until this gate is complete. Until then, use this language:

> Directional microchannel geometry is a candidate embodiment. Current reduced models justify CFD and bench testing but do not yet establish pressure-drop diodicity at the target transpiration-pore Reynolds number.

## Facility Targeting Note

PNNL-Sequim is useful for marine/coastal device, corrosion, biofouling, and in-water testing contexts. It is not the right first target for hypersonic thermal-protection or arc-jet coupon validation. For aerothermal TPS, target NASA Ames/Langley arc-jet capabilities, AFRL, CUBRC, or university aerothermal labs with relevant high-enthalpy flow facilities.
