# SCBE Training on GKE Runbook

This runbook deploys and operates:
- `codex-ingest-daily` (daily codex ingest)
- `node-fleet-train-6h` (every 6 hours node-fleet training + news)

Manifest:
- `k8s/training/node-fleet-gke-automation.yaml`

One-click scripts:
- `scripts/gke_training_oneclick.sh`
- `scripts/gke_training_oneclick.ps1`

## 1) Prerequisites

- `kubectl` authenticated to your GKE cluster
- Namespace access for `scbe-training`
- Image exists: `ghcr.io/issdandavis/scbe-aethermoore:latest`
- Secrets ready:
  - `HF_TOKEN`
  - `NOTION_TOKEN`

## 2) First-time deploy

```bash
kubectl create namespace scbe-training --dry-run=client -o yaml | kubectl apply -f -

kubectl -n scbe-training create secret generic hf-secrets \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n scbe-training create secret generic notion-secrets \
  --from-literal=token="$NOTION_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/training/node-fleet-gke-automation.yaml
```

Or run one-click:

```bash
HF_TOKEN=... NOTION_TOKEN=... scripts/gke_training_oneclick.sh
```

```powershell
$env:HF_TOKEN = "..."
$env:NOTION_TOKEN = "..."
.\scripts\gke_training_oneclick.ps1
```

## 3) Verify deployment

```bash
kubectl -n scbe-training get cronjobs
kubectl -n scbe-training get pvc
kubectl -n scbe-training get configmap node-fleet-automation-config -o yaml
```

Expected:
- CronJobs exist: `codex-ingest-daily`, `node-fleet-train-6h`
- PVC exists: `scbe-training-data`

## 4) Manual run now (without waiting schedule)

### Run codex ingest now

```bash
kubectl -n scbe-training create job --from=cronjob/codex-ingest-daily codex-ingest-manual-$(date +%s)
```

### Run node-fleet training now

```bash
kubectl -n scbe-training create job --from=cronjob/node-fleet-train-6h node-fleet-manual-$(date +%s)
```

## 5) Observe jobs and logs

```bash
kubectl -n scbe-training get jobs
kubectl -n scbe-training get pods
kubectl -n scbe-training logs job/<job-name> --tail=200
```

## 6) Update schedules or config

Edit and re-apply:

```bash
kubectl apply -f k8s/training/node-fleet-gke-automation.yaml
```

Common edits:
- `spec.schedule` on each `CronJob`
- `EPOCHS`, `DOCS_GLOB_1`, `PUSH_TO_HUB` in `ConfigMap`
- resource requests/limits in container specs

## 7) Rollback

If a new apply breaks behavior, re-apply previous known-good manifest version:

```bash
git checkout <known-good-commit> -- k8s/training/node-fleet-gke-automation.yaml
kubectl apply -f k8s/training/node-fleet-gke-automation.yaml
```

Emergency stop:

```bash
kubectl -n scbe-training patch cronjob codex-ingest-daily -p '{"spec":{"suspend":true}}'
kubectl -n scbe-training patch cronjob node-fleet-train-6h -p '{"spec":{"suspend":true}}'
```

Resume:

```bash
kubectl -n scbe-training patch cronjob codex-ingest-daily -p '{"spec":{"suspend":false}}'
kubectl -n scbe-training patch cronjob node-fleet-train-6h -p '{"spec":{"suspend":false}}'
```

## 8) Full uninstall

```bash
kubectl delete -f k8s/training/node-fleet-gke-automation.yaml
kubectl -n scbe-training delete secret hf-secrets notion-secrets
# Optional namespace wipe:
# kubectl delete namespace scbe-training
```

## 9) Quick troubleshooting

- `ImagePullBackOff`:
  - verify image exists and cluster has pull access to `ghcr.io/issdandavis/scbe-aethermoore:latest`
- `CreateContainerConfigError`:
  - verify `hf-secrets` and `notion-secrets` exist with key `token`
- jobs fail parsing run dir:
  - check trainer output logs for `Run dir:` line from `scripts/run_node_fleet_pipeline.py`
- no new news output:
  - verify `scripts/generate_node_fleet_news.py` is present in image
- low throughput / OOM:
  - increase memory/cpu limits in manifest
