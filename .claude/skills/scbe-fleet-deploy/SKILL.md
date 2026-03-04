---
name: scbe-fleet-deploy
description: Deploy trained models across the AI fleet — federated artifact fusion, quality gate checks, version promotion, multi-cloud orchestration, and rollback. Use when deploying models, promoting artifacts, checking deployment health, or managing the fleet release cycle.
---

# SCBE Fleet Deploy

Manage the deployment lifecycle from trained artifacts to running fleet agents.

## Deployment Pipeline

```
Trained Artifacts (HF, GCP, AWS)
    |
    v
Federated Fusion (training/federated_orchestrator.py)
    |
    v
Quality Gates (safety >= 0.95, quality >= 0.80)
    |
    v
Version Promotion (staging -> production)
    |
    v
Fleet Rollout (rolling update across agents)
    |
    v
Health Monitoring (coherence, latency, safety scores)
```

## Operations

### 1. Collect Artifacts
Gather training outputs from all providers:

```bash
# Each provider produces a manifest JSON
# HF: textgen models (LoRA adapters, full weights)
# GCP: embedding models (Vertex AI)
# AWS: runtime models (SageMaker endpoints)

ls training/manifests/
# hf_manifest.json  gcp_manifest.json  aws_manifest.json
```

### 2. Run Federated Fusion
```bash
python training/federated_orchestrator.py \
    --manifests training/manifests/*.json \
    --output training/fused_release.json \
    --min-quality 0.80 \
    --min-safety 0.95
```

### 3. Quality Gate Check
Every artifact must pass all gates before promotion:

| Gate | Threshold | Metric |
|------|-----------|--------|
| Quality | >= 0.80 | Task accuracy / BLEU / F1 |
| Safety | >= 0.95 | Governance compliance rate |
| Latency | <= 200ms p95 | Inference latency |
| Cost | <= $1.00/1K tokens | Compute cost |

Failed artifacts are rejected with detailed failure reports.

### 4. Version Promotion
```
staging -> canary (10% traffic) -> production (100%)
```

Each stage requires:
- Governance vote (BFT consensus from validator agents)
- Safety re-check at new scale
- Rollback plan documented

### 5. Fleet Rollout
Rolling update across the flock:

1. Select first batch (1 agent per specialty)
2. Deploy new model version
3. Monitor for 5 minutes (coherence, error rate)
4. If healthy: continue to next batch
5. If degraded: auto-rollback to previous version

### 6. Rollback
```bash
# Immediate rollback to last known good
python training/federated_orchestrator.py \
    --rollback \
    --target-version v2.1.0
```

### 7. Health Monitoring Post-Deploy
Track these metrics after deployment:

```python
# Per-agent metrics
agent.coherence       # Should stay > 0.7
agent.error_rate      # Should stay < 0.05
agent.response_time   # Should stay < target

# Fleet-wide metrics
fleet.consensus_rate  # BFT agreement percentage
fleet.safety_score    # Governance compliance
fleet.task_throughput # Tasks completed per minute
```

## Multi-Cloud Provider Map

| Provider | Role | Artifact Type | Region |
|----------|------|--------------|--------|
| HuggingFace | textgen | LoRA adapters, full weights | Global CDN |
| GCP Vertex | embed | Embedding models | us-central1 |
| AWS SageMaker | runtime | Inference endpoints | us-east-1 |

## Key Files

| File | Purpose |
|------|---------|
| `training/federated_orchestrator.py` | Multi-cloud artifact fusion + gates |
| `training/train_node_fleet_three_specialty.py` | 3-head specialty training |
| `hydra/spine.py` | Fleet coordination backbone |
| `hydra/swarm_governance.py` | BFT consensus for promotions |
| `agents/browser/fleet_coordinator.py` | Browser fleet management |

## Sacred Tongue Deploy Mapping

| Stage | Tongue | Meaning |
|-------|--------|---------|
| Build | CA (Cascade) | Breaking down, compiling |
| Test | RU (Runethic) | Binding, validating rules |
| Stage | UM (Umbroth) | Hidden, not yet revealed |
| Deploy | KO (Kor'aelin) | Asserting into production |
| Monitor | AV (Avali) | Listening, watching |
| Rollback | DR (Draumric) | Structured retreat |
