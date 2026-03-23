# SCBE Internet Navigation Command Lanes

## Shell A: Keep stack alive
```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\bootstrap_24x7_local.ps1 -ZapierWebhookUrl "https://hooks.zapier.com/hooks/catch/23283477/u0m7e1x/"
```

## Shell B: HYDRA browse evidence
```powershell
node C:\Users\issda\.codex\skills\hydra-node-terminal-browsing\scripts\hydra_terminal_browse.mjs --url "https://example.com" --out "C:\Users\issda\SCBE-AETHERMOORE\artifacts\page_evidence\terminal_evidence.json"
```

## Shell C: Playwright + system smoke
```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
python scripts/system/full_system_smoke.py --bridge-url http://127.0.0.1:8002 --browser-url http://127.0.0.1:8012 --n8n-url http://127.0.0.1:5680 --probe-webhook --output artifacts/system_smoke/manual_smoke_2026-02-27.json
```

## Shell D: Hydra Armor ingest from Notion + GitHub
```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\run_hydra_armor_bridge.ps1
```

## Shell E: Connector goals directly
```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\run_connector_goal.ps1 -Goal "run notion armor sync now" -ConnectorName "notion-research-sync"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\run_connector_goal.ps1 -Goal "run github armor sync now" -ConnectorName "github-actions-fleet"
```

## Shell F: Dataset + table sync lanes
```powershell
# Hugging Face dataset publish lane (example)
# hf upload <dataset-repo> training-data/ --repo-type dataset

# Airtable lane via connector goal
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\run_connector_goal.ps1 -Goal "run airtable funnel sync now" -ConnectorName "airtable-funnel-sync"
```
