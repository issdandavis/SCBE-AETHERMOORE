# Multi-Cloud Long-Run Training Bootstrap

This repo now has a practical overnight bootstrap for:
- Vertex AI embeddings run (`training/trigger_vertex_training.py`)
- Kubernetes long-run job scaffold (`k8s/training/phdm21d-longrun-training.yaml`)
- AWS SageMaker launch template (`training/aws_sagemaker_long_run_training_job.json`)
- Hugging Face lane placeholder (`scripts/train_hf_longrun_placeholder.py`)

## Start in one command (Windows)

```powershell
.\scripts\run-long-run-training.ps1 -Hours 8
```

That prints what will run by default, and writes a report at:
`training/runs/<timestamp>/training_bootstrap_report.json`.

To include all lanes including the HF placeholder:

```powershell
.\scripts\run-long-run-training.ps1 -Hours 8 -AllowPending
```

To actually start jobs (you must have all provider credentials available):

```powershell
.\scripts\run-long-run-training.ps1 -Hours 8 -Execute
```

## Provider controls

You can target providers with `-Providers`.

```powershell
.\scripts\run-long-run-training.ps1 -Hours 8 -Execute -Providers vertex-ai,kubernetes,aws-sagemaker
```

Available IDs:
- `vertex-ai`
- `kubernetes`
- `aws-sagemaker`
- `huggingface` (pending placeholder)

## What to do tomorrow morning

1. Validate secret and infra variables:
   - `GCP_PROJECT_ID`, `GCP_REGION`, `HF_TOKEN`, `HF_MODEL_REPO`
   - `AWS_REGION`, `SAGEMAKER_EXECUTION_ROLE_ARN`, `S3_TRAINING_DATA_URI`, `S3_OUTPUT_PATH`
   - `KUBECONFIG` (for Kubernetes lane)
2. Run a dry plan from your machine:
   - `.\scripts\run-long-run-training.ps1 -Hours 8`
3. Start with one lane at a time with `-Providers`.
4. When each lane is stable, run `-Execute` with all lanes.

## GitHub workflow

`/.github/workflows/nightly-multicloud-training.yml` runs a scheduled dry-run at 02:00 UTC and can
execute on-demand via workflow_dispatch with `execute=true`.

## Current status

- Vertex/Kubernetes/AWS lanes are wired to a bootstrap manifest and launch paths.
- Hugging Face lane is intentionally marked **pending** until you wire your real trainer command in `train_hf_longrun_placeholder.py` / plan.
