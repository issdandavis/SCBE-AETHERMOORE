# SCBE Bootstrap Runbook

Date: 2026-02-26

## Purpose

One command to verify local prerequisites, import n8n workflows, and optionally build the training funnel and start services.

## Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scbe_bootstrap.ps1
```

Or from npm:

```powershell
npm run scbe:bootstrap
```

## Common Options

Fresh n8n workspace import:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scbe_bootstrap.ps1 -ResetN8nUserFolder
```

Import and publish workflows as active:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scbe_bootstrap.ps1 -PublishWorkflows
```

Build funnel during bootstrap:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scbe_bootstrap.ps1 -BuildTrainingFunnel
```

Start bridge + n8n after checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scbe_bootstrap.ps1 -StartServices
```

Skip workflow import (for quick command availability check only):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\scbe_bootstrap.ps1 -NoImportWorkflows
```

## Output Artifact

Bootstrap writes a timestamped report to:
- `artifacts/bootstrap/bootstrap_report_<timestamp>.json`

The report includes:
- command availability checks,
- bridge import status,
- workflow import status and workflow count,
- optional funnel build status,
- optional service start status.
