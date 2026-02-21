#!/usr/bin/env python3
"""Federated multi-cloud artifact orchestrator.

This script turns HF/GCP/AWS training outputs into one fused release manifest.
It performs simple promotion gates so the process is operational, not doc-only.

Input manifest schema (per provider JSON):
{
  "provider": "hf" | "gcp" | "aws",
  "artifacts": [
    {
      "id": "spiralverse/textgen-lora-v1",
      "role": "textgen" | "embed" | "runtime",
      "metrics": {
        "quality": 0.81,
        "safety": 0.98,
        "latency_ms_p95": 120,
        "cost_per_1k_tokens": 0.7
      },
      "uri": "hf://issdandavis/spiralverse-ai-federated-v1"
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_PROVIDERS = {"hf", "gcp", "aws"}
EXPECTED_ROLE_BY_PROVIDER = {
    "hf": "textgen",
    "gcp": "embed",
    "aws": "runtime",
}


@dataclass(frozen=True)
class Gates:
    min_quality: float
    min_safety: float
    max_latency_ms_p95: float
    max_cost_per_1k_tokens: float


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Manifest at {path} must be an object")

    provider = data.get("provider")
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Manifest at {path} has invalid provider: {provider}")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(f"Manifest at {path} must have non-empty 'artifacts' list")

    return data


def metric(artifact: dict[str, Any], key: str) -> float:
    metrics = artifact.get("metrics", {})
    value = metrics.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Artifact {artifact.get('id')} missing numeric metric '{key}'")
    return float(value)


def passes_gates(artifact: dict[str, Any], gates: Gates) -> bool:
    return (
        metric(artifact, "quality") >= gates.min_quality
        and metric(artifact, "safety") >= gates.min_safety
        and metric(artifact, "latency_ms_p95") <= gates.max_latency_ms_p95
        and metric(artifact, "cost_per_1k_tokens") <= gates.max_cost_per_1k_tokens
    )


def artifact_score(artifact: dict[str, Any]) -> float:
    # Higher quality/safety is better; lower latency/cost is better.
    q = metric(artifact, "quality")
    s = metric(artifact, "safety")
    l = metric(artifact, "latency_ms_p95")
    c = metric(artifact, "cost_per_1k_tokens")
    return (q * 0.45) + (s * 0.45) - (l * 0.0005) - (c * 0.1)


def select_provider_artifact(provider_manifest: dict[str, Any], gates: Gates) -> dict[str, Any]:
    provider = provider_manifest["provider"]
    expected_role = EXPECTED_ROLE_BY_PROVIDER[provider]

    candidates = [
        a for a in provider_manifest["artifacts"] if isinstance(a, dict) and a.get("role") == expected_role
    ]
    if not candidates:
        raise ValueError(f"No artifacts with expected role '{expected_role}' for provider '{provider}'")

    promoted = [a for a in candidates if passes_gates(a, gates)]
    if not promoted:
        raise ValueError(f"Provider '{provider}' has no artifacts passing promotion gates")

    return max(promoted, key=artifact_score)


def build_fused_manifest(selected: dict[str, dict[str, Any]], gates: Gates) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    release_units = {
        provider: {
            "id": artifact["id"],
            "role": artifact["role"],
            "uri": artifact.get("uri"),
            "metrics": artifact["metrics"],
        }
        for provider, artifact in selected.items()
    }

    fused_version = datetime.now(timezone.utc).strftime("v%Y.%m.%d.%H%M")
    return {
        "fused_model_id": f"spiralverse-ai-federated-{fused_version}",
        "generated_at": now,
        "providers": sorted(list(selected.keys())),
        "gates": {
            "min_quality": gates.min_quality,
            "min_safety": gates.min_safety,
            "max_latency_ms_p95": gates.max_latency_ms_p95,
            "max_cost_per_1k_tokens": gates.max_cost_per_1k_tokens,
        },
        "units": release_units,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fuse HF/GCP/AWS training manifests into one promoted manifest")
    parser.add_argument("--hf-manifest", required=True, type=Path)
    parser.add_argument("--gcp-manifest", required=True, type=Path)
    parser.add_argument("--aws-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-quality", type=float, default=0.75)
    parser.add_argument("--min-safety", type=float, default=0.95)
    parser.add_argument("--max-latency-ms-p95", type=float, default=250.0)
    parser.add_argument("--max-cost-per-1k-tokens", type=float, default=1.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gates = Gates(
        min_quality=args.min_quality,
        min_safety=args.min_safety,
        max_latency_ms_p95=args.max_latency_ms_p95,
        max_cost_per_1k_tokens=args.max_cost_per_1k_tokens,
    )

    manifests = [
        load_manifest(args.hf_manifest),
        load_manifest(args.gcp_manifest),
        load_manifest(args.aws_manifest),
    ]

    by_provider = {m["provider"]: m for m in manifests}
    missing = SUPPORTED_PROVIDERS.difference(by_provider)
    if missing:
        raise ValueError(f"Missing provider manifests: {', '.join(sorted(missing))}")

    selected = {
        provider: select_provider_artifact(provider_manifest, gates)
        for provider, provider_manifest in by_provider.items()
    }

    fused = build_fused_manifest(selected, gates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(fused, fh, indent=2)

    print(f"Wrote fused manifest to {args.output}")
    print(f"Fused model id: {fused['fused_model_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
