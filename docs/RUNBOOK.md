# SCBE Operational Runbook

Last updated: 2026-02-17

## Goal

Run SCBE-AETHERMOORE from kernel validation through browser execution, orchestration, cloud deployment, and training data workflows in a deterministic order.

## Step 1: Validate canonical contracts

Commands:

```powershell
python scripts/validate_layer_manifest.py
```

Checks:
1. `docs/scbe_full_system_layer_manifest.json` format and required fields.
2. Layer dependency references (`depends_on`) are valid.
3. `last_verified_commit` values are structurally valid hashes.

## Step 2: Bring up local governed browser service

Commands:

```powershell
.\scripts\run_aetherbrowse_service.ps1 -SCBEKey "<32-char-key>" -Port 8001 -KillOnPortInUse
```

Health check (new terminal):

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/health"
```

## Step 3: Execute multi-agent browser jobs

Commands:

```powershell
python scripts\aetherbrowse_swarm_runner.py --tasks examples\aetherbrowse_tasks.sample.json
```

Expected artifact surfaces:
1. `training/runs/` output payloads.
2. Decision-record linked results per job.

## Step 4: Execute orchestration connectors (Asana + n8n)

Commands:

```powershell
python scripts\asana_aetherbrowse_orchestrator.py --help
python scripts\n8n_aetherbrowse_bridge.py --help
```

Required environment:
1. `ASANA_TOKEN`
2. `N8N_API_KEY`
3. `SCBE_API_KEY`
4. `SCBE_BROWSER_WEBHOOK_URL`

## Step 5: Deploy cloud execution plane (Cloud Run)

Commands:

```bash
bash deploy/gcloud/deploy_aetherbrowse.sh
```

Required environment:
1. `GCP_PROJECT_ID`
2. `GCP_REGION`
3. `SCBE_API_KEY`

## Step 6: Run training/data plane

Commands:

```powershell
python scripts\notion_access_check.py
python scripts\notion_to_dataset.py
python scripts\push_to_hf.py
```

Required environment:
1. `NOTION_API_KEY`
2. `HF_TOKEN`
3. `GCP_SA_KEY` (for Vertex workflows)

## Step 7: CI gates and release handoff

Commands:

```powershell
gh workflow run "Validate Layer Manifest"
gh workflow run "ci.yml"
```

Release condition:
1. Layer manifest validator passes.
2. Core CI gates pass.
3. Any layer status changes are reflected in `docs/scbe_full_system_layer_manifest.json`.
