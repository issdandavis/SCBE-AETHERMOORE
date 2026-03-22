#!/usr/bin/env python3
"""Tune SCBE internet workflow variables from baseline run summary."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Metrics:
    allowed_records: int
    quarantined_records: int
    total_records: int
    quarantine_ratio: float
    audit_status: str
    core_health_passed: bool


DEFAULT_THRESHOLDS: dict[str, float] = {
    "truth_min": 0.62,
    "useful_min": 0.58,
    "harmful_max": 0.25,
    "dataset_anomaly_threshold": 0.78,
    "dataset_max_flagged_ratio": 0.08,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune cloud kernel thresholds and runtime profile")
    parser.add_argument("--summary", required=True, help="Path to baseline summary.json")
    parser.add_argument("--config", required=True, help="Path to cloud kernel config JSON")
    parser.add_argument("--output-config", required=True, help="Path for tuned cloud kernel config")
    parser.add_argument(
        "--target-quarantine-ratio",
        type=float,
        default=0.08,
        help="Target quarantine ratio used by policy bands",
    )
    parser.add_argument("--runtime-profile", default="", help="Optional runtime profile to tune")
    parser.add_argument(
        "--output-runtime-profile",
        default="",
        help="Optional output path for tuned runtime profile",
    )
    parser.add_argument("--output-report", required=True, help="Path for tuning report JSON")
    return parser.parse_args()


def read_metrics(summary: dict[str, Any]) -> Metrics:
    allowed = int(summary.get("allowed_records", 0) or 0)
    quarantined = int(summary.get("quarantined_records", 0) or 0)
    total = allowed + quarantined
    ratio = (quarantined / float(total)) if total > 0 else 1.0
    return Metrics(
        allowed_records=allowed,
        quarantined_records=quarantined,
        total_records=total,
        quarantine_ratio=ratio,
        audit_status=str(summary.get("audit_status", "QUARANTINE")).upper(),
        core_health_passed=bool(summary.get("core_health_passed", False)),
    )


def policy_band(metrics: Metrics, target_ratio: float) -> str:
    if (not metrics.core_health_passed) or metrics.audit_status != "ALLOW":
        return "hard-tighten"
    if metrics.quarantine_ratio > (target_ratio * 1.5):
        return "hard-tighten"
    if metrics.quarantine_ratio > target_ratio:
        return "tighten"
    if metrics.quarantine_ratio < (target_ratio * 0.5):
        return "relax"
    return "steady"


def tune_thresholds(thresholds: dict[str, Any], band: str) -> tuple[dict[str, float], dict[str, float]]:
    current = {
        key: float(thresholds.get(key, default))
        for key, default in DEFAULT_THRESHOLDS.items()
    }
    tuned = dict(current)

    if band == "hard-tighten":
        tuned["truth_min"] = clamp(tuned["truth_min"] + 0.03, 0.55, 0.90)
        tuned["useful_min"] = clamp(tuned["useful_min"] + 0.03, 0.50, 0.88)
        tuned["harmful_max"] = clamp(tuned["harmful_max"] - 0.03, 0.08, 0.35)
        tuned["dataset_anomaly_threshold"] = clamp(
            tuned["dataset_anomaly_threshold"] - 0.03, 0.60, 0.90
        )
        tuned["dataset_max_flagged_ratio"] = clamp(
            tuned["dataset_max_flagged_ratio"] - 0.015, 0.03, 0.15
        )
    elif band == "tighten":
        tuned["truth_min"] = clamp(tuned["truth_min"] + 0.02, 0.55, 0.90)
        tuned["useful_min"] = clamp(tuned["useful_min"] + 0.02, 0.50, 0.88)
        tuned["harmful_max"] = clamp(tuned["harmful_max"] - 0.02, 0.08, 0.35)
        tuned["dataset_anomaly_threshold"] = clamp(
            tuned["dataset_anomaly_threshold"] - 0.02, 0.60, 0.90
        )
    elif band == "relax":
        tuned["truth_min"] = clamp(tuned["truth_min"] - 0.01, 0.55, 0.90)
        tuned["useful_min"] = clamp(tuned["useful_min"] - 0.01, 0.50, 0.88)
        tuned["harmful_max"] = clamp(tuned["harmful_max"] + 0.01, 0.08, 0.35)
        tuned["dataset_anomaly_threshold"] = clamp(
            tuned["dataset_anomaly_threshold"] + 0.01, 0.60, 0.90
        )

    for key, value in tuned.items():
        tuned[key] = round(value, 6)
    return current, tuned


def tune_runtime(profile: dict[str, Any], band: str, core_health_passed: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    web = profile.get("web_research", {})
    if not isinstance(web, dict):
        web = {}
    before = {
        "max_tabs": int(web.get("max_tabs", 6) or 6),
        "max_per_topic": int(web.get("max_per_topic", 6) or 6),
        "skip_core_check": bool(web.get("skip_core_check", False)),
    }
    after = dict(before)

    if band == "hard-tighten":
        after["max_tabs"] = max(2, after["max_tabs"] - 2)
        after["max_per_topic"] = max(3, after["max_per_topic"] - 1)
    elif band == "tighten":
        after["max_tabs"] = max(2, after["max_tabs"] - 1)
    elif band == "relax":
        after["max_tabs"] = min(12, after["max_tabs"] + 1)
        after["max_per_topic"] = min(12, after["max_per_topic"] + 1)

    if not core_health_passed:
        after["skip_core_check"] = False

    profile["web_research"] = {
        **web,
        "max_tabs": after["max_tabs"],
        "max_per_topic": after["max_per_topic"],
        "skip_core_check": after["skip_core_check"],
    }
    return before, after


def main() -> int:
    args = parse_args()

    summary_path = Path(args.summary).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()
    output_config_path = Path(args.output_config).expanduser().resolve()
    output_report_path = Path(args.output_report).expanduser().resolve()

    summary = read_json(summary_path)
    metrics = read_metrics(summary)
    band = policy_band(metrics, target_ratio=float(args.target_quarantine_ratio))

    config = read_json(config_path)
    thresholds = config.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    before_thresholds, tuned_thresholds = tune_thresholds(thresholds, band)
    config["thresholds"] = tuned_thresholds
    write_json(output_config_path, config)

    runtime_before: dict[str, Any] = {}
    runtime_after: dict[str, Any] = {}
    runtime_output_path = ""
    if args.runtime_profile:
        runtime_profile_path = Path(args.runtime_profile).expanduser().resolve()
        profile = read_json(runtime_profile_path)
        runtime_before, runtime_after = tune_runtime(profile, band, metrics.core_health_passed)

        if args.output_runtime_profile:
            runtime_out = Path(args.output_runtime_profile).expanduser().resolve()
        else:
            runtime_out = runtime_profile_path.with_name(
                runtime_profile_path.stem + ".tuned" + runtime_profile_path.suffix
            )
        write_json(runtime_out, profile)
        runtime_output_path = str(runtime_out)

    report = {
        "generated_at_utc": utc_now(),
        "summary_path": str(summary_path),
        "target_quarantine_ratio": float(args.target_quarantine_ratio),
        "policy_band": band,
        "metrics": {
            "allowed_records": metrics.allowed_records,
            "quarantined_records": metrics.quarantined_records,
            "total_records": metrics.total_records,
            "quarantine_ratio": round(metrics.quarantine_ratio, 6),
            "audit_status": metrics.audit_status,
            "core_health_passed": metrics.core_health_passed,
        },
        "thresholds_before": before_thresholds,
        "thresholds_after": tuned_thresholds,
        "runtime_before": runtime_before,
        "runtime_after": runtime_after,
        "output_config": str(output_config_path),
        "output_runtime_profile": runtime_output_path,
    }
    write_json(output_report_path, report)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
