# Space Stack Integration (2026-05-03)

This update applies the recent research tracks (NASA/ESA/SpaceX/China programs plus FTC/PHM/tether energy references) into executable primitives inside the existing stack.

## What was added

- `src/physics_sim/space_stack.py`
  - Swarm coordination checks for separation and closure-rate safety.
  - FDIR-style health scoring and safe-hold trigger logic.
  - Roundtable signature tier checks (`standard`, `strict`, `critical`).
  - Swarm energy-role assignment (`injector`, `harvester`, `stabilizer`, `standby`).
  - Electrodynamic tether power estimate with explicit orbital-energy debit.
  - Governance action mapping (`ALLOW`, `QUARANTINE`, `ESCALATE`, `DENY`).

- `src/physics_sim/test_space_stack.py`
  - Unit tests covering all above behaviors.

- `scripts/space/space_stack_smoke.py`
  - End-to-end smoke script for local validation of the new layer.

- `src/physics_sim/__init__.py`
  - Exported `space_stack` public API for direct import from `physics_sim`.

## Why this matches the research

- Formation autonomy focus (Starling/Proba-style behavior): represented via pairwise separation + closure constraints.
- Self-maintenance / PHM focus: represented via FDIR thresholds and safe-hold triggering.
- ISAM safety/governance focus: represented via tiered roundtable authorization checks.
- Mechanical energy-harvesting caveat in microgravity: represented via tether generation plus orbital-energy debit accounting.

## How to run

From repo root:

```powershell
python -m pytest src/physics_sim/test_space_stack.py -q
python scripts/space/space_stack_smoke.py
```

## Next integration step (recommended)

Wire `space_stack.py` outputs into:

1. `src/physics_sim/simulator.py` event handlers for autonomous safe-hold transitions.
2. `workflows/n8n/scbe_n8n_bridge.py` mission endpoint payload validation.
3. `spiralverse-protocol/docs/SPACE_DEBRIS_FLEET.md` examples backed by executable test vectors from `test_space_stack.py`.
