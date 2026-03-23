# Control Plane And Command Center

This is the fastest path into the live local system.

## Core Files

- `scripts/hydra_command_center.ps1`
- `scripts/install_hydra_quick_aliases.ps1`
- `scripts/scbe-system-cli.py`
- `scripts/scbe_terminal_ops.py`
- `docs/ISSAC_QUICKSTART.md`
- `docs/ISSAC_COMMAND_CENTER.md`
- `package.json`

## First-Time Local Setup

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE
.\scripts\install_hydra_quick_aliases.ps1
issac-help
```

Open a fresh PowerShell window if the aliases do not appear immediately.

## Fast Health Checks

```powershell
hstatus
hqueue
Get-Command hstatus,hqueue,scbe-api,scbe-bridge,octo-serve
```

## Main Entry Points

### PowerShell command center

```powershell
issac-help
hresearch "topic"
hdeep "topic"
hswarm "task"
hwf
```

Use this when you want the fastest shell-driven workflow and do not want to remember raw script names.

### Unified SCBE CLI

```powershell
python scripts/scbe-system-cli.py --help
python scripts/scbe-system-cli.py status
python scripts/scbe-system-cli.py tongues --help
python scripts/scbe-system-cli.py runtime --help
python scripts/scbe-system-cli.py pollypad --help
```

Use this when you want a single Python CLI that can fan into tongues, web, runtime, antivirus, or Polly Pad operations.

### Terminal Ops API wrapper

```powershell
python scripts/scbe_terminal_ops.py --help
```

Use this when you need terminal-first calls into the mobile/connector API layer.

### npm script surface

```powershell
npm run typecheck
npm test
npm run test:python
npm run system:cli -- --help
npm run mcp:doctor
```

Use this when the task lives in the Node/TS build or service layer.

## When To Use This Guide

- You are starting work and need the right entrypoint fast.
- You are unsure whether the task should go through PowerShell, Python CLI, or npm.
- You want to keep using the local integrated stack instead of drifting into ad hoc one-off scripts.
