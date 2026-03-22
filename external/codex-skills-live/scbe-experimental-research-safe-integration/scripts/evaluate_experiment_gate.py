from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_metrics(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def decide(metrics: dict) -> dict:
    # Defaults mirror references/safe-integration-gates.yaml.
    checks = {
        "regression_rate": float(metrics.get("regression_rate", 1.0)) <= 0.02,
        "reproducibility": float(metrics.get("reproducibility", 0.0)) >= 0.98,
        "redteam_pass_rate": float(metrics.get("redteam_pass_rate", 0.0)) >= 0.95,
        "safety_incidents": int(metrics.get("safety_incidents", 999)) <= 0,
        "p95_latency_delta_ms": float(metrics.get("p95_latency_delta_ms", 1e9)) <= 40.0,
        "error_rate_delta": float(metrics.get("error_rate_delta", 1.0)) <= 0.01,
        "trust_score": float(metrics.get("trust_score", 0.0)) >= 0.85,
        "model_norm_lt_1": float(metrics.get("model_norm", 2.0)) < 1.0,
        "no_negative_space_crossing": bool(metrics.get("negative_space_crossed", True)) is False,
        "harmonic_energy_within_budget": float(metrics.get("harmonic_energy", 1e9)) <= float(metrics.get("harmonic_energy_budget", 1000.0)),
        "rollback_ready": bool(metrics.get("rollback_ready", False)) is True,
    }

    failed = [k for k, v in checks.items() if not v]
    if failed:
        action = "QUARANTINE"
        if any(k in failed for k in ("safety_incidents", "no_negative_space_crossing", "model_norm_lt_1")):
            action = "DENY"
    else:
        action = "ALLOW"

    return {
        "action": action,
        "failed_checks": failed,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate experimental integration safety gates.")
    parser.add_argument("--metrics", required=True, help="Path to metrics JSON file")
    args = parser.parse_args()

    metrics = load_metrics(Path(args.metrics))
    result = decide(metrics)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
