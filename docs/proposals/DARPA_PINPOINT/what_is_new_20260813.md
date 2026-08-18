# What is new

The IMU is new. The supporting pieces are not.

BAA alignment needs both: the concept is not already done, and it has not already been funded. Cover sheet line: **other solicitations this concept has been proposed to: none.**

## New (the proposal)

A 6-DOF IMU whose proof mass is a magnetically trapped ferrofluid droplet and whose gyro channel is a driven Rosensweig / Faraday mode, built and tested by one PI, 24 months, Table 2 UAV metrics.

This combination did not exist in the farm or on GitHub before today. There is no prior ferrofluid accelerometer, no prior ferrofluid gyroscope, no ADEV plot, no housing, no rate-table data. Do not cite `ferro_field.py` or drone-a-rang as if they were that sensor.

Patent 63/961,403 is authorization / TLCFI / fail-to-noise / Lyapunov *behavior*. It is not an inertial-sensor filing. Do not say the IMU is already claimed.

## Old (may be cited as starting software / arithmetic only)

| Piece | What it is | What it is not |
|---|---|---|
| `ferro_field.py` | Legal coil current maps | A plant model or a sensor |
| Habitat ferrofluid spec | Honest TRL bound | A space IMU |
| Drone-a-rang §2.2 | Ferrofluid vs centrifugal force, computed | An IMU channel |
| L7 Lyapunov | Software-state bounded update | A closed-loop IMU proof |
| Rubix cubit | 4D control-state addressing | A physical tesseract IMU |
| M-TEF / tether / dock plug | Other ferrofluid uses | Inertial sensing |

## How the abstract should say it

> This is new proposed research. I have not received funding or a positive funding decision for a ferrofluid IMU. Existing coil-array control and ferrofluid arithmetic are the starting tools. The sensor, the six-channel package, and the Allan Deviation measurements do not exist yet. That is the Phase I work.

## Do not

- Call this a continuation of MATHBAC, CLARA, Deep Thoughts, or QBI
- Put Clay counting scores, DAVA 24/24, or `d_H` trust-AUC in the abstract
- Say "we already built the tesseract"
- Back-date the IMU into older repos
