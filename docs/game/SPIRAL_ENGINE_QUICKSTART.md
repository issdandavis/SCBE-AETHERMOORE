# Spiral Engine Quickstart (Aethermoor)

This guide is the operator path for the deterministic Aethermoor simulator.

## Prerequisites

- Python available in shell (`python --version`)
- Repo root as working directory

## 1. Validate script syntax

```powershell
python -m py_compile scripts/spiral_engine_game_sim.py tests/test_spiral_engine_game_sim.py
```

No output means success.

## 2. Run a deterministic one-tick mission

```powershell
python scripts/spiral_engine_game_sim.py --seed aethermoor-mvp --ticks 1 --pad ENGINEERING --tongue KO --output artifacts/spiral_engine_tick.json --pretty
```

Expected result:
- Writes `artifacts/spiral_engine_tick.json`
- Contains `history[0].StateVector` and `history[0].DecisionRecord`

## 3. Run a short multi-tick session

```powershell
python scripts/spiral_engine_game_sim.py --seed aethermoor-test --ticks 5 --pad SYSTEMS --tongue DR --output artifacts/spiral_engine_run.json --pretty
```

Use this output for HUD wiring and gameplay balancing.

## 4. Verify simulator tests

```powershell
pytest -q tests/test_spiral_engine_game_sim.py
```

## 5. Route chain command (step 1)

The route chain entry point in `scripts/route_spiral_engine_chain.yaml` starts with:

```powershell
python scripts/spiral_engine_game_sim.py --seed aethermoor-mvp --ticks 1 --pad ENGINEERING --tongue KO --output artifacts/spiral_engine_tick.json
```

This payload is then reviewed by KO/CA lanes and routed to commit or quarantine.

## Key Output Fields

- `StateVector.hud.poincare_heat`
- `StateVector.hud.wall_pressure`
- `StateVector.hud.watcher_rings`
- `StateVector.hud.gate_locks`
- `DecisionRecord.action` (`ALLOW`, `QUARANTINE`, `DENY`)
- `voxel_keys_per_lang` and `StateVector.voxel_shard`

## Windows Line Ending Note

If you see `LF will be replaced by CRLF` warnings during `git add`, they are warnings, not failures.
To enforce LF for source/docs long-term, add a `.gitattributes` policy in the repo root.
