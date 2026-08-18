# PINPOINT Abstract Draft (solo) — paste into Attachment B

Status: draft for Issac edit. Not submitted. No measured ADEV. No teammates.

**Abstract title:** Ferrofluid-Trapped 6-DOF IMU with Grammar-Governed Nonlinear Control

**Proposer:** Issac Davis dba SCBE AetherMoore
**CAGE:** 1EXD5 · **UEI:** J4NXHM6N5F59
**PI / Technical POC:** Issac D. Davis, Port Angeles, WA · issdandavis7795@gmail.com
**Admin POC:** same
**Other team members:** none
**Instrument sought:** Other Transaction for Prototype
**Estimated Phase I cost:** $400k–$575k (see Cost)
**Period of performance:** 24 months
**Use case:** Table 2 Persistent Autonomy / UAV
**Other solicitations this concept has been proposed to:** none
**New work:** yes. No prior funding or positive funding decision on a ferrofluid IMU. Sensor does not exist yet.

---

## 1. Goals and Impact

I will build a proof-of-concept six-degree-of-freedom inertial measurement unit whose proof masses are magnetically trapped ferrofluid droplets and whose sense modes run in the Rosensweig / Faraday nonlinear regime. The same person who writes the plant model writes the real-time adaptive controller and the 6-DOF estimator. Phase I delivers five packaged bench IMUs, a Design Guide, and a software PDK.

MEMS IMUs have sat on a noise-and-drift plateau for a decade because the solid proof mass is anchored to the die. Anchor loss and substrate coupling cap Q. PINPOINT asks for architectures that leave that regime. A ferrofluid droplet in a shaped magnetic well has no solid anchor. Isolation is magnetic. The same coils that form the well can drive the droplet into a nonlinear surface/volume mode, which is the gyroscope channel.

This is new proposed research, not a continuation and not a finished device asking for fab money. I have not been funded for a ferrofluid IMU. I have a running coil-array controller (`ferro_field.py`), a computed high-g ferrofluid routing model, and a Lyapunov-bounded update rule. Those are starting tools. The sensor does not exist yet. Phase I is the work that builds six live sensing channels and measures the Table 2 Phase I numbers:

- vibration survivability 10 gRMS
- accelerometer bias instability 1 µg (ADEV, τ = 1000 s)
- gyroscope bias instability 1e-3 °/hr (ADEV, τ = 1000 s)
- SWaP reported in the Design Guide

If successful, a tactical UAV keeps a dead-reckoning core when GPS is denied, without a ring-laser or fiber-optic gyro.

## 2. Technical Approach

**What the work does.** Design, simulate, fabricate at bench scale, and test a 6-DOF IMU: three accelerometers (droplet displacement in a magnetic well) and three gyroscopes (Coriolis coupling out of a driven Rosensweig / Faraday mode). One housing. One current-map controller. Fail-closed: illegal field ops are not emitted.

**How it is done today, and the limit.** Linear MEMS IMUs. Compact, cheap, plateaued. Strategic RLG/FOG units meet the numbers and miss the SWaP. Visual navigation still needs a baseline IMU and fails in fog, blur, water, cloud, and desert. Levitated *solid* proof masses and high-velocity tethered resonators are the HALOVS path. I am proposing the fluid analog of the levitated mass, which a single investigator can build without a cleanroom.

**What is new, and why it can work.**
1. Plant: ferrofluid droplet as the levitated proof mass. Magnetic body force vs Stokes drag vs inertia is a closed, textbook ferrohydrodynamic system I will write down and simulate in months 1–3, replacing the cosmetic surface-height map I use today.
2. Sense: accel = well displacement; gyro = nonlinear-mode Coriolis. Same coils, two demodulation paths.
3. Control: only legal field-ops reach the amplifiers. Accepted updates keep a tracked trap/estimator energy non-increasing. This is a stabilizer, not a claimed Lyapunov theorem.
4. State: six channels addressed as a 4D control-state cube with SHA receipts, so every current vector and every estimate is replayable.

I think it will work because the isolation argument does not depend on silicon Q, the coil-array control already runs, and the first hardware gate (month 6) is one accel axis vs tilt — a measurement I can do on a bench before any rate table.

**How DoD test people use it.** Month 12: I ship ADEV plots to 1000 s and bring the unit to a rented rate table and a rented shaker. Month 21: three packaged units to the government IV&V lab for the Table 3 24-hour soak (drift < 1.0e-3 °/hr @ 1000 s in a day/night thermal cycle). Month 24: five units.

**Cost and time.** Phase I 24 months, ROM $400k–$575k. One FTE. No foundry. No IIP. Materials + instruments + rented test days are the non-labor cost.

**Technical challenges and mitigations.**

| Challenge | Mitigation |
|---|---|
| Colloid settles or dries | Sealed cartridge, two fluid formulations (EFH1-class and higher-Ms), swap protocol |
| Viscosity tempco looks like bias | On-board temperature in the estimator; thermal chamber or day/night soak |
| Brownian / thermal noise of a droplet | Larger droplet for accel, lock-in on the gyro drive, measure the floor early |
| Drive leaks into sense | Orthogonal demodulation, fail-closed kill if the droplet leaves the well |
| No in-house rate table | Commercial rental booked at month 10; gravity-tilt as the month-6 accel check |
| Single-person critical path | Month-6 one-axis gate is the early fail. If the droplet does not move with tilt, I stop and replan before month 12. |

**Milestones (payable, OT).**

- M1 (month 3): ferrohydrodynamic model + controller + estimator; simulated ADEV delivered.
- M2 (month 6): one physical accel axis; displacement vs tilt plot.
- M3 (month 12): six live channels; ADEV ≥ 1000 s; rented rate-table and vibration data.
- M4 (month 21): three packaged IMUs shipped for IV&V.
- M5 (month 24): five IMUs + Design Guide + software PDK + final report.

## 3. Capabilities / Management

Issac D. Davis is sole PI, sole investigator, and sole author. Small-business sole proprietor, Port Angeles, WA. SAM active, CAGE 1EXD5, UEI J4NXHM6N5F59.

Relevant existing work: grammar-governed electromagnet current maps; ferrofluid-in-centrifugal-field calculations; Lyapunov-bounded software-state updates; receipted 4D control-state cube. Prior DARPA proposal process experience. I have not previously delivered an IMU. That is stated so the reviewers do not have to infer it.

Organization: one person. Vendors supply fluid, coil goods, machined housings, and rented test time. They are not performers.

## 4. Cost and Schedule

Contractor fiscal years treated as 12 + 12 months.

| | Year 1 | Year 2 | Total |
|---|---|---|---|
| PI labor | $150k | $150k | $300k |
| Materials / housings / electronics | $40k | $20k | $60k |
| Instruments | $25k | $5k | $30k |
| Rate-table / shaker rental + ship | $8k | $10k | $18k |
| Travel (PI meetings, site visit) | $8k | $8k | $16k |
| Contingency | $20k | $20k | $40k |
| **Phase I** | **$251k** | **$213k** | **$464k** |

Phase II ROM for government planning only: $500k, packaging and ruggedization, not definitized.

IIP: not proposed.

---

Bibliography (optional, 2 pages later): HALOVS portfolio PDF; Rosensweig ferrohydrodynamics; Rajnak 2025 ferrofluid harvester (adjacent, not IMU); FARGO ISS thermal switch (adjacent, not IMU). Add ferrofluid-accelerometer / magnetic-trap droplet papers only after Issac has opened them.
