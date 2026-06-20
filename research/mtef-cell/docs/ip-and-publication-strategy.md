# IP and Publication Strategy

## Patent-sensitive areas

The most defensible invention space appears to be system-level integration, not individual known components.

Potential claim areas for patent counsel to review:

1. three-fluid separation architecture for hybrid energy harvesting,
2. fluid-coupled EM + liquid-solid TENG generation in one cell,
3. cartridge-based replaceable fluid stacks for mission-specific materials,
4. dual-bus power management for EM and TENG outputs,
5. exercise-equipment integration where resistance, telemetry, and recovered power share a mechanical source,
6. magnetic-control layer for droplet/piston tuning inside the harvesting channel.

## Avoid premature public disclosure

Before publishing full implementation details, decide whether to file a provisional patent application. Public GitHub commits can count as disclosure.

Recommended public/private split:

| Public now | Hold until IP decision |
|---|---|
| high-level concept | exact channel geometry |
| prototype roadmap | exact fluid formulations |
| test methodology | integrated control topology |
| component literature summary | detailed claims and novelty diagrams |
| non-sensitive code utilities | CAD, PCB, COMSOL files |

## Publication ladder

Each prototype can become a standalone paper or technical note:

1. **Prototype 1:** EM piston harvester measurements.
2. **Prototype 2:** liquid-solid droplet TENG channel measurements.
3. **Prototype 3:** first integrated fluid-coupled EM + TENG cell.
4. **Prototype 4:** magnetic-control enhancement and stability study.
5. **Relevant-environment test:** vacuum/microgravity-relevant validation.

## Legal note

This repository is not legal advice. Patentability, freedom to operate, inventorship, ownership, and publication timing should be reviewed with qualified patent counsel before broad disclosure.
