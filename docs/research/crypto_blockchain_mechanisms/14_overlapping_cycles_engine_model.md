# 14 — Overlapping Cycles: The Engine Model

## Time grains
| Cycle | Grain | Role |
|---|---|---|
| Fills | real time | Sync (07) |
| Reconciliation | hourly | Catch breaks early |
| Closes | daily | Daily-close discipline |
| TDA windows | weekly | Regime detection (10) |

Each layer samples the same market at a different temporal resolution.

## Engine analogy (Issac)
- **Power = fast instance**: what you can do *right now at this RPM*.
- **Torque = slow instance**: what you can *sustain* under load.
- **Combined envelope = the vehicle's performance curve.** Neither number alone
  describes the car.
- **Traction ∝ predictive mass accumulated into a single real moment**, not clock
  time. A decision has grip when the evidence from several grains converges on it.

## Dilution risk
If knowledge is spread across too many predictive moments, each one carries too
little evidence and the result is noise. The fix is **ExperientialSignature
weighting**: recent, relevant incidents count more, and old or irrelevant breaks
decay. This stops every past break from getting an equal vote.

## Testable claim
In 12's two-instance setup, a combined fast+slow policy should beat either one alone
on risk-adjusted outcomes. If it doesn't, the engine analogy is decorative.
