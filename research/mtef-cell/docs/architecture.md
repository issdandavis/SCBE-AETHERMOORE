# M-TEF System Architecture

## One-sentence architecture

A pressure pulse or mechanical stroke drives a coupled fluidic channel where one path produces electromagnetic induction through a moving magnetic element and another path produces triboelectric charge through controlled droplet contact/separation against a fluoropolymer surface.

## Design principle: separate the jobs

The core engineering insight is not “make a magic conductive ferrofluid.” The safer architecture is a separated stack:

1. **Magnetic control layer** handles field response, damping, restoring force, droplet/piston guidance, and optional tunability.
2. **Conductive droplet layer** handles charge collection and electrode interaction.
3. **Triboelectric interface layer** handles surface charge generation.

This avoids the failure path where conductivity destabilizes the ferrofluid, shorts triboelectric charge separation, or changes viscosity in ways that destroy controllability.

## Candidate physical layout

```text
Mechanical input
   │
   ▼
[pressure chamber / piston / oscillator]
   │
   ├── EM branch: moving magnet ↔ coil stack ↔ bridge rectifier ↔ storage capacitor
   │
   └── TENG branch: droplet train ↔ PTFE channel/electrodes ↔ high-voltage rectifier ↔ storage capacitor

Power manager:
   EM bus   → low-voltage / higher-current conditioning
   TENG bus → high-voltage / low-current conditioning
   Combined → sensor load, telemetry node, wake-up circuit, micro-actuator, emergency reserve
```

## Electrical architecture

The EM and TENG outputs should not be forced through a single naive rectifier. They have different source impedances and waveform behavior.

Recommended first architecture:

```text
EM channel    → low-loss bridge/synchronous rectifier → bulk capacitor → DC/DC regulator
TENG channel  → high-voltage rectifier/charge pump     → HV capacitor   → regulated wake/sensor rail
Combined rail → supercapacitor or LiFePO4 test pack, depending on lab constraints
```

## Control architecture

Prototype 1 and 2 should be passive. Active magnetic control is added only after the individual channels work.

Prototype 4 may add:

- bias magnets
- coil-driven field shaping
- MR damping region
- ferrofluid droplet positioning
- feedback from voltage/current/pressure sensors

## Main system risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Conductive shorting | conductive droplets can collapse the triboelectric field | isolate droplets, tune spacing, use dielectric carrier phase |
| Ferrofluid sedimentation | magnetic layer can lose response over time | bidisperse formulation, cartridge replacement, cycling protocol |
| Droplet coalescence | tribo output depends on stable interfaces | surfactant tuning, channel geometry, surface treatment |
| Tribo drag | contact/friction can reduce EM output | compare combined cell against EM-only baseline |
| Parasitic capacitance | TENG scaling can collapse output | short channels first, local rectification, segmented electrodes |
| Radiation/vacuum compatibility | space use imposes material constraints | start with vacuum chamber tests before space claims |

## Success definition

The integrated architecture only matters if Prototype 3 proves:

```text
P_combined > max(P_EM_only, P_TENG_only)
```

under the same mechanical input envelope and load conditions.
