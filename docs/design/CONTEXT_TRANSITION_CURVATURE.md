# Context transition curvature (software)

**Status:** internal theory note — not implemented as a named metric in kernel yet
**Hardware analogue:** sheath–spine differential motion on the multifunction tether (see `docs/research/magnetic_sheathed_fiber_optic_space_tether_2026-06-01.md`)

## Problem

`ContextBundle` already feeds identity, temporal, and environment into L1’s imaginary lift (`src/harmonic/contextBundle.ts`). What is still missing is an explicit score for **how violently context changed between handoffs**, not only the current point in hyperbolic space.

## v1 proxy (no gauge theory)

Between bundle `B_{t-1}` and `B_t`:

```text
kappa =
  w_id   * delta_identity(B)
+ w_perm * delta_permission(B)
+ w_env  * delta_environment(B)
+ w_vel  * velocity(temporal)
+ w_tool * mismatch(intent, tool_surface)
```

Normalize each term to `[0, 1]` with documented clamps. Map:

| kappa band | Decision bias |
|------------|----------------|
| low | ALLOW |
| moderate | QUARANTINE |
| high sustained | DENY or ESCALATE |

## Relation to “magnetic fiber bundle” metaphor

- **Base space:** token / intent trajectory
- **Fiber:** context fields attached to each step
- **Curvature proxy:** large incompatible changes in fiber state over a short base-space move

Use the word **magnetic** only in internal notes. External copy: **transition curvature** or **context-fiber drift**.

## Implemented prototype (desk sim bridge)

- `scripts/sim_tether_rectifier.py` — JSON telemetry stream
- `src/harmonic/tetherTelemetry.ts` — `calculateTetherCurvature()` → ALLOW / QUARANTINE / DENY
- `ContextBundle.physical` — last 8 imaginary features via `physicalTelemetryFeatures()`
- `docs/tether-governance-demo.html` — ops UI cards + terminal flash

## Next implementation targets

1. Agent bus event schema — optional `curvature` field on handoff records
2. Wire live stream into running API `/v1/govern` path (optional second lane)
3. `contextTransitionCurvature(prev, next)` for pure software bundles (no sim)

## Do not claim

- Equivalence to U(1) gauge curvature or aerospace tether physics
- Patent-ready novelty without counsel review
