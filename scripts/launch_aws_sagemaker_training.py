#!/usr/bin/env python3
"""Render and optionally submit a SageMaker training job definition."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render SageMaker job from template")
    parser.add_argument("--template", default="training/aws_sagemaker_long_run_training_job.json")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--run-root", default="training/runs")
    parser.add_argument("--region", default=None, help="AWS Region override")
    parser.add_argument("--submit", action="store_true", help="Submit job via AWS CLI")
    return parser.parse_args()


def load_template(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_node(node, context):
    if isinstance(node, str):
        try:
            return node.format(**context)
        except KeyError as exc:
            raise ValueError(f"Missing template context key: {exc.args[0]}")
    if isinstance(node, dict):
        return {key: render_node(value, context) for key, value in node.items()}
    if isinstance(node, list):
        return [render_node(item, context) for item in node]
    return node


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json_payload(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def submit_to_aws(payload_path: Path, region: str) -> int:
    command = [
        "aws",
        "sagemaker",
        "create-training-job",
        "--cli-input-json",
        f"file://{payload_path}",
        "--region",
        region,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
    return result.returncode


def main() -> int:
    args = parse_args()
    template_path = Path(args.template)
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    output_root = Path(args.run_root).expanduser().resolve()
    ensure_output_dir(output_root)

    region = args.region or os.environ.get("AWS_REGION")
    if not region:
        raise ValueError("AWS_REGION is required (argument --region or environment variable)")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    job_name = f"scbe-longrun-{timestamp}"
    context = {
        "AWS_REGION": region,
        "SAGEMAKER_JOB_NAME": job_name,
        "SAGEMAKER_EXECUTION_ROLE_ARN": os.environ.get("SAGEMAKER_EXECUTION_ROLE_ARN", ""),
        "S3_TRAINING_DATA_URI": os.environ.get("S3_TRAINING_DATA_URI", ""),
        "S3_OUTPUT_PATH": os.environ.get("S3_OUTPUT_PATH", ""),
        "SAGEMAKER_MAX_RUNTIME_SECONDS": str(int(float(args.hours) * 3600)),
        "TRAINING_HOURS": str(float(args.hours)),
    }

    required = ["SAGEMAKER_EXECUTION_ROLE_ARN", "S3_TRAINING_DATA_URI", "S3_OUTPUT_PATH"]
    missing = [name for name in required if not context[name]]
    if missing:
        raise ValueError(f"Missing required environment values: {', '.join(missing)}")

    template = load_template(template_path)
    rendered = render_node(deepcopy(template), context)
    output_path = output_root / f"sagemaker_job_{job_name}.json"
    write_json_payload(output_path, rendered)

    print("Rendered SageMaker job spec:", output_path)
    if args.submit:
        print("Submitting SageMaker job to AWS...")
        return submit_to_aws(output_path, region)

    print("Dry-run mode (default): rendered spec written, job not submitted.")
    print("Run with --submit to send create-training-job.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
