# Checkpoint: Mars Source Map + Optical Prime Model

Date: 2026-06-20

## Current Artifacts

Mars long-horizon source map:

- `docs/research/mars_long_horizon_drone/source_manifest.json`
- `docs/research/mars_long_horizon_drone/outline.md`
- `docs/research/mars_long_horizon_drone/draft.md`
- `docs/research/mars_long_horizon_drone/decision_record.json`

Optical/thermal short-form artifacts:

- `scripts/research/run_thermal_grid_sweep.py`
- `scripts/research/optical_laser_prime_model.py`
- `scripts/research/fuse_thermal_optical.py`
- `tests/test_optical_laser_prime_model.py`

## What Was Done

- Consolidated Mars, drone, Godot/NPC, spatial movement, fleet formation, Endless Sky, materials/PUF, and space-system sources into one source-map package.
- Added materials and PUF guardrails: deterministic seeded topology is not a standalone PUF; use challenge-response physical measurement with entropy/separation checks.
- Added space docs as mission-simulation/evidence-adapter lanes, not flight-readiness or NASA-endorsement claims.
- Hardened the optical laser prime model and thermal-optical fusion bridge.
- Added focused tests for the optical channel.

## Verification

```powershell
python -m json.tool docs\research\mars_long_horizon_drone\source_manifest.json > $null
python -m json.tool docs\research\mars_long_horizon_drone\decision_record.json > $null
python -m pytest tests\test_optical_laser_prime_model.py -q
python -m pytest tests\test_thermal_mirror_probe.py -q
```

Observed:

- Optical tests: 7 passed
- Thermal mirror tests: 17 passed
- Both JSON files parsed cleanly

## Important Boundary

`scripts/research/prime_fog_of_war_probe.py` was referenced by the new sweep and optical docs, but was not found in the current repo search. The user said it is somewhere. Do not overwrite or replace it without searching/recovering first.

## Resume Point

1. Locate `prime_fog_of_war_probe.py` in archive/backup/vault roots.
2. If found, wire `fused_anchor_score` from `scripts/research/fuse_thermal_optical.py` into its scoring loop.
3. If not found, rebuild a minimal probe using the tested `optical_laser_prime_model.py`.
4. Run the safe single-process sweep only after the probe path is correct.
