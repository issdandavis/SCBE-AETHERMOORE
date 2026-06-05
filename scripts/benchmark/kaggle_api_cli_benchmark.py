#!/usr/bin/env python3
"""Live Kaggle API benchmark through the SCBE CLI wrapper.

This lane proves the local `scbe run` command can route real Kaggle CLI/API
calls, preserve governance metadata, and return parseable evidence. It does not
download datasets, submit competitions, or claim a Kaggle leaderboard score.
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


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "packages" / "cli" / "bin" / "scbe.js"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "kaggle_api_cli"


@dataclass(frozen=True)
class Probe:
    probe_id: str
    command: str
    expect: tuple[str, ...]
    timeout_s: int = 30


PROBES: tuple[Probe, ...] = (
    Probe("kaggle_version", "kaggle --version", ("Kaggle CLI",), 20),
    Probe(
        "getting_started_competitions",
        "kaggle competitions list --category gettingStarted",
        ("Getting Started",),
        30,
    ),
    Probe("titanic_files", "kaggle competitions files titanic", ("train.csv", "test.csv"), 30),
    Probe("iris_dataset_search", "kaggle datasets list -s iris --max-size 1000000", ("Iris Dataset",), 30),
)


def node_command() -> str:
    return "node.exe" if sys.platform.startswith("win") else "node"


def run_scbe_command(command: str, timeout_s: int) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(
        [node_command(), str(CLI), "run", command, "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "schema_version": "scbe_terminal_run_v1",
            "success": False,
            "exit_code": proc.returncode,
            "stdout_preview": proc.stdout[:1000],
            "stderr_preview": proc.stderr[:1000],
            "governance": {"tier": "UNKNOWN", "allowed": False},
        }
    payload["wrapper_exit_code"] = proc.returncode
    payload["wrapper_elapsed_ms"] = elapsed_ms
    return payload


def score_probe(probe: Probe, payload: dict[str, Any]) -> dict[str, Any]:
    text = f"{payload.get('stdout_preview', '')}\n{payload.get('stderr_preview', '')}"
    expected_hits = {needle: (needle.lower() in text.lower()) for needle in probe.expect}
    allowed = bool((payload.get("governance") or {}).get("allowed"))
    tier = str((payload.get("governance") or {}).get("tier", "UNKNOWN"))
    success = bool(payload.get("success")) and allowed and all(expected_hits.values())
    return {
        "probe_id": probe.probe_id,
        "command": probe.command,
        "success": success,
        "exit_code": payload.get("exit_code"),
        "wrapper_exit_code": payload.get("wrapper_exit_code"),
        "duration_ms": payload.get("duration_ms"),
        "wrapper_elapsed_ms": payload.get("wrapper_elapsed_ms"),
        "governance_tier": tier,
        "governance_allowed": allowed,
        "expected_hits": expected_hits,
        "stdout_preview": payload.get("stdout_preview", ""),
        "stderr_preview": payload.get("stderr_preview", ""),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    rows = []
    for probe in report["probes"]:
        rows.append(
            "| {probe_id} | {status} | {tier} | {ms} | `{command}` |".format(
                probe_id=probe["probe_id"],
                status="PASS" if probe["success"] else "FAIL",
                tier=probe["governance_tier"],
                ms=probe.get("wrapper_elapsed_ms"),
                command=probe["command"],
            )
        )
    body = "\n".join(
        [
            "# SCBE Kaggle API CLI Benchmark",
            "",
            f"Generated: {report['generated_at_utc']}",
            f"Decision: {report['summary']['decision']}",
            f"Score: {report['summary']['passed']}/{report['summary']['total']}",
            "",
            "Claim boundary: live Kaggle API reachability through `scbe run`; not a Kaggle competition score.",
            "",
            "| Probe | Status | Gate | ms | Command |",
            "| --- | --- | --- | ---: | --- |",
            *rows,
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark SCBE CLI wrapping live Kaggle API calls.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    probes = [score_probe(probe, run_scbe_command(probe.command, probe.timeout_s)) for probe in PROBES]
    passed = sum(1 for probe in probes if probe["success"])
    total = len(probes)
    report = {
        "schema_version": "scbe_kaggle_api_cli_benchmark_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "decision": "PASS" if passed == total else "FAIL",
            "passed": passed,
            "total": total,
            "score": passed / total if total else 0.0,
        },
        "claim_boundary": "live Kaggle API reachability through scbe run; not a Kaggle competition or leaderboard score",
        "probes": probes,
    }

    latest_json = out_dir / "latest_report.json"
    latest_md = out_dir / "LATEST.md"
    latest_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, latest_md)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"SCBE Kaggle API CLI benchmark: {passed}/{total} {report['summary']['decision']}")
        print(f"report: {latest_json}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
