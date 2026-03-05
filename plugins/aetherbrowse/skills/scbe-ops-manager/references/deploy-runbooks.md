# Deployment Runbooks

Step-by-step procedures for deploying SCBE-AETHERMOORE services.

## Hydra Armor API to Cloud Run (Recommended First Deploy)

**Cost**: $0/month (free tier, 2M requests/month)
**Time**: ~5 minutes
**Prerequisites**: `gcloud` CLI authenticated, project created

### Steps

1. **Pre-check**:
   ```bash
   gcloud auth list
   gcloud config get-value project
   ```

2. **Verify Dockerfile builds locally** (optional):
   ```bash
   docker build -f deploy/gcloud/Dockerfile.hydra-armor -t hydra-armor-test .
   docker run -p 8400:8400 hydra-armor-test
   curl http://localhost:8400/v1/armor/health
   ```

3. **Deploy**:
   ```bash
   bash deploy/gcloud/deploy_hydra_armor.sh [PROJECT_ID] [REGION]
   ```
   Defaults: project from `gcloud config`, region `us-central1`.

4. **Post-deploy verification**:
   ```bash
   SERVICE_URL=$(gcloud run services describe hydra-armor-api \
     --platform managed --region us-central1 --format='value(status.url)')
   curl $SERVICE_URL/v1/armor/health
   curl -X POST $SERVICE_URL/v1/armor/verify \
     -H 'Content-Type: application/json' \
     -d '{"agent_id":"smoke","action":"click","selector":"#test","context":"deploy-check"}'
   ```

5. **Emit ship packet** with the SERVICE_URL as proof.

### Endpoints Available

- `POST /v1/armor/verify` — Action-level governance check
- `POST /v1/hydra-armor` — Multi-head consensus on browser snapshot
- `GET /v1/armor/health` — API health
- `GET /v1/armor/usage/{agent_id}` — Usage stats per agent
- `GET /health` — Runtime health

## AetherBrowse Full Stack to Cloud Run

**Cost**: ~$5/month (needs more memory for Playwright)
**Time**: ~10 minutes
**Prerequisites**: `gcloud` CLI, project with billing

### Steps

1. **Deploy**:
   ```bash
   bash deploy/gcloud/deploy_aetherbrowse.sh [PROJECT_ID] [REGION]
   ```

2. **Post-deploy**:
   ```bash
   SERVICE_URL=$(gcloud run services describe aetherbrowse \
     --platform managed --region us-central1 --format='value(status.url)')
   curl $SERVICE_URL/health
   curl $SERVICE_URL/api/status
   ```

## Free VM (e2-micro) — All Services

**Cost**: $0/month (GCP Always Free tier)
**Time**: ~15 minutes first deploy
**Prerequisites**: `gcloud` CLI, project

### Steps

1. **Deploy**:
   ```bash
   bash deploy/gcloud/deploy_free_vm.sh [PROJECT_ID] [ZONE]
   ```
   Default zone: `us-central1-a`

2. **Services started via systemd**:
   - Port 8400: AetherBrowse runtime
   - Port 8001: n8n bridge
   - Port 5678: n8n

3. **Post-deploy SSH**:
   ```bash
   gcloud compute ssh scbe-free --zone us-central1-a
   systemctl status scbe-runtime scbe-bridge
   curl localhost:8400/health
   ```

## Local Development Stack

### Minimal (runtime only)

```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400 --reload
```

### Full stack (runtime + bridge + n8n)

```bash
# Terminal 1: Runtime
python -m uvicorn aetherbrowse.runtime.server:app --host 127.0.0.1 --port 8400 --reload

# Terminal 2: Bridge
python -m uvicorn workflows.n8n.scbe_n8n_bridge:app --host 127.0.0.1 --port 8001 --reload

# Terminal 3: n8n
n8n start
```

### With Electron shell

```bash
cd aetherbrowse
npm install
npm start
```

## Shopify Product Sync

### Dry run (preview changes)

```bash
python scripts/shopify_bridge.py products --dry-run
```

### Publish live

```bash
python scripts/shopify_bridge.py products --publish-live
```

### Required env vars

- `SHOPIFY_STORE_URL` — e.g. `aethermore-works.myshopify.com`
- `SHOPIFY_ACCESS_TOKEN` — Admin API access token

## Pre-Deploy Checklist

Before any production deployment:

1. **Tests pass**:
   ```bash
   npx vitest run tests/shell-executor.test.ts tests/swarm_governance.test.ts tests/interop.test.ts
   ```

2. **No secrets in code**: Grep for keys/tokens
   ```bash
   grep -rn "sk-\|SHOPIFY_ACCESS_TOKEN=\|password=" --include="*.py" --include="*.ts" --include="*.js" src/ aetherbrowse/
   ```

3. **Docker builds clean** (for Cloud Run):
   ```bash
   docker build -f deploy/gcloud/Dockerfile.hydra-armor -t test .
   ```

4. **Governance policies reviewed**: `aetherbrowse/config/governance_policies.yaml`

5. **Model routing configured**: `aetherbrowse/config/model_routing.yaml`

## Rollback Procedure

### Cloud Run

```bash
# List revisions
gcloud run revisions list --service hydra-armor-api --region us-central1

# Route traffic to previous revision
gcloud run services update-traffic hydra-armor-api \
  --to-revisions=hydra-armor-api-00001-abc=100 \
  --region us-central1
```

### Local

```bash
git log --oneline -5
git checkout {previous-commit} -- aetherbrowse/runtime/server.py
# Restart uvicorn
```
