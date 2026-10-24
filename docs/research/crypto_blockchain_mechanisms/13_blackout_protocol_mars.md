# 13 — Blackout Protocol (the Mars-relay analogy)

## Real-world basis
During **Mars solar conjunction**, the Sun sits between Earth and Mars and garbles
radio contact. It happens about every **26 months** (the synodic period, ~780 days)
and lasts about **2 weeks**. NASA puts a command moratorium in place. Rovers get
**pre-loaded command sequences**, run them on their own, and **reconcile** once the
link comes back. (Well-documented NASA practice, e.g. NASA/JPL "Mars Solar
Conjunction" explainers. ⚠ Add the specific link for the year cited.)

## Experiment
- Instance **C** has a continuous feed.
- Instance **B** is in **blackout**. Before going dark, it commits to a set of
  procedures (a pre-loaded queue plus conditional rules), then runs blind.
- When the link returns, diff **positions and intent**: did B's pre-loaded plan pick
  what C picked with full information?
  - High intent agreement means the predictive layer is validated.
  - Low agreement means the plan was overfit to the moment it was written.

## Tie to SCBE
- **Time-dilation dwell gate:** when confidence drops (blackout, stale feed),
  **stall high-risk actions** and let pre-authorized low-risk ones run. This is the
  rover rule applied to trading.
- It is the fail-closed rule (09) in time-extended form.

## Cross-references in this repo
- `../mars_long_horizon_drone/` — long-horizon autonomy packet
- `../mars_nested_drone_architecture_spec.md`
- `../mars_tethered_pushline_relay.md` — relay and link-loss design
