# PINPOINT Solo Approach — Issac only

Date: 2026-08-13
Decision: no teammates, no subcontract PIs, no university option.
Vendors (coil wire, ferrofluid bottles, a rented rate-table day) are procurement, not teaming.

## The only conforming solo sentence

I will design, simulate, build, and deliver a bench-scale 6-DOF IMU whose proof masses are **magnetically trapped ferrofluid**, whose resonator is the **Rosensweig / Faraday nonlinear regime**, and whose real-time controller and estimator are the SCBE stack I already run.

That maps onto the BAA's own examples: electromagnetically levitated proof mass + nonlinear resonator + tight plant/control co-design. It does not require a foundry. It does require that I actually build six sensing channels.

A software-only abstract is non-conforming. A teammate abstract is off the table. This is the remaining path.

## What I already have (cite, do not inflate)

- `C:\dev\ferro_field.py` — language → legal field-op grammar → electromagnet current map. **Simulated** surface height. The current map is what transfers to hardware.
- `C:\dev\ferrofluid_habitat_control_SPEC.md` — already says the fluid physics is not a capability. Keep that bound.
- `C:\dev\clay_home\folds\drone_a_rang\BUILD.md` §2.2 — computed ferrofluid vs 98 g centrifugal (50–800 T/m vs 1,492 kN/m³). Mass-routing arithmetic, not a sensor, but it is the only high-g ferrofluid number on this machine.
- L7 Lyapunov exponent in `symphonic_cipher` — software-state stability behavior, not a finished proof.
- `python/scbe/rubix_cubit.py` — 4D control-state cube with SHA receipts. Addressing layer for six channels. Not a physical tesseract.
- SAM: CAGE 1EXD5, UEI J4NXHM6N5F59. Sole PI.

## Plant (what I will build)

Two channel types, three axes each.

**Accelerometer (3).** A ferrofluid droplet sits in a magnetic potential well shaped by a coil set (bias + gradient). Linear acceleration displaces the droplet in the well. Displacement is read by pickup-coil inductance and/or a cheap optical beam. The droplet *is* the levitated proof mass. No silicon flexure, no anchor loss — that is the HALOVS/PINPOINT isolation argument, done with a colloid instead of a solid levitated proof.

**Gyroscope (3).** Drive the same (or a paired) droplet into the Rosensweig / Faraday nonlinear regime with an AC field. Rotation couples through Coriolis into a quadrature magnetic moment. Demodulate that channel. This is the BAA's "nonlinear resonator," not a linear MEMS mode.

One housing, six channels, one current-map controller. Call the package an integrated IMU. Do **not** call the 4D software cube the IMU.

## Control (what I already started)

Upgrade `ferro_field.py` from a 9×22 display grid to a 3D trap current law:

```
legal field-op  →  coil current vector  →  trap potential + drive
illegal op      →  reject, fail-to-noise
accepted update →  Lyapunov-like energy of the trap/estimator is non-increasing
```

Month 3 is this model in simulation, with a fake plant that is *actual ferrohydrodynamics* (magnetization + Stokes drag + magnetic body force), not the ASCII height ramp in the current file. The current file is the grammar. The new file is the plant.

## Use case

**Table 2 — Persistent Autonomy / UAV.** Long-horizon bias stability. Not munitions, not 10,000 g, not Hopkinson bar.

Phase I targets I will put on the abstract (copied from Table 2, not invented):

- Vibration survivability 10 gRMS
- Accel bias instability 1 µg (ADEV @ τ = 1000 s)
- Gyro bias instability 1e-3 °/hr (ADEV @ τ = 1000 s)
- SWaP reported in the Design Guide

I have **not measured** any of those. The abstract proposes to measure them. If a reviewer asks "have you hit 1e-3 °/hr" the answer is no.

Deviations are allowed with justification. I will not water the table down in the abstract. If month-12 hardware only shows the *mechanism* (trap holds, tilt moves the droplet, ADEV exists as a plot), that is a program risk I name, not a secret.

## 24-month solo schedule

| Month | What I personally deliver |
|---|---|
| 1 | Kickoff. Coil/trap CAD. Ferrohydrodynamic sim v0. BAAT/OT paperwork. |
| 3 | Sim of full controller + 6-DOF estimator. Predicted ADEV from the model. Design Guide outline. |
| 6 | First physical trap: one accel axis on the bench. Current-map drives real coils. Displacement vs tilt recorded. |
| 9 | Three accel + one gyro channel. Temperature log. First Allan plot (even if ugly). |
| 12 | Six channels live. ADEV to ≥1000 s on each. Rate-table / turntable day **rented**. Shaker day rented or a calibrated vibration fixture. Report. |
| 18 | Packaging: one boxed IMU, not a breadboard. Repeat ADEV. |
| 21 | Three packaged units ready for government IV&V. |
| 24 | Five units + Design Guide + software PDK + final report. |

Vendors, not teammates: Ferrotec (fluid), coil/wire suppliers, a machine shop or JLCPCB for housings, a commercial or university rate-table **rental**, FedEx to the IV&V lab. None of them are on the cover sheet.

## What I will buy (not invent)

- Ferrofluid: Ferrotec EFH1 or EMG-700 class, several bottles, plus a higher-Ms candidate
- Coils: wound on printed forms, or COTS Helmholtz/gradient kits
- Drive: STM32 or similar + current amplifiers + current sense
- Readout: pickup coils + instrumentation amp; optional photodiode pair; USB scope / lock-in
- Mechanical: 3D print + one machined nonmagnetic housing lot
- Test rental: one rate-table day, one shaker day, a decent thermometer
- Instruments I do not own: lock-in and a quiet current source are the two that actually matter

Ballpark materials + rentals: **$40k–$120k** over 24 months. Labor is me.

## Cost ROM (Phase I, OT for Prototype)

| Line | 24-month ROM |
|---|---|
| PI labor (1.0 FTE, sole prop) | $280k–$360k |
| Materials, coils, electronics, housings | $40k–$80k |
| Instruments (lock-in, supplies) | $15k–$40k |
| Rate-table / shaker rental + shipping | $10k–$25k |
| Travel (east/west PI meetings every 6 months, one site visit) | $12k–$20k |
| Overhead / contingency | $30k–$50k |
| **Phase I total** | **~$400k–$575k** |

Phase II ROM (planning only): packaging/ruggedization, another $400k–$700k, not definitized.

IIP student option: no. No university.

Instrument: **OT for Prototype**. Milestone-paid. Avoids procurement-contract CMMC L2 as the opening move. ACA still applies to program-generated data; background IP (63/961,403, Rubix, ferro_field grammar) is listed as background and not in the share set.

## Evaluation-criteria honesty

| Criterion (descending) | Solo reality |
|---|---|
| Scientific / technical merit | The plant is a real PINPOINT species. The control co-design is the strongest part. Feasibility of Table 2 numbers from a first ferrofluid IMU is the hole. Name it. |
| Relevance to DARPA | GPS-denied UAV PNT. Fine. |
| Cost and schedule realism | One person, bench, rented test time. Credible at $0.4–0.6M. Not credible if I write $3M or claim a foundry PDK. |
| Capabilities / related experience | Weakest score. I have SAM, prior DARPA abstracts, and running control software. I have never delivered an IMU. Do not dress that up. |

## Risks I will print in the abstract

- Colloidal stability over 1000 s–days (sedimentation, evaporation, surfactant breakdown)
- Temperature coefficient of viscosity dominating bias
- Brownian / thermal noise of a droplet vs a solid proof mass
- Rosensweig drive leaking into the sense channel
- No in-house rate table — rented days only
- One-person critical path; illness or a failed coil lot slips month 12
- Table 2 ADEV may be missed even if the mechanism works

Mitigations that are real: sealed cartridge, two fluid formulations, temperature logged and estimated out, lock-in demodulation, fail-closed controller that kills drive if the droplet leaves the well, rented test days booked at month 10.

## Abstract rules for this path

- First sentence is the ferrofluid-trap IMU, not Rubix, not Clay, not MATHBAC 24/24.
- `ferro_field.py` is "existing coil-array controller, to be extended." It is not prior IMU evidence.
- Lyapunov is "bounded-update stabilizer," not a theorem.
- Tesseract, if used at all, is "4D control-state addressing of six channels."
- No teammates on the cover sheet. Other team members: none.
- PI: Issac D. Davis.

## Go / no-go (solo)

**GO to write the abstract** on this architecture.

**NO-GO to claim** any ADEV number as measured, any foundry, any teammate, or that `ferro_field.py` already is the sensor.

If I will not build six physical channels in Port Angeles, do not file. The BAA will not accept the estimator alone.
