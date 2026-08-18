# Experiment docs found (Issac's, not teammates)

Searched 2026-08-13 after "i have docs for my own experiments."
These are **his** logs and packets. None of them is a finished IMU.

## Ran (software / geometry). Cite as experimental discipline, not as ADEV.

| Doc | What he actually ran |
|---|---|
| `C:\dev\EXPERIMENT_LOG.md` | His rule: PREDICTION before, RESULT after, MATCH, NEXT. Verifier/chem/MoE/polyglot. Not ferrofluid. |
| `issdandavis/scbe-experiments` (public, archived) | Hyperbolic vs Euclidean, pipeline ablation, sacred eggs, trajectory curvature. JSON results in-repo. |
| MATHBAC experiment tables in `SCBE-private` | Sealed-blind 24/24 etc. Wrong metric for PINPOINT. Do not paste. |
| Clay / Kaggle / STaR logs | Training experiments. Wrong metric. |

Abstract use: one sentence under Capabilities.

> I keep a prediction-before / result-after experiment ledger and have shipped controlled ablations with stored JSON (`scbe-experiments`). Phase I IMU gates will use the same ledger.

## Designed / mapped (physics). Cite as prior art *reading* + a gap, not as his bench.

| Doc | What it is |
|---|---|
| `notes/theory/2026-04-06-gyroscopic-interlattice-magnetic-arrays.md` | His writeup of Nash 54-gyro magnet-coupled lattice, Einstein-de Haas levitated ferromagnet, maglev CMG. Status in-file: `raw-research`. He did not build the 54-gyro table. |
| Session `notes/sessions/2026-04-06-gyroscopic-interlattice-session.md` | Same day: literature pull, SCBE mapping, named gap: **gyro-gyro interlattice not built by anyone**. |
| `ferro_field.py` + habitat spec | His sim + honesty bound. |
| drone-a-rang §2.2 | His arithmetic. |

The gyroscopic packet is the strongest *physics* experiment doc he owns. It is still a paper map. Nash's 54-gyro honeycomb is the closest published cousin to a PINPOINT plant; Ahrens & Vinante 2025 is a levitated ferromagnet gyroscope. Those are other people's experiments that he already read and filed.

## Not found on this machine

A lab notebook of *his* ferrofluid / coil / droplet / rate-table measurements. If that lives in Drive, photos, a paper book, or a folder I did not search, the path has to be named. I will not invent it.

## What goes in the abstract

- Capabilities: experiment ledger + `scbe-experiments`.
- Technical approach bibliography: Nash 2015, Ahrens/Vinante 2025, HALOVS — as prior art he has already digested.
- Not claimed: "I built a gyroscopic lattice" or "I measured ferrofluid ADEV."
