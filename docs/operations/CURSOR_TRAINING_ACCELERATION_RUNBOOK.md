# Cursor Training Acceleration Runbook

Cursor is installed at:

```text
C:\Users\issda\AppData\Local\Programs\cursor\resources\app\bin\cursor.cmd
```

Use Cursor as a parallel editor for narrow lanes while Codex owns terminal verification, commits, external publishing, and final promotion decisions.

## Start Cursor

From the repo root:

```powershell
cursor .
```

If `cursor` is not on `PATH`, use:

```powershell
& "C:\Users\issda\AppData\Local\Programs\cursor\resources\app\bin\cursor.cmd" .
```

## Fast Tasks

Open Command Palette in Cursor, run `Tasks: Run Task`, then pick one of the `SCBE:` tasks.

Recommended order for the active training lane:

1. `SCBE: Kaggle Approval V2 Ready`
2. `SCBE: Kaggle Active Status`
3. `SCBE: Kaggle Approval V2 Pattern Score`
4. `SCBE: Kaggle Approval V2 Launch` only when the ready check says slots are free

Recommended order for adapter review:

1. `SCBE: Frozen Eval Fresh HF v7`
2. `SCBE: Functional Benchmark Fresh HF v7`
3. `SCBE: Gate Latest Functional Benchmark`

## Division Of Labor

Cursor can safely handle docs, tests, isolated scripts, dataset validation, and small refactors.

Codex should keep ownership of:

- Git staging and commits.
- HF/Kaggle launch decisions.
- Proton/Gmail sends.
- BAAT/SAM uploads.
- Adapter promotion and merge decisions.
- Secret sweep and credential handling.

## Safety Rules

Do not edit `.env*`, `config/connector_oauth/**`, OAuth files, Proton/Gmail credentials, HF tokens, or generated caches.

Do not merge adapters from perplexity alone. The functional benchmark gate is required because the latest v7 run improved frozen perplexity but regressed executable coding behavior.
