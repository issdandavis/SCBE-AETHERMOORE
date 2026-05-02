# Rho logging (`composite_harmonic_wall`)

Instrumentation lives in `src/symphonic_cipher/scbe_aethermoore/axiom_grouped/polyhedral_flow.py` (env-gated, fail-soft).

## PowerShell (Windows): use `$env:`, not `export`

Bash-style `export VAR=value` does **not** work in PowerShell.

```powershell
# Enable for this session only (recommended for measurement runs)
$env:SCBE_RHO_LOG = "1"
$env:SCBE_RHO_LOG_PATH = "artifacts/rho_logging/composite_wall_rho.jsonl"

# Verify
$env:SCBE_RHO_LOG
$env:SCBE_RHO_LOG_PATH

# Turn off
Remove-Item Env:SCBE_RHO_LOG -ErrorAction SilentlyContinue
Remove-Item Env:SCBE_RHO_LOG_PATH -ErrorAction SilentlyContinue
```

Optional absolute path:

```powershell
$env:SCBE_RHO_LOG_PATH = "$(Get-Location)\artifacts\rho_logging\composite_wall_rho.jsonl"
```

## Workflow

1. Set the two env vars in the **same** shell (or process) that runs code calling `composite_harmonic_wall`.
2. Run your app / tests / harness until the JSONL has enough rows (Pearson warms after 32 samples per axis in-process).
3. Read out:

```powershell
python scripts/analyze_rho_log.py
python scripts/analyze_rho_log.py --json
python scripts/analyze_rho_log.py --hint
python scripts/analyze_rho_log.py --hint-only
```

## Synthetic smoke (no live traffic)

```powershell
# From repo root; PYTHONPATH is set inside the script
python scripts/rho_logging/generate_sample_rho_log.py --iterations 128 --truncate

# Or one-shot (truncate + generate + table):
powershell -NoProfile -File scripts/windows/capture_rho_log_smoke.ps1

# Only analyze an existing log (e.g. after a long run):
powershell -NoProfile -File scripts/windows/capture_rho_log_smoke.ps1 -AnalyzeOnly -Hint
```

## Empirical decision (hint)

`--hint` summarizes whether `rho_latest` shows enough per-tongue spread to justify a **dynamic relation-radii** experiment vs keeping the **static φⁿ** baseline. See `decision_hint` in `scripts/analyze_rho_log.py` when using `--json --hint`.

## Tests

- `tests/test_polyhedral_flow_rho_logging.py` — logger + Pearson
- `tests/test_rho_logging_generator_smoke.py` — generator → analyzer
- `tests/test_analyze_rho_log_hint.py` — hint thresholds
