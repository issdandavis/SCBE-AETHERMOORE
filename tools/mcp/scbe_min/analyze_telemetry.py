#!/usr/bin/env python3
"""Analyze SCBE MIN telemetry into HF-ready dataset rows and next-step actions."""

from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _load_events(source: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not source.exists():
        return events

    for line_no, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            obj["_line_no"] = line_no
            events.append(obj)
    return events


def _get_click_offsets(event: Dict[str, Any]) -> List[float]:
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    offsets: List[float] = []

    telemetry_summary = payload.get("telemetry_summary")
    if isinstance(telemetry_summary, dict):
        click_metrics = telemetry_summary.get("click_metrics")
        if isinstance(click_metrics, dict):
            p95 = click_metrics.get("p95_offset_px")
            if isinstance(p95, (int, float)) and p95 >= 0:
                offsets.append(float(p95))

    preview = payload.get("action_diagnostics_preview")
    if isinstance(preview, list):
        for row in preview:
            if not isinstance(row, dict):
                continue
            if str(row.get("action", "")).lower() != "click":
                continue
            intended = row.get("intended")
            actual = row.get("actual")
            if not isinstance(intended, dict) or not isinstance(actual, dict):
                continue
            x0 = intended.get("x")
            y0 = intended.get("y")
            x1 = actual.get("x")
            y1 = actual.get("y")
            if all(isinstance(v, (int, float)) for v in [x0, y0, x1, y1]):
                dx = float(x1) - float(x0)
                dy = float(y1) - float(y0)
                offsets.append(round(math.sqrt(dx * dx + dy * dy), 4))

    return offsets


def _get_precision_markers(event: Dict[str, Any]) -> List[int]:
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    markers: List[int] = []
    preview = payload.get("action_diagnostics_preview")
    if not isinstance(preview, list):
        return markers

    keys = ["precision_digits", "rounded_decimals", "serialization_decimals", "numeric_precision_digits"]
    for row in preview:
        if not isinstance(row, dict):
            continue
        for key in keys:
            value = row.get(key)
            if isinstance(value, int):
                markers.append(value)
    return markers


def _build_row(event: Dict[str, Any], run_index: int, dataset_name: str) -> Dict[str, Any]:
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    decision_record = event.get("decision_record", {}) if isinstance(event.get("decision_record"), dict) else {}
    state_vector = event.get("state_vector", {}) if isinstance(event.get("state_vector"), dict) else {}

    job_id = str(decision_record.get("job_id", "none"))
    event_type = str(event.get("event_type", "unknown"))
    created_at_utc = str(event.get("created_at_utc", "")).strip() or _now_iso()
    decision = str(decision_record.get("decision", "DENY"))
    risk = float(decision_record.get("metrics", {}).get("risk", 1.0)) if isinstance(decision_record.get("metrics"), dict) else 1.0

    click_offsets = _get_click_offsets(event)
    p95 = max(click_offsets) if click_offsets else None
    precision_markers = _get_precision_markers(event)

    return {
        "dataset": dataset_name,
        "run_id": job_id,
        "run_index": run_index,
        "created_at_utc": created_at_utc,
        "event_type": event_type,
        "decision": decision,
        "risk": round(risk, 4),
        "target_ref": event.get("target_ref"),
        "tool": event_type,
        "lane": state_vector.get("lane"),
        "objective": state_vector.get("objective"),
        "click_offset_p95_px": p95,
        "click_offset_samples": len(click_offsets),
        "precision_markers": precision_markers,
        "trace_hash": decision_record.get("trace_hash"),
    }


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

def _analysis(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    decision_counts = {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0}
    offsets: List[float] = []
    precision_values: List[int] = []

    for row in rows:
        decision = str(row.get("decision", "DENY")).upper()
        if decision in decision_counts:
            decision_counts[decision] += 1

        val = row.get("click_offset_p95_px")
        if isinstance(val, (int, float)):
            offsets.append(float(val))

        marks = row.get("precision_markers")
        if isinstance(marks, list):
            for m in marks:
                if isinstance(m, int):
                    precision_values.append(m)

    total = len(rows)
    deny_ratio = round((decision_counts["DENY"] / total), 4) if total else 0.0
    quarantine_ratio = round((decision_counts["QUARANTINE"] / total), 4) if total else 0.0

    p95_offset = None
    max_offset = None
    if offsets:
        ordered = sorted(offsets)
        p95_index = int(round((len(ordered) - 1) * 0.95))
        p95_offset = round(ordered[p95_index], 4)
        max_offset = round(max(ordered), 4)

    rounded_decimal_risk = {
        "observed": len(precision_values) > 0,
        "min_precision_digits": min(precision_values) if precision_values else None,
        "sample_count": len(precision_values),
    }

    recommendations: List[Dict[str, Any]] = []

    if p95_offset is None:
        recommendations.append(
            {
                "priority": "P1",
                "issue": "Missing click drift observability",
                "action": "Log intended/actual click points in action diagnostics for each click step",
                "metric": "click_offset_p95_px coverage",
            }
        )
    elif p95_offset > 16.0:
        recommendations.append(
            {
                "priority": "P1",
                "issue": "High click drift",
                "action": "Enable pre-click recenter, viewport stabilization, and selector confidence gating",
                "metric": f"click_offset_p95_px={p95_offset}",
            }
        )

    if deny_ratio > 0.15:
        recommendations.append(
            {
                "priority": "P1",
                "issue": "High deny ratio",
                "action": "Tighten target preflight and add domain-specific mission policies",
                "metric": f"deny_ratio={deny_ratio}",
            }
        )

    if quarantine_ratio > 0.25:
        recommendations.append(
            {
                "priority": "P2",
                "issue": "Frequent quarantine decisions",
                "action": "Train policy on quarantined traces to reduce ambiguous behavior",
                "metric": f"quarantine_ratio={quarantine_ratio}",
            }
        )

    if not rounded_decimal_risk["observed"]:
        recommendations.append(
            {
                "priority": "P1",
                "issue": "Rounded-decimal gap not instrumented",
                "action": "Record serialization precision fields (precision_digits/rounded_decimals) in telemetry",
                "metric": "rounded_decimal_samples=0",
            }
        )
    elif isinstance(rounded_decimal_risk["min_precision_digits"], int) and rounded_decimal_risk["min_precision_digits"] <= 3:
        recommendations.append(
            {
                "priority": "P1",
                "issue": "Low precision serialization observed",
                "action": "Run targeted rounded-decimal adversarial test suite using real production traces",
                "metric": f"min_precision_digits={rounded_decimal_risk['min_precision_digits']}",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "priority": "P3",
                "issue": "No critical drift signals",
                "action": "Continue telemetry collection and retrain at next mission milestone",
                "metric": "steady-state",
            }
        )

    return {
        "generated_at_utc": _now_iso(),
        "rows": total,
        "decision_counts": decision_counts,
        "deny_ratio": deny_ratio,
        "quarantine_ratio": quarantine_ratio,
        "click_offset_p95_px": p95_offset,
        "click_offset_max_px": max_offset,
        "rounded_decimal_risk": rounded_decimal_risk,
        "next_steps": recommendations,
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _upload_hf(repo: str, files: List[Path], token_env: str) -> None:
    token = os.environ.get(token_env) or os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError(f"Missing token env: {token_env} (or HUGGINGFACE_TOKEN/HF_TOKEN)")

    try:
        from huggingface_hub import HfApi
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"huggingface_hub unavailable: {exc}") from exc

    api = HfApi(token=token)
    for path in files:
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=f"data/{path.name}",
            repo_id=repo,
            repo_type="dataset",
            commit_message=f"Update SCBE telemetry artifact: {path.name}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze SCBE MIN telemetry and generate next-step actions")
    parser.add_argument(
        "--source",
        default=str(Path("artifacts") / "scbe_min" / "telemetry" / "events.jsonl"),
        help="Input telemetry JSONL",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path("training-data") / "scbe-min"),
        help="Output directory",
    )
    parser.add_argument("--dataset", default="scbe_min_browser_telemetry", help="Dataset name field")
    parser.add_argument("--upload-hf", action="store_true", help="Upload outputs to HF dataset repo")
    parser.add_argument("--hf-repo", default=None, help="HF dataset repo owner/name")
    parser.add_argument("--hf-token-env", default="HUGGINGFACE_TOKEN", help="Token environment variable")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    events = _load_events(source)
    rows = [_build_row(event, idx, args.dataset) for idx, event in enumerate(events)]

    out_data = out_dir / f"{args.dataset}.jsonl"
    out_analysis = out_dir / f"{args.dataset}.analysis.json"
    _write_jsonl(out_data, rows)

    analysis = _analysis(rows)
    analysis["source"] = str(source)
    analysis["output_dataset"] = str(out_data)
    _write_json(out_analysis, analysis)

    if args.upload_hf:
        if not args.hf_repo:
            raise ValueError("--hf-repo is required when --upload-hf is set")
        _upload_hf(args.hf_repo, [out_data, out_analysis], args.hf_token_env)

    print(
        json.dumps(
            {
                "source": str(source),
                "events": len(events),
                "dataset_file": str(out_data),
                "analysis_file": str(out_analysis),
                "deny_ratio": analysis["deny_ratio"],
                "click_offset_p95_px": analysis["click_offset_p95_px"],
                "rounded_decimal_observed": analysis["rounded_decimal_risk"]["observed"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
