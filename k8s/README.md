# k8s/

Kubernetes manifests.

- `namespace.yaml`, `deployment.yaml`, `service.yaml` — the SCBE API deployment.
- `agent-manifests/` — agent fleet: hidden agents, Kafka, network policies, kustomization.
- `training/` — GKE training jobs (node-fleet CronJob and the PHDM-21D long-run Job). Runbook in `training/README.md`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/k8s.md`](../docs/file-index/k8s.md).
