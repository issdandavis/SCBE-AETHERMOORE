# Validation Plan

## Measurement discipline

Every prototype must log:

- mechanical input: force, displacement, frequency, duty cycle
- electrical output: open-circuit voltage, short-circuit current, loaded voltage/current
- power into defined load
- temperature
- pressure / humidity when relevant
- cycle count
- failure mode observations

Do not compare outputs unless the mechanical input and load conditions are controlled.

## Baseline tests

### EM baseline

1. open-circuit voltage vs frequency
2. loaded power vs load resistance
3. damping vs load
4. thermal behavior under long cycling

### TENG baseline

1. open-circuit voltage vs droplet velocity
2. transferred charge per droplet/cycle
3. output vs humidity/pressure
4. output degradation over cycle count

### Combined baseline

Run these with identical mechanical input:

```text
A. EM branch only
B. TENG branch only
C. EM + TENG physically integrated, electrically separate
D. EM + TENG electrically combined through power manager
```

## Decision metrics

| Metric | Meaning |
|---|---|
| `P_em_only` | EM branch output under controlled input |
| `P_teng_only` | TENG branch output under controlled input |
| `P_combined_separate` | physical integration with separate logging |
| `P_combined_pm` | output after power management |
| `drag_penalty` | EM loss introduced by TENG channel |
| `net_gain_ratio` | `P_combined_pm / max(P_em_only, P_teng_only)` |

## Minimum useful pass

Prototype 3 should hit:

```text
net_gain_ratio > 1.0
```

A stronger engineering target is:

```text
net_gain_ratio >= 1.25
```

because a tiny gain may not justify complexity.

## Failure taxonomy

| Failure | Symptom | Likely fix |
|---|---|---|
| charge leakage | TENG voltage collapses | improve dielectric isolation / droplet spacing |
| coalescence | droplet train becomes slug flow | surfactant or geometry change |
| wall fouling | output decays quickly | surface treatment / fluid replacement |
| viscous loss | EM output drops in combined test | reduce channel drag / decouple branch |
| impedance mismatch | high voltage but no usable stored energy | redesign power management |
| magnetic instability | control fluid clumps or sediments | formulation change / cartridge strategy |

## Documentation requirements

Each prototype run should produce:

- run ID
- schematic version
- fluid stack
- material list
- input waveform
- raw CSV data
- plotted output curves
- summary conclusion
- next design change
