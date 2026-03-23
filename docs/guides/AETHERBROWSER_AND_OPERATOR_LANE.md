# AetherBrowser And Operator Lane

This is the browser-first execution surface for GitHub, Hugging Face, Notion, arXiv, and general web work.

## Core Files

- `src/aetherbrowser/`
- `src/browser/`
- `scripts/system/aetherbrowser_model_cli.py`
- `scripts/system/aetherbrowser_search.py`
- `scripts/verify_aetherbrowser_extension_service.py`
- `scripts/system/start_aetherbrowser_extension_service.ps1`
- `scripts/system/stop_aetherbrowser_extension_service.ps1`

## Start And Verify

```powershell
npm run aetherbrowser:service:start
npm run aetherbrowser:service:verify
```

Use these first when the browser lane is supposed to be live.

## Run A Model-Planned Browser Task

```powershell
python scripts/system/aetherbrowser_model_cli.py "inspect the current Hugging Face dataset state" --provider huggingface --json
```

This logs the plan/execution pair into:

- `artifacts/aetherbrowser_cli/run-*/result.json`
- `training-data/browser/aetherbrowser_model_cli_calls.jsonl`

## Run Unified Search

```powershell
python scripts/system/aetherbrowser_search.py --surface github --query "SCBE AetherBrowser"
python scripts/system/aetherbrowser_search.py --surface huggingface --query "scbe pivot"
```

## When To Use This Lane

- You want browser work to stay inside SCBE rather than defaulting to a generic browser.
- You want page evidence, operator logs, or training capture from browser tasks.
- You want provider-aware model routing attached to the browser workflow.

## Repo Role

The separate GitHub repo `aetherbrowser` is best treated as an extraction lane. The live integrated browser/operator system is still in this monorepo.
