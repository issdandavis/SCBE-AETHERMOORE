# SCBE-AETHERMOORE IL5-GovCloud Overlay Stub

This overlay is a conservative hardening starting point for controlled government cloud discussions. It is not an IL5 authorization package and does not claim certification.

Use this layer to show how the current SCBE-AETHERMOORE Kubernetes surfaces can be moved toward a governed deployment model:

- `scbe-aethermoore`: API/runtime namespace.
- `scbe-agents`: agent fleet namespace.
- `scbe-training`: training and recurring pipeline namespace.

## What This Adds

- Pod Security Standards labels for `restricted` enforcement.
- Default-deny ingress and egress network policies.
- DNS egress allowance for Kubernetes service discovery.
- Namespace resource quotas and default limits.
- Deployment annotations that mark governance, lineage, and audit expectations.

## What This Does Not Yet Provide

- FedRAMP High or IL5 authorization.
- Cloud-provider specific controls for AWS GovCloud, Azure Government, or GCP Assured Workloads.
- Signed image provenance, SBOM enforcement, or admission control.
- External Secrets Operator integration.
- Runtime detection through Falco, audit sinks, Loki, or SIEM forwarding.
- Service mesh mTLS.

## Validation Intent

This overlay exists to make the deployment path concrete for RFI and prime-sub conversations. Before live deployment, the next gate is a real cluster dry-run plus admission-policy review:

```powershell
kubectl kustomize k8s/overlays/il5-govcloud
kubectl apply --dry-run=server -k k8s/overlays/il5-govcloud
```

