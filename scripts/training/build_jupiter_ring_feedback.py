#!/usr/bin/env python3
"""Build a Jupiter-ring feedback corpus from completed eval artifacts.

The ring is outside the main training orbit: it keeps prompts, model outputs,
checks, and pass/fail evidence together so later fine-tunes can learn from both
sides of the equation without pretending every attempt shipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = (
    REPO_ROOT / "training-data" / "agentic_coding" / "jupiter_ring_feedback.jsonl"
)
DEFAULT_MANIFEST = (
    REPO_ROOT / "artifacts" / "training_hub" / "jupiter_ring_feedback_manifest.json"
)


SYSTEM = (
    "You are SCBE-Coder learning from the Jupiter-ring feedback lane. "
    "Use the user request, generated output, checks, and outcome evidence to improve future tool and code decisions. "
    "Do not claim failed attempts shipped."
)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _json_excerpt(value: Any, limit: int = 4000) -> str:
    text = json.dumps(value, indent=2, ensure_ascii=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...<truncated>"


def _coding_benchmark_records(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    if not data:
        return []
    records: list[dict[str, Any]] = []
    benchmark = data.get("benchmark", path.parent.name)
    for adapter in data.get("results", []):
        if not isinstance(adapter, dict):
            continue
        adapter_id = str(adapter.get("adapter", "unknown"))
        for task in adapter.get("tasks", []):
            if not isinstance(task, dict):
                continue
            passed = bool(task.get("passed"))
            checks = task.get("checks") if isinstance(task.get("checks"), list) else []
            prompt = str(task.get("prompt", "")).strip()
            output = str(
                task.get("extracted_code") or task.get("raw_generation") or ""
            ).strip()
            if not prompt or not output:
                continue
            outcome = {
                "passed": passed,
                "checks": checks,
                "summary": adapter.get("summary"),
                "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            }
            record = {
                "source_type": "coding_agent_benchmark",
                "id": _sha(
                    [benchmark, adapter_id, task.get("task_id"), prompt, output]
                )[:24],
                "category": "agentic-feedback-ring",
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": output},
                    {
                        "role": "user",
                        "content": "Outcome evidence:\n" + _json_excerpt(outcome),
                    },
                    {
                        "role": "assistant",
                        "content": (
                            "Decision: "
                            + (
                                "ACCEPT_AS_POSITIVE_EXAMPLE"
                                if passed
                                else "USE_AS_REPAIR_EXAMPLE"
                            )
                            + "\nReason: checks show "
                            + (
                                "the requested behavior passed."
                                if passed
                                else "at least one behavior failed."
                            )
                        ),
                    },
                ],
                "metadata": {
                    "source": "scbe_aethermoore",
                    "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "benchmark": benchmark,
                    "adapter": adapter_id,
                    "task_id": task.get("task_id"),
                    "passed": passed,
                    "quality": "positive" if passed else "repair",
                    "deployment_status": "eval_only",
                },
            }
            records.append(record)
    return records


def _operator_bus_records(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    if not data:
        return []
    records: list[dict[str, Any]] = []
    endpoint = data.get("endpoint") if isinstance(data.get("endpoint"), dict) else {}
    for row in endpoint.get("task_scores", []):
        if not isinstance(row, dict):
            continue
        ok = bool(row.get("ok"))
        prompt = f"Route operator task `{row.get('task_id')}` through the governed agent bus."
        outcome = {
            "score": row.get("score"),
            "checks": row.get("checks"),
            "duration_ms": row.get("duration_ms"),
            "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        }
        records.append(
            {
                "source_type": "operator_agent_bus_eval",
                "id": _sha([path.as_posix(), row.get("task_id"), outcome])[:24],
                "category": "agentic-feedback-ring",
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                    {
                        "role": "assistant",
                        "content": "Use local-only routing, emit structured evidence, and avoid raw prompt echo.",
                    },
                    {
                        "role": "user",
                        "content": "Outcome evidence:\n" + _json_excerpt(outcome),
                    },
                    {
                        "role": "assistant",
                        "content": "Decision: "
                        + (
                            "ACCEPT_AS_POSITIVE_EXAMPLE"
                            if ok
                            else "USE_AS_REPAIR_EXAMPLE"
                        )
                        + "\nReason: runtime bus checks "
                        + ("passed." if ok else "did not pass."),
                    },
                ],
                "metadata": {
                    "source": "scbe_aethermoore",
                    "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "task_id": row.get("task_id"),
                    "passed": ok,
                    "quality": "positive" if ok else "repair",
                    "deployment_status": "eval_only",
                },
            }
        )
    return records


def _governance_records(path: Path, limit: int = 40) -> list[dict[str, Any]]:
    data = _load_json(path)
    if not data:
        return []
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(data.get("record_scores", [])[:limit]):
        if not isinstance(row, dict):
            continue
        ok = bool(row.get("ok"))
        attack_class = row.get("attack_class") or row.get("kind") or "governance_case"
        prompt = f"Classify and route governance/security case `{attack_class}`."
        outcome = {
            "expected_block": row.get("expected_block"),
            "predicted_block": row.get("predicted_block"),
            "decision": row.get("decision"),
            "checks": row.get("checks"),
            "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        }
        records.append(
            {
                "source_type": "governance_security_eval",
                "id": _sha([path.as_posix(), idx, outcome])[:24],
                "category": "agentic-feedback-ring",
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                    {
                        "role": "assistant",
                        "content": f"Return a governed decision for `{attack_class}` with plain evidence.",
                    },
                    {
                        "role": "user",
                        "content": "Outcome evidence:\n" + _json_excerpt(outcome),
                    },
                    {
                        "role": "assistant",
                        "content": "Decision: "
                        + (
                            "ACCEPT_AS_POSITIVE_EXAMPLE"
                            if ok
                            else "USE_AS_REPAIR_EXAMPLE"
                        )
                        + "\nReason: governance classification "
                        + ("matched expectations." if ok else "needs repair."),
                    },
                ],
                "metadata": {
                    "source": "scbe_aethermoore",
                    "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "attack_class": attack_class,
                    "passed": ok,
                    "quality": "positive" if ok else "repair",
                    "deployment_status": "eval_only",
                },
            }
        )
    return records


def build_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(
        (REPO_ROOT / "artifacts" / "coding_agent_benchmarks").glob("*/report.json")
    ):
        records.extend(_coding_benchmark_records(path))
    records.extend(
        _operator_bus_records(
            REPO_ROOT
            / "artifacts"
            / "benchmarks"
            / "operator_agent_bus_eval"
            / "latest_report.json"
        )
    )
    records.extend(
        _governance_records(
            REPO_ROOT
            / "artifacts"
            / "benchmarks"
            / "governance_security_eval"
            / "latest_report.json"
        )
    )

    dedup: dict[str, dict[str, Any]] = {}
    for record in records:
        dedup[str(record["id"])] = record
    return list(dedup.values())


def write_outputs(
    out_path: Path = DEFAULT_OUT, manifest_path: Path = DEFAULT_MANIFEST
) -> dict[str, Any]:
    records = build_records()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    counts: dict[str, int] = {}
    qualities: dict[str, int] = {}
    for record in records:
        counts[record["source_type"]] = counts.get(record["source_type"], 0) + 1
        quality = str(record.get("metadata", {}).get("quality", "unknown"))
        qualities[quality] = qualities.get(quality, 0) + 1
    manifest = {
        "schema_version": "scbe_jupiter_ring_feedback_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "output": str(out_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_counts": counts,
        "quality_counts": qualities,
        "principle": "pair user/task inputs with model outputs and outcome evidence; failed evals become repair data, not shipped claims",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build SCBE Jupiter-ring feedback training rows"
    )
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    manifest = write_outputs(Path(args.output), Path(args.manifest))
    print(json.dumps(manifest, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
