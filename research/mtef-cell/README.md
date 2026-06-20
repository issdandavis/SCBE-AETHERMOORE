# M-TEF Cell — Magneto-Triboelectric Fluid Cell

**Status:** concept research + prototype-planning scaffold.
**Maturity:** component-level literature support exists, but the integrated M-TEF Cell is still unbuilt / unvalidated hardware. Treat this folder as a technical research package and prototype roadmap, not as a flight-qualified design.

## Core idea

The **M-TEF Cell** is a hybrid energy-harvesting concept that converts mechanical motion into electricity through two coordinated channels:

1. **Electromagnetic induction** — motion drives a magnet/piston through coils, producing a lower-voltage, higher-current output.
2. **Triboelectric liquid-solid generation** — droplets or moving fluid interfaces contact/separate against a triboelectric channel surface, producing a higher-voltage, lower-current output.

The key design principle is **three-fluid separation of concerns**:

| Layer | Job | Candidate materials |
|---|---|---|
| Magnetic control fluid | control, damping, field-guided motion | ferrofluid or magnetorheological fluid |
| Conductive droplet phase | charge collection / electrode interaction | Galinstan, eGaIn, ionic liquid, carbon/graphene suspension |
| Triboelectric dielectric/surface | contact electrification | PTFE / fluoropolymer channel, dielectric carrier fluid |

Instead of forcing one “miracle fluid” to be magnetic, conductive, triboelectric, vacuum-stable, and mechanically stable at once, M-TEF splits the functions so each layer can be independently optimized and replaced.

## Why this folder exists

This folder converts the uploaded research bundle into an engineering-facing GitHub project nested inside `SCBE-AETHERMOORE`:

- executive concept summary
- system architecture
- prototype roadmap
- validation plan
- draft bill of materials
- early power-estimation utility code
- reserved-rights license notice

## What is not proven yet

The research package supports the plausibility of the component technologies, but it does **not** prove that the integrated system will produce net positive useful power. The make-or-break technical question is whether a combined fluidic EM + TENG cell produces additive output, or whether drag, leakage, droplet coalescence, parasitic capacitance, or stability losses erase the benefit.

## Proposed development sequence

| Stage | Prototype | Goal | Decision gate |
|---|---|---|---|
| 1 | Coil-only piston | validate EM channel | measurable voltage/current vs stroke/frequency |
| 2 | Tribo droplet channel | validate liquid-solid TENG channel | stable droplet train + measurable charge/current |
| 3 | Combined EM + tribo cell | test coupling | combined output must beat either channel alone |
| 4 | Magnetic-control cell | add ferrofluid/MR control | stable control without unacceptable drag/stability loss |
| 5 | Vacuum / microgravity-relevant test | validate target environment | performance and stability under relevant pressure/orientation conditions |

## Target positioning

Do **not** position this as a replacement for solar arrays or station-scale power. The strongest technical and strategic position is:

> M-TEF is a **distributed recovery layer** for sensor power, health telemetry, emergency micro-actuation, and exercise-equipment energy recovery.

The best first application is likely an instrumented exercise/resistance device, vibration source, or wireless sensor node power module where small amounts of recovered power plus telemetry have higher value than raw wattage.

## Folder map

```text
research/mtef-cell/
├── README.md
├── docs/
│   └── research-packet.md
├── hardware/
│   └── bom-draft.md
├── prototypes/
│   └── prototype-roadmap.md
├── src/
│   └── mtef_model.py
├── tests/
│   └── test_mtef_model.py
├── pyproject.toml
├── requirements.txt
└── LICENSE.md
```

## Immediate next step

Build Prototype 1 and Prototype 2 separately before integrating them. Prototype 3 is the actual make/break cell.

## Rights / license

No open-source license is granted yet. See `LICENSE.md`. This is intentional because the concept may contain patent-sensitive system-integration material.
