# SCBE Workcell Quickstart

SCBE Workcell is a downloadable command-line workcell for governed AI operations.

It gives you the `scbe`, `geoseal`, and `scbe-geoseal` commands without cloning
the full SCBE-AETHERMOORE repository.

## Requirements

- Node.js 20 or newer
- npm
- Windows PowerShell, macOS Terminal, or Linux shell

## Install From The Download Bundle

Unzip the download. Inside the folder you will see an npm package named like:

```text
scbe-aethermoore-cli-4.4.0.tgz
```

Install it globally:

```powershell
npm install -g .\scbe-aethermoore-cli-4.4.0.tgz
```

On macOS/Linux:

```bash
npm install -g ./scbe-aethermoore-cli-4.4.0.tgz
```

## First Commands

```bash
scbe version
scbe demo --json
scbe tools --json
scbe selftest
```

## What It Does

- `scbe version` proves the command is installed.
- `scbe demo --json` shows the governed AI-tool-call safety demo.
- `scbe tools --json` lists the command manifest for humans or agents.
- `scbe selftest` checks the installed command path.

## Buyer Promise

SCBE Workcell is not a magic cloud agent. It is a local governed command surface:

- commands are explicit
- risky operations go through GeoSeal-style gating
- outputs can be recorded as receipts
- local/free routes come first
- paid or cloud routes require user configuration

## Update

When a new bundle is released, install the new `.tgz` the same way:

```bash
npm install -g ./scbe-aethermoore-cli-NEW_VERSION.tgz
```

## Uninstall

```bash
npm uninstall -g scbe-aethermoore-cli
```
