# Terminal AI Autopilot Setup (SCBE)

This is the fastest way to run your AI ops loop from terminal with cheap/local defaults.

## One-command setup

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\setup_terminal_ai_ops.ps1 -IntervalHours 4 -EnableMoney -StartNow -ConfigureGrokFromEnv
```

What this does:
- wires Grok key from `.env` into `~/.grok/user-settings.json` (hidden, never printed),
- registers `SCBE-OpsAutopilot` scheduled task (every 4h),
- triggers one run immediately,
- falls back to a hidden background loop if Task Scheduler is blocked.

## Status checks

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
Get-Content .\artifacts\ops-autopilot\latest.json -TotalCount 120
```

```powershell
Get-ScheduledTask -TaskName SCBE-OpsAutopilot | Format-List TaskName,State,LastRunTime,NextRunTime
```

## Trigger another run now

```powershell
Start-ScheduledTask -TaskName SCBE-OpsAutopilot
```

## Stop/disable scheduler

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\register_autopilot_task.ps1 -Unregister
```

## Headless one-shot run (no scheduler)

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
python .\scripts\ops_24x7_autopilot.py --scan-name manual --repeat-every-minutes 0 --iterations 1 --run-money --money-probe --no-run-smoke
```
