# deploy/

Deployment assets.

- `gcloud/` — Cloud Run Dockerfiles (main API, AetherBrowse, Hydra Armor), `cloudbuild.yaml`, `deploy.sh`, and a free-tier quickstart (`QUICKSTART.md`).
- `gateway/` — production docker-compose for the gateway.
- `postgres-lite/` — SQL run once on first Postgres container start.
- `multi_cloud_deploy.sh` — multi-cloud agent deployment script.

Kubernetes manifests are in `k8s/`; AWS assets are in `aws/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/deploy.md`](../docs/file-index/deploy.md).
