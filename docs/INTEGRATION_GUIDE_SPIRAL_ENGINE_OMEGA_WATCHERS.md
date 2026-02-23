# Integration Guide: Spiral Engine Watchers + Omega Locks

Date: 2026-02-20  
Audience: SCBE runtime, browser/terminal UI, and pipeline integrators

## 1) What to integrate

Primary integration surface:

- `src/spiralverse/aethermoor_spiral_engine.py`
- `src/spiralverse/temporal_intent.py`

New runtime contracts:

- Three Watchers:
  - `watcher_fast`
  - `watcher_memory`
  - `watcher_governance`
  - `d_tri`
- Triadic blend:
  - `triadic_from_rings = 1 - d_tri`
  - `triadic_from_sheaf`
  - `triadic_stable = triadic_from_sheaf * triadic_from_rings`
- Five-lock gate factors:
  - `pqc`
  - `harm`
  - `drift`
  - `triadic`
  - `spectral`
- Gameplay/ops utility:
  - `friction_multiplier` (from harmonic wall)
  - `permission_color` (`green`/`amber`/`red`)
  - `weakest_lock`

## 2) Quick verification

Run tests:

```bash
python -m pytest -q tests/test_aethermoor_spiral_engine.py tests/test_temporal_lock_diagnostic.py
```

Run demo:

```bash
python scripts/aethermoor_spiral_demo.py --seed 7 --turns 8
```

Run lock diagnostic:

```bash
python scripts/omega_lock_diagnostic.py --distance 0.82 --velocity 0.05 --harmony -0.2 --samples 8 --pqc-valid --triadic-stable 0.55 --spectral-score 0.72 --pretty
```

## 3) UI/terminal wiring

Use these fields from each turn:

- `history[*].watchers.fast|memory|governance|d_tri`
- `history[*].omega_factors.pqc|harm|drift|triadic|spectral`
- `history[*].friction`
- `history[*].permission_color`
- `history[*].weakest_lock`
- `history[*].voxel_key`
- `history[*].terrain`

Recommended display:

- Three ring widgets for watcher signals.
- Five lock bars for Omega factors.
- Friction badge from `friction`.
- Permission indicator from `permission_color`.
- Remediation prompt from `weakest_lock`.

## 4) Data semantics

- `d_tri` is risk-oriented (higher = worse).
- `triadic_from_rings` is safety-oriented (higher = safer).
- `omega` is safety-oriented (higher = safer).
- `friction_multiplier` is cost/latency-oriented (higher = more expensive).

## 5) Common integration pitfalls

- Do not invert `d_tri` twice.
- Do not mix risk-domain and safety-domain values in one chart without labels.
- Keep `permission_color` thresholds aligned with runtime (`green >= 0.70`, `amber >= 0.30`, else `red`).
- Prefer deterministic seed-based demo output for front-end snapshots.

## 6) Minimal API envelope suggestion

If exporting through API, expose this schema per turn:

```json
{
  "decision": "ALLOW|QUARANTINE|DENY|EXILE",
  "omega": 0.0,
  "watchers": {
    "fast": 0.0,
    "memory": 0.0,
    "governance": 0.0,
    "d_tri": 0.0
  },
  "omega_factors": {
    "pqc": 0.0,
    "harm": 0.0,
    "drift": 0.0,
    "triadic": 0.0,
    "spectral": 0.0
  },
  "friction": 1.0,
  "permission_color": "green",
  "weakest_lock": "harm_score",
  "voxel_key": "00:00:00:00:00:00",
  "terrain": "glow_meadow"
}
```

