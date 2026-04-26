#!/usr/bin/env python3
"""Evaluate the SCBE operator-agent-bus lane.

This harness checks two things:
1. The held-out operator-agent-bus records preserve required route/proof/risk fields.
2. The user-facing `agentbus run` endpoint creates the expected observable artifacts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_PATH = REPO_ROOT / "training-data" / "sft" / "operator_agent_bus_extracted_v1_eval.sft.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "operator_agent_bus_eval"
CLI = REPO_ROOT / "scripts" / "scbe-system-cli.py"


@dataclass(frozen=True)
class EndpointTask:
    task_id: str
    task_type: str
    prompt: str
    operation_command: str = "korah aelin dahru"


ENDPOINT_TASKS = (
    EndpointTask(
        task_id="coding_route",
        task_type="coding",
        prompt="User asks the agent bus to route a scoped coding fix with local-only privacy.",
    ),
    EndpointTask(
        task_id="training_route",
        task_type="training",
        prompt="User asks the agent bus to route a training consolidation task into the correct lane.",
    ),
    EndpointTask(
        task_id="governance_route",
        task_type="governance",
        prompt="User asks the agent bus to keep security boundaries separate from AI operation routing.",
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _assistant_json(row: dict[str, Any]) -> dict[str, Any]:
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    assistant = next(
        (item for item in reversed(messages) if isinstance(item, dict) and item.get("role") == "assistant"),
        {},
    )
    raw = str(assistant.get("content", "")).strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("assistant content must decode to a JSON object")
    return parsed


def _record_required_fields(row: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    tags = set((row.get("metadata") or {}).get("tags") or [])
    if "cross_talk" in tags:
        return ["intent", "next_action", "risk", "status", "ledger", "proof", "layer14"]
    if "workflow_eval" in tags:
        return ["status", "source_type"]
    if "route_gate" in tags:
        return ["decision", "commitment_status", "proof_status", "route_confidence"]
    if "agent_bus" in tags:
        return ["status"]
    return sorted(str(key) for key in payload.keys())[:1]


def score_eval_record(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    try:
        payload = _assistant_json(row)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "ok": False,
            "score": 0.0,
            "record_id": metadata.get("dedupe_key", ""),
            "source_path": metadata.get("source_path", ""),
            "error": f"invalid_assistant_json: {exc}",
            "checks": {"json_parse": False},
        }

    required = _record_required_fields(row, payload)
    checks: dict[str, bool] = {"json_parse": True}
    for field in required:
        checks[f"has_{field}"] = field in payload
    checks["no_execution_command"] = not any(
        key in payload for key in ("shell_command", "powershell", "bash", "cmd")
    )
    checks["has_source_metadata"] = bool(metadata.get("source_path") and metadata.get("dedupe_key"))
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return {
        "ok": passed == total,
        "score": round(passed / total, 4),
        "record_id": metadata.get("dedupe_key", ""),
        "source_path": metadata.get("source_path", ""),
        "required_fields": required,
        "checks": checks,
    }


def evaluate_dataset(eval_path: Path = DEFAULT_EVAL_PATH) -> dict[str, Any]:
    rows = _load_jsonl(eval_path)
    record_scores = [score_eval_record(row) for row in rows]
    average = (
        round(sum(item["score"] for item in record_scores) / len(record_scores), 4)
        if record_scores
        else 0.0
    )
    return {
        "eval_path": str(eval_path),
        "record_count": len(rows),
        "average_score": average,
        "passed_records": sum(1 for item in record_scores if item["ok"]),
        "record_scores": record_scores,
    }


def _path_exists(relative: str | None) -> bool:
    if not relative:
        return False
    return (REPO_ROOT / relative).exists()


def run_endpoint_task(task: EndpointTask, run_id: str) -> dict[str, Any]:
    series_id = f"operator-eval-{run_id}-{task.task_id}"
    command = [
        sys.executable,
        str(CLI),
        "--repo-root",
        str(REPO_ROOT),
        "agentbus",
        "run",
        "--task",
        task.prompt,
        "--operation-command",
        task.operation_command,
        "--task-type",
        task.task_type,
        "--series-id",
        series_id,
        "--privacy",
        "local_only",
        "--budget-cents",
        "0",
        "--dispatch",
        "--json",
    ]
    start = time.perf_counter()
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False, timeout=60)
    duration_ms = int((time.perf_counter() - start) * 1000)
    payload: dict[str, Any] = {}
    error = ""
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError as exc:
            error = f"json_decode_error: {exc}"
    if proc.returncode != 0 and not error:
        error = proc.stderr[-1000:]
    return {
        "task": asdict(task),
        "returncode": proc.returncode,
        "duration_ms": duration_ms,
        "stdout_chars": len(proc.stdout),
        "stderr_chars": len(proc.stderr),
        "payload": payload,
        "error": error,
    }


def score_endpoint_result(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    dispatch = payload.get("dispatch") if isinstance(payload.get("dispatch"), dict) else {}
    operation = payload.get("operation_shape") if isinstance(payload.get("operation_shape"), dict) else {}
    checks = {
        "returncode_zero": result.get("returncode") == 0,
        "schema": payload.get("schema_version") == "scbe_agentbus_user_run_v1",
        "selected_provider": payload.get("selected_provider") in {"offline", "ollama"},
        "local_only": payload.get("privacy") == "local_only",
        "zero_budget": float(payload.get("budget_cents", 1.0)) == 0.0,
        "dispatch_event": dispatch.get("enabled") is True and bool(dispatch.get("event_id")),
        "operation_shape": operation.get("root_value") == 12026 and bool(operation.get("signature_hex")),
        "no_float_consensus": operation.get("floating_point_policy") == "forbidden for consensus signatures",
        "mirror_artifact": _path_exists(artifacts.get("latest_round")),
        "watcher_artifact": _path_exists(artifacts.get("watcher")),
        "summary_artifact": _path_exists(artifacts.get("summary")),
        "raw_prompt_not_echoed": str((result.get("task") or {}).get("prompt", "")) not in json.dumps(payload),
    }
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    return {
        "task_id": (result.get("task") or {}).get("task_id", ""),
        "score": round(passed / total, 4),
        "ok": passed == total,
        "checks": checks,
        "duration_ms": result.get("duration_ms", 0),
        "error": result.get("error", ""),
    }


def evaluate_endpoint(run_id: str, *, run_live: bool = True) -> dict[str, Any]:
    if not run_live:
        return {"run_live": False, "task_count": 0, "average_score": 0.0, "task_scores": []}
    raw_results = [run_endpoint_task(task, run_id) for task in ENDPOINT_TASKS]
    task_scores = [score_endpoint_result(result) for result in raw_results]
    average = (
        round(sum(item["score"] for item in task_scores) / len(task_scores), 4)
        if task_scores
        else 0.0
    )
    return {
        "run_live": True,
        "task_count": len(ENDPOINT_TASKS),
        "average_score": average,
        "passed_tasks": sum(1 for item in task_scores if item["ok"]),
        "task_scores": task_scores,
        "raw_results": raw_results,
    }


def build_report(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    eval_path: Path = DEFAULT_EVAL_PATH,
    run_id: str | None = None,
    run_live_endpoint: bool = True,
) -> dict[str, Any]:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dataset = evaluate_dataset(eval_path)
    endpoint = evaluate_endpoint(run_id, run_live=run_live_endpoint)
    dataset_weight = 0.55
    endpoint_weight = 0.45 if run_live_endpoint else 0.0
    denominator = dataset_weight + endpoint_weight
    overall = round(
        (
            dataset["average_score"] * dataset_weight
            + endpoint["average_score"] * endpoint_weight
        )
        / denominator,
        4,
    )
    decision = "PASS" if dataset["average_score"] >= 0.9 and (not run_live_endpoint or endpoint["average_score"] >= 0.9) else "HOLD"
    report = {
        "schema_version": "scbe_operator_agent_bus_eval_v1",
        "purpose": "operator_agent_bus",
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "decision": decision,
        "score": overall,
        "dataset_score": dataset["average_score"],
        "endpoint_score": endpoint["average_score"],
        "dataset": dataset,
        "endpoint": endpoint,
        "promotion_gate": "PASS only when held-out records preserve route/proof/risk fields and endpoint artifacts exist.",
    }
    run_dir = output_dir / run_id
    _write_json(run_dir / "report.json", report)
    _write_json(output_dir / "latest_report.json", report)
    (run_dir / "REPORT.md").write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "LATEST.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCBE Operator Agent Bus Eval",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Run ID: `{report['run_id']}`",
        f"- Decision: `{report['decision']}`",
        f"- Overall score: `{report['score']}`",
        f"- Dataset score: `{report['dataset_score']}`",
        f"- Endpoint score: `{report['endpoint_score']}`",
        "",
        "## Gate",
        "",
        report["promotion_gate"],
        "",
        "## Dataset Records",
        "",
        f"- Records: `{report['dataset']['record_count']}`",
        f"- Passed: `{report['dataset']['passed_records']}`",
        "",
        "## Endpoint Tasks",
        "",
        f"- Run live endpoint: `{report['endpoint']['run_live']}`",
        f"- Tasks: `{report['endpoint']['task_count']}`",
        f"- Passed: `{report['endpoint'].get('passed_tasks', 0)}`",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-path", type=Path, default=DEFAULT_EVAL_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--skip-live-endpoint", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(
        output_dir=args.out_dir,
        eval_path=args.eval_path,
        run_id=args.run_id or None,
        run_live_endpoint=not args.skip_live_endpoint,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(
            "operator agent bus eval: "
            f"decision={report['decision']} score={report['score']} "
            f"dataset={report['dataset_score']} endpoint={report['endpoint_score']}"
        )
        print(f"report={args.out_dir / report['run_id'] / 'report.json'}")
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
