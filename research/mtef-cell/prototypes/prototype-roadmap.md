# M-TEF Cell Prototype Roadmap

## Prototype 1 — Coil-only piston

**Purpose:** prove the electromagnetic baseline before adding fluid complexity.

Build:

- magnet carrier/piston
- coil around travel path
- repeatable stroke input
- rectifier and capacitor
- known resistor load

Record:

- stroke length
- cycles per second
- input force estimate
- open-circuit voltage
- loaded voltage/current
- capacitor charge time

Pass/fail:

- Pass if output is repeatable and scales with stroke speed or magnet/coil changes.
- Fail if signal is inconsistent or mostly measurement noise.

## Prototype 2 — Triboelectric droplet channel

**Purpose:** prove the liquid-solid TENG baseline separately.

Build:

- fluoropolymer/PTFE channel
- controlled droplet or slug movement
- electrode pickup
- high-impedance measurement path

Record:

- droplet size/count
- contact area
- stroke/frequency
- voltage/current/charge signal
- leakage decay
- droplet stability

Pass/fail:

- Pass if the droplet channel produces repeatable charge/current above the measurement floor.
- Fail if droplets coalesce, contaminate the surface, leak charge too quickly, or output is unstable.

## Prototype 3 — Combined EM + tribo cell

**Purpose:** test the actual M-TEF hypothesis.

Build:

- combine the EM piston path with the triboelectric droplet channel
- keep EM and TENG outputs electrically conditioned separately
- measure both channels independently and together

Decision equation:

```text
combined_conditioned_output > max(em_only_output, teng_only_output)
```

Pass/fail:

- Pass if combined output beats the strongest individual channel under equal mechanical input.
- Fail if combined output is lower, unstable, or only trivially higher after added complexity.

## Prototype 4 — Magnetic-control cell

**Purpose:** add ferrofluid/MR control only after the hybrid cell has value.

Build:

- magnetic-fluid damping or steering layer
- external magnet control / field shaping
- containment and seal test

Record:

- repeatability improvement
- drag penalty
- fluid migration
- thermal behavior
- output change from Prototype 3

Pass/fail:

- Pass if magnetic control improves reliability without killing net power.
- Fail if it adds complexity/drag without measurable benefit.

## Prototype 5 — environment-relevant cell

**Purpose:** only after proof of additive output.

Test:

- orientation independence
- pressure/vacuum relevance
- thermal cycling
- long-duration operation
- material compatibility

Pass/fail:

- Pass if the cell remains stable and useful in the target environment.
- Fail if output depends on fragile conditions or fluids degrade/migrate.

## Minimum data table

Each run should log:

| Field | Meaning |
|---|---|
| run_id | unique test ID |
| prototype | P1/P2/P3/P4/P5 |
| force_n | approximate input force |
| stroke_m | stroke length |
| hz | cycles per second |
| em_v | EM channel voltage |
| em_i | EM channel current |
| teng_v | TENG channel voltage |
| teng_i | TENG channel current |
| storage_v_start | capacitor start voltage |
| storage_v_end | capacitor end voltage |
| duration_s | run duration |
| notes | failure/stability observations |
