# SCBE-AETHERMOORE Execution Environment Appendix

Date: 2026-04-26

This appendix describes the current SCBE-AETHERMOORE deployment path for government and prime-contractor discussions. It is intentionally conservative: the repository contains working Kubernetes manifests and training automation, but this document does not claim IL5 authorization or production certification.

## Current Deployment Surfaces

SCBE-AETHERMOORE currently includes three Kubernetes deployment surfaces:

| Surface | Path | Current Role |
| --- | --- | --- |
| API/runtime deployment | `k8s/deployment.yaml`, `k8s/service.yaml`, `k8s/namespace.yaml` | Runs the SCBE API/runtime with health probes, persistent storage, service account, and resource limits. |
| Agent fleet manifests | `k8s/agent-manifests/` | Defines public, private, and hidden agent tiers with RBAC, Kafka, services, and network policies. |
| Training automation | `k8s/training/` | Provides training Jobs/CronJobs, persistent training data storage, and a GKE runbook for recurring pipeline execution. |

## New Hardening Stub

The repository includes a conservative government-cloud overlay stub:

`k8s/overlays/il5-govcloud/`

This overlay adds:

- Pod Security Standards labels for restricted enforcement.
- Default-deny network policies for runtime, agent, and training namespaces.
- DNS egress allowances required for Kubernetes service discovery.
- Agent-to-runtime egress allowance on the SCBE API port.
- Resource quotas and default container limits.
- Governance annotations for lineage, decision-envelope enforcement, and audit expectations.

## Why This Matters

This gives reviewers a concrete path from the current local-first and cloud-ready repo into a controlled deployment model. It separates what is already implemented from what still requires an authorized environment, cloud-prime support, and compliance validation.

## Remaining Production Gates

Before a live controlled deployment, SCBE-AETHERMOORE should add or verify:

- Authorized IL5 or equivalent cloud boundary with the prime or agency environment.
- External Secrets Operator or approved cloud secrets backend.
- Signed images, SBOM generation, vulnerability scanning, and admission policy enforcement.
- Runtime audit forwarding to the authorized SIEM or logging stack.
- Service mesh mTLS or equivalent east-west transport security.
- Cluster dry-run and policy review against the target Kubernetes distribution.
- Model and adapter lineage records for any deployed LLM training or inference components.

## Suggested Pilot Shape

A low-risk pilot should deploy one SCBE API/runtime service, one limited agent lane, and one training/evaluation Job lane. The pilot should prove:

- Workload health and rollback.
- Network isolation between tiers.
- Task provenance and artifact receipts.
- Frozen evaluation or executable-gate promotion for model/training outputs.
- Exportable audit logs and lineage summaries.

## Boundary Statement

SCBE-AETHERMOORE provides the technical runtime, agent-fleet structure, training/evaluation pipeline, and governance hooks. A prime contractor or authorized government cloud environment would provide the accredited boundary, compliance operations, and production authority to operate.

