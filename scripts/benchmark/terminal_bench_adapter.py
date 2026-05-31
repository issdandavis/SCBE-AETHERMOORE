#!/usr/bin/env python3
"""Terminal-Bench-style adapter contract for SCBE.

This is a local adapter fixture, not an official Terminal-Bench run. It proves
the execution contract SCBE needs before attaching to the official harness:
task setup, shell execution, answer-file capture, verifier, receipt, and
artifact hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "terminal_bench_adapter"


@dataclass(frozen=True)
class TerminalTask:
    task_id: str
    instruction: str
    files: dict[str, str]
    command: tuple[str, ...]
    answer_path: str
    expected_answer: str
    timeout_s: int = 15


@dataclass(frozen=True)
class TerminalReceipt:
    task_id: str
    ok: bool
    answer_ok: bool
    answer_path: str
    answer_sha256: str | None
    artifact_sha256: str
    command: list[str]
    duration_ms: int
    returncode: int
    stdout_tail: str
    stderr_tail: str
    verifier_note: str


TASKS: tuple[TerminalTask, ...] = (
    TerminalTask(
        task_id="answer_file_arithmetic",
        instruction="Write the sum of integers 1 through 10 to answer.txt.",
        files={},
        command=(
            sys.executable,
            "-c",
            "from pathlib import Path; Path('answer.txt').write_text(str(sum(range(1, 11))), encoding='utf-8')",
        ),
        answer_path="answer.txt",
        expected_answer="55",
    ),
    TerminalTask(
        task_id="inspect_workspace_file",
        instruction="Count occurrences of 'alpha' in data/input.txt and write the count to answer.txt.",
        files={"data/input.txt": "alpha beta alpha\ngamma alpha\n"},
        command=(
            sys.executable,
            "-c",
            "from pathlib import Path; data=Path('data/input.txt').read_text(encoding='utf-8'); Path('answer.txt').write_text(str(data.split().count('alpha')), encoding='utf-8')",
        ),
        answer_path="answer.txt",
        expected_answer="3",
    ),
    TerminalTask(
        task_id="script_execution_result",
        instruction="Run the provided script and write its stdout value to answer.txt.",
        files={"tools/emit_value.py": "print('terminal-contract-ok')\n"},
        command=(
            sys.executable,
            "-c",
            "import subprocess, sys; from pathlib import Path; p=subprocess.run([sys.executable, 'tools/emit_value.py'], text=True, capture_output=True, check=True); Path('answer.txt').write_text(p.stdout.strip(), encoding='utf-8')",
        ),
        answer_path="answer.txt",
        expected_answer="terminal-contract-ok",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_task_files(workdir: Path, task: TerminalTask) -> None:
    for rel, content in task.files.items():
        path = workdir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def artifact_hash(workdir: Path, answer_rel: str) -> tuple[str, str | None]:
    answer_path = workdir / answer_rel
    manifest: list[dict[str, str]] = []
    answer_hash = None
    for file in sorted(p for p in workdir.rglob("*") if p.is_file()):
        digest = sha256_bytes(file.read_bytes())
        rel = file.relative_to(workdir).as_posix()
        manifest.append({"path": rel, "sha256": digest})
        if rel == Path(answer_rel).as_posix():
            answer_hash = digest
    return sha256_bytes(json.dumps(manifest, sort_keys=True).encode("utf-8")), answer_hash


def run_task(root: Path, task: TerminalTask) -> TerminalReceipt:
    workdir = root / task.task_id
    workdir.mkdir(parents=True, exist_ok=True)
    write_task_files(workdir, task)

    t0 = time.perf_counter()
    proc = subprocess.run(
        list(task.command),
        cwd=workdir,
        text=True,
        capture_output=True,
        timeout=task.timeout_s,
        check=False,
    )
    duration_ms = int((time.perf_counter() - t0) * 1000)
    answer_file = workdir / task.answer_path
    answer = answer_file.read_text(encoding="utf-8").strip() if answer_file.exists() else ""
    answer_ok = proc.returncode == 0 and answer == task.expected_answer
    artifact_digest, answer_digest = artifact_hash(workdir, task.answer_path)
    note = "answer matched" if answer_ok else f"expected {task.expected_answer!r}, got {answer!r}"
    return TerminalReceipt(
        task_id=task.task_id,
        ok=answer_ok,
        answer_ok=answer_ok,
        answer_path=task.answer_path,
        answer_sha256=answer_digest,
        artifact_sha256=artifact_digest,
        command=list(task.command),
        duration_ms=duration_ms,
        returncode=proc.returncode,
        stdout_tail=proc.stdout[-1200:],
        stderr_tail=proc.stderr[-1200:],
        verifier_note=note,
    )


def load_cross_test_status() -> dict[str, Any]:
    path = REPO_ROOT / "artifacts" / "benchmarks" / "real_patch_tasks" / "latest_report.json"
    if not path.exists():
        return {"lane": "real-patch-tasks", "artifact_exists": False}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"lane": "real-patch-tasks", "artifact_exists": True, "parse_ok": False}
    summary = report.get("summary", {})
    return {
        "lane": "real-patch-tasks",
        "artifact_exists": True,
        "parse_ok": True,
        "decision": summary.get("decision"),
        "task_count": summary.get("task_count"),
        "scbe_test_passes": summary.get("scbe_test_passes"),
        "claim_boundary": report.get("scope") or report.get("claim_boundary"),
    }


def build_report(out_dir: Path, run_id: str | None = None) -> dict[str, Any]:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scbe-terminal-adapter-") as tmp:
        root = Path(tmp)
        receipts = [run_task(root, task) for task in TASKS]

    passed = sum(1 for receipt in receipts if receipt.ok)
    report = {
        "schema_version": "scbe_terminal_bench_adapter_v1",
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "claim_boundary": [
            "Local Terminal-Bench-style adapter contract.",
            "Not an official Terminal-Bench score.",
            "Proves setup, shell execution, answer-file capture, verifier, receipt, and artifact hash.",
        ],
        "summary": {
            "decision": "PASS" if passed == len(TASKS) else "HOLD",
            "task_count": len(TASKS),
            "passed": passed,
            "pass_rate": passed / len(TASKS),
            "answer_contract": "answer.txt",
            "cross_test": "real-patch-tasks",
        },
        "failure_model": {
            "origin": "official harness access and SCBE shell protocol translation",
            "obstacle": "official tb runner is separate from local SCBE command surfaces",
            "next_improvement": "map official Terminal-Bench task import to this answer-file and receipt contract",
        },
        "receipts": [asdict(receipt) for receipt in receipts],
        "cross_test_status": load_cross_test_status(),
    }

    payload = json.dumps(report, indent=2)
    (run_dir / "report.json").write_text(payload, encoding="utf-8")
    (out_dir / "latest_report.json").write_text(payload, encoding="utf-8")
    write_markdown(report, out_dir / "LATEST.md")
    write_markdown(report, run_dir / "report.md")
    return report


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# SCBE Terminal-Bench Adapter",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Decision: `{report['summary']['decision']}`",
        f"- Pass rate: `{report['summary']['passed']}/{report['summary']['task_count']}`",
        "",
        "## Receipts",
        "",
        "| Task | OK | Duration ms | Answer SHA-256 | Artifact SHA-256 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for receipt in report["receipts"]:
        lines.append(
            f"| {receipt['task_id']} | {receipt['ok']} | {receipt['duration_ms']} | {receipt['answer_sha256'] or 'missing'} | {receipt['artifact_sha256']} |"
        )
    lines.extend(
        [
            "",
            "## Failure Model",
            "",
            f"- Origin: {report['failure_model']['origin']}",
            f"- Obstacle: {report['failure_model']['obstacle']}",
            f"- Next improvement: {report['failure_model']['next_improvement']}",
            "",
            "## Claim Boundary",
            "",
            "This is a local adapter contract. Do not call it an official Terminal-Bench score until the official runner executes tasks through this contract.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(out_dir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(
            "terminal-bench adapter: "
            f"decision={summary['decision']} pass={summary['passed']}/{summary['task_count']} "
            f"cross_test={summary['cross_test']}"
        )
        print(f"report={out_dir / 'LATEST.md'}")
    return 0 if report["summary"]["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
