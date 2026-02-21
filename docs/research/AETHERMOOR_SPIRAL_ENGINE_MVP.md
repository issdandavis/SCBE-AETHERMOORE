# Aethermoor Spiral Engine MVP

Status: `prototype`

## What this adds

File: `src/spiralverse/aethermoor_spiral_engine.py`

The module turns SCBE governance signals into a game loop with:

1. Procedural exploration map (`Region` generation by seed)
2. Inventory + crafting (`consensus_seal`, `spectral_filter`)
3. Skill progression (`tongue` levels + skill points)
4. Mission routing with `ALLOW/QUARANTINE/DENY/EXILE`
5. Sheaf consistency gate using Tarski lattice operators (`src/harmonic/tarski_sheaf.py`)
6. Five-lock diagnostics (`pqc/harm/drift/triadic/spectral`) with weakest-lock attribution
7. Live permission dial color (`green/amber/red`) and friction multiplier from harmonic wall

## Key Formulas as Mechanics

| Mechanic | Formula | Player feels it as |
|---|---|---|
| Distance from safe | `d = acosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))` | Heat/fog pressure on the map |
| Intent persistence | `x = min(3, (0.5 + intent*0.25) * (1 + (1-trust)))` | Rising heat meter for sustained risky behavior |
| Cost wall | `H_eff = 1.5^(d^2 * x)` | Latency/friction storm and compute drag |
| Safety inversion | `harm = 1 / (1 + log(max(1, H_eff)))` | Green-to-red permission dial |
| Five-lock gate | `Omega = pqc * harm * drift * triadic * spectral` | Door with five locks |
| Three Watchers | `d_tri = (Σ λ_i * I_i^phi)^(1/phi)` | Three guardian rings (fast/memory/governance) |

Voxel discovery is coherence-shaped:
- procedural voxel key uses `[X:Y:Z:V:P:S]`
- coherence influences terrain class and discovery rhythm
- low coherence tends toward hostile terrain; high coherence tends toward stable terrain

Runtime note:
- watcher rings produce `I_fast`, `I_memory`, `I_governance`
- triadic gate uses `triadic_from_rings = 1 - d_tri`
- final triadic factor is blended conservatively: `triadic = triadic_from_sheaf * triadic_from_rings`

## Math chain in the loop

Each turn computes:

- Distance pressure from region hazard
- Temporal intent accumulation (`TemporalSecurityGate`)
- Harmonic wall cost `H_eff = R^(d^2 * x)` (inside temporal gate)
- Sheaf obstruction count on temporal nodes `{Ti, Tm, Tg}`
- Triadic stability `= 1 - obstruction_count / 3`
- Omega gate:
  - `Omega = pqc_valid * harm_score * drift_factor * triadic_stable * spectral_score`
- Lock diagnostics:
  - `weakest_lock = argmin({pqc_factor, harm_score, drift_factor, triadic_stable, spectral_score})`
  - `permission_color` bands: `green >= 0.70`, `amber >= 0.30`, else `red`
  - `friction_multiplier = H_eff` (latency/cost pressure)

Decision thresholds come from `TemporalSecurityGate`:

- `ALLOW` if omega > `0.85`
- `QUARANTINE` if omega > `0.40`
- otherwise `DENY`
- `EXILE` when sustained low trust triggers exile state

## Demo

```bash
python scripts/aethermoor_spiral_demo.py --seed 7 --turns 12 --output-json artifacts/aethermoor/spiral_demo.json
```

## Useful Tool: Five-Lock CLI

```bash
python scripts/omega_lock_diagnostic.py --distance 0.82 --velocity 0.05 --harmony -0.2 --samples 8 --pqc-valid --triadic-stable 0.55 --spectral-score 0.72 --pretty
```

This prints:
- per-lock values
- Omega decision
- green/amber/red permission color
- weakest lock + direct remediation hint

## Tests

File: `tests/test_aethermoor_spiral_engine.py`

Coverage:

- deterministic world generation for same seed
- sheaf obstruction influences stability
- crafting resource consumption + output
- valid decision/omega per turn
- lock diagnostics populated on each turn outcome
- deterministic replay for same seed/turns
