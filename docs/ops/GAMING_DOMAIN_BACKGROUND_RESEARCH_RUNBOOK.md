# Gaming Domain Background Research Runbook

Run game-industry domain research in the background using SCBE HYDRA ingestion.

## Start (background)

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\start_gaming_domain_research_background.ps1
```

## Check status

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\get_gaming_domain_research_status.ps1
```

## Stop

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\system\stop_gaming_domain_research_background.ps1
```

## Inputs

- Topic seeds: `training/topics/gaming_domains_topics.txt`
- URL seeds: `training/topics/gaming_domains_seed_urls.json`

## Outputs

- Job metadata: `artifacts/background_jobs/gaming_domains/latest.json`
- Logs: `artifacts/background_jobs/gaming_domains/*.log`
- Pipeline runs: `training/runs/web_research/<run_id>/`
