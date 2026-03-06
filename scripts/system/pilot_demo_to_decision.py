#!/usr/bin/env python3
"""Run a compact SCBE pilot evidence path and emit a decision packet.

This script is intentionally simple so it can be run by non-developers:

    python scripts/system/pilot_demo_to_decision.py

Artifacts are written to:
    artifacts/pilot_demo/<run_id>/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Step:
    id: str
    name: str
    command: list[str]
    parse_json: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCBE pilot demo and emit decision artifacts.")
    parser.add_argument("--repo-root", default="", help="Repository root path (auto-detected if omitted).")
    parser.add_argument("--output-dir", default="artifacts/pilot_demo", help="Artifact directory relative to repo root.")
    parser.add_argument("--sample-count", type=int, default=16, help="Count for lattice25d sample command.")
    parser.add_argument("--max-notes", type=int, default=24, help="Max notes for lattice25d notes command.")
    parser.add_argument("--notes-glob", default="docs/**/*.md", help="Glob pattern for lattice notes import.")
    parser.add_argument("--json", action="store_true", help="Print final evidence index JSON.")
    return parser.parse_args()


def run_step(step: Step, repo_root: Path, step_dir: Path, timeout_seconds: int = 240) -> dict[str, Any]:
    started = utc_now()
    t0 = time.perf_counter()
    proc = subprocess.run(
        step.command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )
    duration = round(time.perf_counter() - t0, 4)
    ended = utc_now()

    stdout_path = step_dir / f"{step.id}.stdout.txt"
    stderr_path = step_dir / f"{step.id}.stderr.txt"
    stdout_path.write_text(proc.stdout or "", encoding="utf-8")
    stderr_path.write_text(proc.stderr or "", encoding="utf-8")

    parsed_json_path = ""
    parsed_payload: dict[str, Any] | None = None
    if step.parse_json:
        try:
            parsed_payload = json.loads(proc.stdout)
            parsed_json_path = str((step_dir / f"{step.id}.parsed.json").resolve())
            Path(parsed_json_path).write_text(json.dumps(parsed_payload, indent=2), encoding="utf-8")
        except Exception:
            parsed_payload = None

    return {
        "id": step.id,
        "name": step.name,
        "command": step.command,
        "return_code": proc.returncode,
        "ok": proc.returncode == 0,
        "started_at_utc": utc_iso(started),
        "ended_at_utc": utc_iso(ended),
        "duration_seconds": duration,
        "stdout_path": str(stdout_path.resolve()),
        "stderr_path": str(stderr_path.resolve()),
        "parsed_json_path": parsed_json_path,
        "parsed_payload": parsed_payload,
    }


def collect_metrics(step_results: list[dict[str, Any]]) -> dict[str, Any]:
    sample_payload = next((s.get("parsed_payload") for s in step_results if s["id"] == "step01_lattice_sample"), None)
    notes_payload = next((s.get("parsed_payload") for s in step_results if s["id"] == "step02_lattice_notes"), None)

    metrics: dict[str, Any] = {
        "sample_ingested_count": None,
        "sample_overlap_cells": None,
        "notes_ingested_count": None,
        "notes_overlap_cells": None,
        "notes_lace_edge_count": None,
    }

    if isinstance(sample_payload, dict):
        metrics["sample_ingested_count"] = sample_payload.get("ingested_count")
        overlap = sample_payload.get("overlap_cells")
        metrics["sample_overlap_cells"] = len(overlap) if isinstance(overlap, list) else None

    if isinstance(notes_payload, dict):
        metrics["notes_ingested_count"] = notes_payload.get("ingested_count")
        overlap = notes_payload.get("overlap_cells")
        metrics["notes_overlap_cells"] = len(overlap) if isinstance(overlap, list) else None
        metrics["notes_lace_edge_count"] = notes_payload.get("lace_edge_count")

    return metrics


def write_markdown_index(path: Path, index: dict[str, Any]) -> None:
    lines = [
        "# Pilot Demo Evidence Index",
        "",
        f"- run_id: `{index['run_id']}`",
        f"- generated_at_utc: `{index['generated_at_utc']}`",
        f"- ok: `{index['ok']}`",
        f"- repo_root: `{index['repo_root']}`",
        "",
        "## Key Metrics",
    ]
    for key, value in index.get("key_metrics", {}).items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Steps"])
    for step in index.get("steps", []):
        lines.extend(
            [
                f"### {step['id']} - {step['name']}",
                f"- ok: `{step['ok']}`",
                f"- return_code: `{step['return_code']}`",
                f"- duration_seconds: `{step['duration_seconds']}`",
                f"- command: `{ ' '.join(step['command']) }`",
                f"- stdout: `{step['stdout_path']}`",
                f"- stderr: `{step['stderr_path']}`",
            ]
        )
        if step.get("parsed_json_path"):
            lines.append(f"- parsed_json: `{step['parsed_json_path']}`")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve() if args.repo_root else repo_root_from_script()

    timestamp = utc_now()
    run_id = timestamp.strftime("%Y%m%dT%H%M%SZ")
    run_dir = (repo_root / args.output_dir / run_id).resolve()
    step_dir = run_dir / "steps"
    step_dir.mkdir(parents=True, exist_ok=True)

    steps = [
        Step(
            id="step01_lattice_sample",
            name="Generate lattice sample payload",
            command=[
                sys.executable,
                "-m",
                "hydra.cli",
                "lattice25d",
                "sample",
                "--count",
                str(args.sample_count),
                "--json",
            ],
            parse_json=True,
        ),
        Step(
            id="step02_lattice_notes",
            name="Ingest markdown notes into lattice payload",
            command=[
                sys.executable,
                "-m",
                "hydra.cli",
                "lattice25d",
                "notes",
                "--glob",
                args.notes_glob,
                "--max-notes",
                str(args.max_notes),
                "--json",
            ],
            parse_json=True,
        ),
        Step(
            id="step03_regression_tests",
            name="Run deterministic lattice regression tests",
            command=[sys.executable, "-m", "pytest", "tests/test_lattice25d_ops.py", "-q"],
            parse_json=False,
        ),
    ]

    step_results = [run_step(step, repo_root, step_dir) for step in steps]
    ok = all(bool(step["ok"]) for step in step_results)

    index = {
        "ok": ok,
        "run_id": run_id,
        "generated_at_utc": utc_iso(utc_now()),
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "steps_dir": str(step_dir),
        "steps": [
            {k: v for k, v in step.items() if k != "parsed_payload"}
            for step in step_results
        ],
        "key_metrics": collect_metrics(step_results),
    }

    index_json_path = run_dir / "evidence_index.json"
    index_md_path = run_dir / "evidence_index.md"
    index_json_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    write_markdown_index(index_md_path, index)

    if args.json:
        print(json.dumps(index, indent=2))
    else:
        print(f"[pilot-demo] run_id={run_id}")
        print(f"[pilot-demo] ok={ok}")
        print(f"[pilot-demo] evidence_json={index_json_path}")
        print(f"[pilot-demo] evidence_md={index_md_path}")

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
