# NotebookLM Connector

Terminal-first NotebookLM automation bridge.

## Files

- `scripts/system/notebooklm_connector.py`
- `scripts/system/notebooklm_connector.ps1`
- `src/fleet/connector_bridge.py` platform: `notebooklm`

## Actions

1. `profile` — verify local runtime readiness and registry status.
2. `resolve-notebook` — resolve notebook by URL, ID, or title from registry.
3. `create-notebook` — create notebook or reuse existing by title.
4. `add-source-url` — attach URL source to notebook (by URL or title).
5. `seed-notebooks` — create/reuse multiple notebooks and add shared URLs.
6. `ingest-report` — read local report files, extract URLs, attach as sources.
7. `agent-dual` — visual lane preview + writer lane source/prompt submission.

## Quick start (PowerShell)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\notebooklm_connector.ps1 -Action profile -Session 1
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\notebooklm_connector.ps1 -Action create-notebook -Session 1 -Title "Hydra Research 01"
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\notebooklm_connector.ps1 -Action add-source-url -Session 1 -NotebookUrl "https://notebooklm.google.com/notebook/<id>" -SourceUrl "https://arxiv.org/abs/2501.00001"
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\notebooklm_connector.ps1 -Action seed-notebooks -Session 1 -Count 3 -NamePrefix "Hydra Batch" -SourceUrl "https://arxiv.org" -SourceUrl "https://example.com/report"
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\notebooklm_connector.ps1 -Action ingest-report -Session 1 -Title "Hydra Batch 01" -ReportFile ".\docs\research\sample.md"
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\notebooklm_connector.ps1 -Action agent-dual -Session 1 -Title "Hydra Batch 01" -SourceUrl "https://arxiv.org/abs/2406.00001" -Prompt "Summarize the top findings and list gaps."
```

## Runtime notes

- Browser mode requires the Playwriter Chrome extension connected to an active tab.
- Artifacts are written to `artifacts/notebooklm/`.
- Notebook registry is persisted at `artifacts/notebooklm/notebook_registry.json`.
- If UI selectors change in NotebookLM, run with `-DryRun` to inspect the generated browser expression and adjust.
