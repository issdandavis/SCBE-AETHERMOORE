# SCBE AetherMoore — PINPOINT Teammate Brief

Solicitation: DARPA HR001126S0016 (PINPOINT), DSO
Entity: Issac Davis dba SCBE AetherMoore
CAGE: 1EXD5 · UEI: J4NXHM6N5F59
Date: 2026-08-13

## Role

SCBE is a **controls / estimator / Design-Guide software teammate**, not an IMU foundry.

Hardware prime owns the physics package (levitated proof mass, nonlinear resonator, or high-velocity tethered microsystem), fab, packaging, rate table, shaker, and the five Phase I IMU deliverables.

SCBE owns the other half of the BAA's central sentence: *tight co-design of that plant with a real-time adaptive controller and dynamic state estimator*.

## What we put on the month-3 and month-12 gates

- Adaptive stabilizer for a highly nonlinear plant, with a tracked Lyapunov-like energy that is required to be non-increasing on accepted updates.
- 6-DOF dynamic state estimator whose internal addressing is a 4D control-state cube (`rubix_cubit`: 16 vertices, SHA-256 receipts). This is a software state container for the six sensing channels, not a claim that we built a physical tesseract IMU.
- Fail-closed estimator behavior: illegal control paths refuse; rejection returns no useful side channel.
- Design Guide / software PDK: simulated control parameter space, projected closed-loop metrics, hash-linked evidence for every accepted design point.

## What we do not claim

- No MEMS/NEMS fab, no cleanroom, no rate table, no Allan-deviation laboratory.
- No packaged IMU hardware.
- No hyperbolic-distance superiority on navigation error. Existing `d_H` work is a governance metric, not an INS score.
- The word "tesseract" in our repo is a 4D code-state primitive. PINPOINT's tesseract is DSO's name for an integrated IMU. We will not conflate them in the abstract.

## Suggested split

| Package | Owner |
|---|---|
| Sensor physics, process, packaging, lab demo | Hardware prime (PI) |
| Nonlinear control law + adaptive stabilizer | SCBE + prime controls lead |
| 6-DOF estimator + 4D state cube | SCBE |
| Design Guide / software PDK / receipts | SCBE |
| Month-12 ADEV, rate table, shaker; month-21/24 IMUs | Prime + government IV&V |

Preferred use case: **Table 2 Persistent Autonomy / UAV**. Long-horizon bias stability is the metric this stack can actually support. Table 1 high-G munitions is a fab and shock problem.

## Federal posture

- U.S. small business, sole proprietor
- SAM active: CAGE 1EXD5, UEI J4NXHM6N5F59
- Background IP (filed U.S. 63/961,403 and related control/geometry source) listed as background, not ACA-shared program data
- Prefer OT-for-Prototype under the prime if CMMC/SPRS timing is tight

## Contact

Issac Davis
issdandavis7795@gmail.com
issac@aethermoorgames.com
Port Angeles, WA
