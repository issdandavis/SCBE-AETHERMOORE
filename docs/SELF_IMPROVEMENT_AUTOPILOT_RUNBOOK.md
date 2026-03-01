# SCBE Self-Improvement Ops Autopilot (Free-Cost Path)

Use this for nonstop low-cost progress without paying for GPU time.

## What it runs

1. Repo scan (`scripts/repo_scanner.py`)
2. Scan postprocess + task prioritization (`scripts/scan_postprocess.py`)
3. Optional local HF smoke test (`training/hf_smoke_sft_uv.py`) in CPU mode
4. AI→AI packet emission into shared location
5. Optional Obsidian session note via `scripts/obsidian_ai_hub.py`

## One-shot run

```powershell
python scripts/run_ops_autopilot.py --obsidian-vault "C:\Users\issda\OneDrive\Dropbox\Izack Realmforge\AI Workspace"
```

Skips smoke:

```powershell
python scripts/run_ops_autopilot.py --skip-smoke
```

## Windows scheduled 24/7 cadence

Create a user task to run every 4 hours:

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\issda\SCBE-AETHERMOORE\scripts\run_ops_autopilot.py --obsidian-vault `"C:\Users\issda\OneDrive\Dropbox\Izack Realmforge\AI Workspace`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date "03:00") -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType InteractiveToken
Register-ScheduledTask -TaskName "SCBE-Autopilot" -Action $action -Trigger $trigger -Principal $principal -Description "Free-cost SCBE ops loop"
```

## Where outputs land

- `artifacts/repo_scans/<timestamp>-full_codebase`
- `artifacts/repo_scans/<timestamp>-full_codebase/<timestamp>-full_codebase/postprocess` (scan output is nested inside scanner stamp dir)
- `artifacts/ops-autopilot/latest.json`
- `C:\Users\issda\OneDrive\Dropbox\SCBE-AI-Comm\packets\`

## Cost notes

- The default loop is local-only when smoke is enabled with CPU env defaults (`SCBE_SMOKE_USE_CPU=1` and low `SCBE_SMOKE_MAX_STEPS`).
- It is free in compute cost when you are not using Hugging Face paid jobs / external GPUs.
