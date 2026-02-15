#!/usr/bin/env python3
"""PHDM 21D Embedding Model - Vertex AI Training Trigger

Triggers a Vertex AI custom training job for the PHDM 21D embedding model.
Uses the pipeline config from vertex_pipeline_config.yaml and pushes
trained weights to HuggingFace Hub.

Usage:
    python trigger_vertex_training.py [--dry-run] [--config PATH]
"""

import os
import sys
import json
import yaml
import argparse
import logging
from pathlib import Path
from datetime import datetime
from kernel_manifest import load_manifest, to_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULTS = {
    "project_id": os.environ.get("GCP_PROJECT_ID", "studio-6928670609-fdd4c"),
    "region": os.environ.get("GCP_REGION", "us-west1"),
    "hf_model_repo": os.environ.get("HF_MODEL_REPO", "issdandavis/phdm-21d-embedding"),
    "gke_cluster": os.environ.get("GKE_CLUSTER_NAME", "test-scbecluser"),
    "staging_bucket": "gs://scbe-vertex-staging",
}


def load_pipeline_config(config_path=None):
    """Load the Vertex AI pipeline YAML config."""
    if config_path is None:
        config_path = Path(__file__).parent / "vertex_pipeline_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)




def load_kernel_summary(manifest_path=None):
    """Load canonical kernel file summary for training provenance."""
    if manifest_path is None:
        manifest_path = Path(__file__).parent / "kernel_manifest.yaml"
    manifest = load_manifest(manifest_path)
    return to_summary(manifest)


def validate_environment(dry_run=False):
    """Check that required env vars and credentials are present."""
    required = ["GCP_PROJECT_ID"]
    if not dry_run:
        required.extend(["HF_TOKEN"])
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        log.error("Missing environment variables: %s", ", ".join(missing))
        sys.exit(1)
    log.info("Environment validated - all required vars present")


def create_training_job(cfg, pipeline, kernel_summary, dry_run=False):
    """Submit a Vertex AI CustomJob for PHDM 21D embedding training."""
    try:
        from google.cloud import aiplatform
    except ImportError:
        if not dry_run:
            log.error("google-cloud-aiplatform not installed. Run: pip install google-cloud-aiplatform")
            sys.exit(1)
        log.warning("google-cloud-aiplatform not available (ok for dry-run)")

    model_cfg = pipeline.get("model", {})
    training_cfg = pipeline.get("training", {})
    infra_cfg = pipeline.get("infrastructure", {})

    job_name = "phdm-21d-train-%s" % datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    worker_pool = [{
        "machine_spec": {
            "machine_type": infra_cfg.get("machine_type", "n1-standard-8"),
            "accelerator_type": infra_cfg.get("accelerator_type", "NVIDIA_TESLA_T4"),
            "accelerator_count": infra_cfg.get("accelerator_count", 1),
        },
        "replica_count": 1,
        "container_spec": {
            "image_uri": infra_cfg.get("container_image",
                "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-1:latest"),
            "command": ["python", "-m", "training.train_phdm"],
            "args": [
                "--dimensions=%s" % model_cfg.get("dimensions", 21),
                "--curvature=%s" % model_cfg.get("curvature", -1.0),
                "--epochs=%s" % training_cfg.get("epochs", 50),
                "--batch-size=%s" % training_cfg.get("batch_size", 64),
                "--learning-rate=%s" % training_cfg.get("learning_rate", 0.001),
                "--hf-repo=%s" % cfg["hf_model_repo"],
                "--kernel-manifest-sha=%s" % kernel_summary["kernel_manifest_sha"],
                "--kernel-file-count=%s" % kernel_summary["kernel_file_count"],
            ],
        },
    }]

    if dry_run:
        log.info("[DRY RUN] Would create job: %s", job_name)
        log.info("[DRY RUN] Worker pool config:")
        log.info(json.dumps(worker_pool, indent=2))
        log.info("[DRY RUN] Pipeline config loaded successfully")
        log.info("[DRY RUN] All systems nominal - ready for real training")
        return None

    aiplatform.init(
        project=cfg["project_id"],
        location=cfg["region"],
        staging_bucket=cfg["staging_bucket"],
    )

    log.info("Creating Vertex AI training job: %s", job_name)
    job = aiplatform.CustomJob(
        display_name=job_name,
        worker_pool_specs=worker_pool,
        labels={
            "model": "phdm-21d",
            "framework": "scbe-aethermoore",
            "type": "embedding",
            "kernel_manifest_sha": kernel_summary["kernel_manifest_sha"][:32],
        },
    )

    log.info("Submitting training job to Vertex AI...")
    job.run(sync=False)
    log.info("Job submitted: %s", job.resource_name)
    return job


def push_to_huggingface(cfg):
    """Push trained model artifacts to HuggingFace Hub."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        log.warning("huggingface_hub not installed - skipping HF push")
        return

    api = HfApi(token=os.environ.get("HF_TOKEN"))
    output_dir = Path("./output/phdm-21d")

    if not output_dir.exists():
        log.warning("No output directory found at %s - skipping push", output_dir)
        return

    log.info("Pushing model to HuggingFace: %s", cfg["hf_model_repo"])
    api.upload_folder(
        folder_path=str(output_dir),
        repo_id=cfg["hf_model_repo"],
        repo_type="model",
        commit_message="training: upload PHDM 21D weights %s" % datetime.utcnow().isoformat(),
    )
    log.info("Model pushed to HuggingFace successfully")


def main():
    parser = argparse.ArgumentParser(description="Trigger PHDM 21D Vertex AI training")
    parser.add_argument("--dry-run", action="store_true", help="Print job config without submitting")
    parser.add_argument("--config", type=str, default=None, help="Path to pipeline config YAML")
    parser.add_argument("--push-only", action="store_true", help="Skip training, push existing output to HF")
    args = parser.parse_args()

    cfg = DEFAULTS.copy()
    pipeline = load_pipeline_config(args.config)
    kernel_summary = load_kernel_summary()

    log.info("PHDM 21D Embedding Training Trigger")
    log.info("Project: %s | Region: %s", cfg["project_id"], cfg["region"])
    log.info("HF Model: %s", cfg["hf_model_repo"])
    log.info("GKE Cluster: %s", cfg["gke_cluster"])
    log.info("Kernel files: %s | Manifest SHA: %s", kernel_summary["kernel_file_count"], kernel_summary["kernel_manifest_sha"])

    if args.push_only:
        push_to_huggingface(cfg)
        return

    validate_environment(dry_run=args.dry_run)
    job = create_training_job(cfg, pipeline, kernel_summary, dry_run=args.dry_run)

    if job and not args.dry_run:
        log.info("Training job is running. Monitor at:")
        log.info("  https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=%s", cfg["project_id"])


if __name__ == "__main__":
    main()
