#!/usr/bin/env python3
"""
SCBE AI Kernel Wrapper Runner
-----------------------------

Loads a job spec (YAML/JSON), applies SCBE defensive mesh gates to each task,
optionally calls a browser worker endpoint, and emits governance artifacts +
Hugging Face training rows.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

import yaml

from python.scbe.defensive_mesh import DefensiveMeshKernel


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run SCBE AI kernel wrapper over a job spec")
    p.add_argument("--job", required=True, help="Path to YAML/JSON job spec")
    p.add_argument("--run-dir", default="", help="Optional run dir. Default: training/runs/scbe_ai_kernel/<timestamp>")
    p.add_argument(
        "--browser-endpoint", default="", help="Optional browser worker endpoint, e.g. http://127.0.0.1:8000/scrape"
    )
    p.add_argument(
        "--hf-output",
        default="training-data/hf-digimon-egg/defensive_mesh_sft.jsonl",
        help="Output JSONL for defensive mesh training rows",
    )
    p.add_argument("--skip-hf", action="store_true", help="Skip writing Hugging Face SFT rows")
    return p.parse_args()


def read_job(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def call_browser_worker(endpoint: str, task_payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(task_payload).encode("utf-8")
    req = urlrequest.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=90) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    job_path = (repo_root / args.job).resolve() if not Path(args.job).is_absolute() else Path(args.job)
    spec = read_job(job_path)

    job, tasks = DefensiveMeshKernel.from_job_spec(spec)

    run_dir = Path(args.run_dir) if args.run_dir else (repo_root / "training" / "runs" / "scbe_ai_kernel" / utc_stamp())
    run_dir.mkdir(parents=True, exist_ok=True)

    governed_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    browser_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    hf_rows: list[dict[str, Any]] = []

    previous_antibody_load = 0.0
    for idx, task in enumerate(tasks, start=1):
        gate = DefensiveMeshKernel.gate_task(job, task, previous_antibody_load=previous_antibody_load)
        previous_antibody_load = float(
            gate.kernel_gate.get("turnstile", {}).get("antibody_load", previous_antibody_load)
        )

        row = {
            "job_id": job.job_id,
            "task": task.__dict__,
            "gate": gate.to_dict(),
        }
        governed_rows.append(row)

        if gate.decision != "ALLOW":
            blocked_rows.append(row)
        else:
            if args.browser_endpoint:
                payload = {
                    "url": task.url,
                    "selector": task.selector,
                    "fields": task.fields,
                    "actions": task.actions,
                }
                result = call_browser_worker(args.browser_endpoint, payload)
                browser_rows.append({"task_id": task.task_id, "raw": result})
                raw_items = result.get("items", []) if isinstance(result, dict) else []
                clean_items = DefensiveMeshKernel.sanitize_items(
                    raw_items,
                    allowed_fields=job.allowed_fields,
                    pii_rules=job.pii_rules,
                )
                output_rows.extend(clean_items)

        if not args.skip_hf:
            hf_rows.append(
                DefensiveMeshKernel.build_hf_training_row(
                    idx=idx,
                    job=job,
                    task=task,
                    gate=gate,
                )
            )

    review = DefensiveMeshKernel.review_output(job, output_rows)

    write_json(run_dir / "job.json", {"job": job.__dict__, "task_count": len(tasks)})
    write_json(run_dir / "governed_tasks.json", governed_rows)
    write_json(run_dir / "blocked_tasks.json", blocked_rows)
    write_json(run_dir / "browser_results.json", browser_rows)
    write_json(run_dir / "output_items.json", output_rows)
    write_json(run_dir / "review.json", review)

    hf_written = 0
    if not args.skip_hf:
        hf_written = append_jsonl((repo_root / args.hf_output), hf_rows)

    summary = {
        "job_id": job.job_id,
        "run_dir": str(run_dir.relative_to(repo_root)).replace("\\", "/"),
        "tasks_total": len(tasks),
        "tasks_blocked": len(blocked_rows),
        "tasks_allowed": len(tasks) - len(blocked_rows),
        "output_items": len(output_rows),
        "review_status": review.get("status"),
        "hf_rows_written": hf_written,
        "hf_output": args.hf_output if not args.skip_hf else None,
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
