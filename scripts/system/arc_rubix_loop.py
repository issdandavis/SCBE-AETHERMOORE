#!/usr/bin/env python3
"""Coordinate ARC Rubix local solve/score/dashboard loops.

This script is deterministic by default. It runs local scripts, writes receipts,
and only calls Ollama when --ollama is supplied.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from subprocess import run
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ARC_ROOT = Path(r"C:\Users\issda\kaggle\arc_agi2_2026")
COMP_ROOT = ARC_ROOT / "competition"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "openclaw:latest"


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _text_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_step(cmd: list[str]) -> dict[str, Any]:
    started = time.time()
    proc = run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=3600,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def _parse_last_json(text: str) -> Any | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _ollama_generate(url: str, model: str, prompt: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
        },
    }
    request = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {
            "ok": True,
            "model": model,
            "text": str(data.get("response", "")).strip(),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "ok": False,
            "model": model,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _defaults_for_mode(mode: str) -> dict[str, Path | None]:
    if mode == "test":
        return {
            "challenges": COMP_ROOT / "arc-agi_test_challenges.json",
            "solutions": None,
            "submission": ARC_ROOT / "submission.json",
        }
    return {
        "challenges": COMP_ROOT / "arc-agi_evaluation_challenges.json",
        "solutions": COMP_ROOT / "arc-agi_evaluation_solutions.json",
        "submission": ARC_ROOT / "eval_submission.json",
    }


def _compact_rule_report(report_path: Path, limit: int = 24) -> dict[str, Any]:
    if not report_path.exists():
        return {"available": False, "items": []}
    report = _json_load(report_path)
    rows = report.get("tasks", []) if isinstance(report, dict) else []
    compact: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        compact.append(
            {
                "task_id": row.get("task_id"),
                "status": row.get("status"),
                "rules": row.get("rules", [])[:2],
            }
        )
    return {
        "available": True,
        "count": len(rows),
        "sample": compact,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local ARC Rubix solve/score/dashboard loops with optional Ollama notes."
    )
    parser.add_argument("--mode", choices=["eval", "test"], default="eval")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--challenges", type=Path)
    parser.add_argument("--solutions", type=Path)
    parser.add_argument("--submission", "--out", dest="submission", type=Path)
    parser.add_argument("--report", type=Path, default=ARC_ROOT / "arc_rubix_report.json")
    parser.add_argument("--dashboard", type=Path, default=ARC_ROOT / "arc_rubix_dashboard.html")
    parser.add_argument("--receipt", type=Path, default=ARC_ROOT / "arc_rubix_loop_receipt.json")
    parser.add_argument("--ollama", action="store_true")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    defaults = _defaults_for_mode(args.mode)
    challenges = args.challenges or defaults["challenges"]
    solutions = args.solutions if args.solutions is not None else defaults["solutions"]
    submission = args.submission or defaults["submission"]

    if challenges is None:
        raise SystemExit("No challenge file was provided.")
    if submission is None:
        raise SystemExit("No submission output file was provided.")

    commands: list[dict[str, Any]] = []
    score_payload: Any | None = None
    iterations = max(1, args.iterations)

    solver = REPO_ROOT / "scripts" / "system" / "arc_rubix_solver.py"
    scorer = REPO_ROOT / "scripts" / "system" / "arc_rubix_score.py"
    dashboarder = REPO_ROOT / "scripts" / "system" / "arc_rubix_dashboard.py"

    for iteration in range(iterations):
        solve_cmd = [
            sys.executable,
            str(solver),
            "--challenges",
            str(challenges),
            "--out",
            str(submission),
            "--report",
            str(args.report),
            "--json",
        ]
        solve_result = _run_step(solve_cmd)
        solve_result["iteration"] = iteration + 1
        commands.append(solve_result)

        if solve_result["returncode"] != 0:
            break

        if solutions is not None and Path(solutions).exists():
            score_cmd = [
                sys.executable,
                str(scorer),
                "--submission",
                str(submission),
                "--solutions",
                str(solutions),
                "--json",
            ]
            score_result = _run_step(score_cmd)
            score_result["iteration"] = iteration + 1
            score_payload = _parse_last_json(score_result.get("stdout_tail", ""))
            commands.append(score_result)
            if score_result["returncode"] != 0:
                break

    dashboard_cmd = [
        sys.executable,
        str(dashboarder),
        "--challenges",
        str(challenges),
        "--submission",
        str(submission),
        "--report",
        str(args.report),
        "--out",
        str(args.dashboard),
        "--json",
    ]
    dashboard_result = _run_step(dashboard_cmd)
    commands.append(dashboard_result)

    report_summary = _compact_rule_report(args.report)
    ollama_result: dict[str, Any] | None = None
    if args.ollama:
        prompt = (
            "You are a local ARC Rubix critic. Do not solve from scratch. "
            "Review this compact run receipt and name the next deterministic "
            "rule-template additions that would improve the solver. Keep it short.\n\n"
            + json.dumps(
                {
                    "mode": args.mode,
                    "score": score_payload,
                    "rules": report_summary,
                    "submission": str(submission),
                    "dashboard": str(args.dashboard),
                },
                indent=2,
                sort_keys=True,
            )[:12000]
        )
        ollama_result = _ollama_generate(args.ollama_url, args.ollama_model, prompt)
        notes_path = ARC_ROOT / "arc_rubix_ollama_notes.md"
        note_body = [
            "# ARC Rubix Ollama Notes",
            "",
            f"- model: {args.ollama_model}",
            f"- ok: {ollama_result.get('ok')}",
            "",
            "```text",
            str(ollama_result.get("text") or ollama_result.get("error") or ""),
            "```",
            "",
        ]
        _text_write(notes_path, "\n".join(note_body))
        ollama_result["notes_path"] = str(notes_path)

    receipt = {
        "ok": all(step.get("returncode") == 0 for step in commands),
        "mode": args.mode,
        "iterations": iterations,
        "paths": {
            "challenges": str(challenges),
            "solutions": str(solutions) if solutions is not None else None,
            "submission": str(submission),
            "report": str(args.report),
            "dashboard": str(args.dashboard),
            "receipt": str(args.receipt),
        },
        "score": score_payload,
        "report_summary": report_summary,
        "ollama": ollama_result,
        "commands": commands,
    }
    _json_write(args.receipt, receipt)

    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(f"ARC Rubix loop {'passed' if receipt['ok'] else 'failed'}")
        print(f"submission: {submission}")
        print(f"report: {args.report}")
        print(f"dashboard: {args.dashboard}")
        print(f"receipt: {args.receipt}")
        if score_payload is not None:
            print(f"score: {score_payload}")
        if ollama_result is not None:
            print(f"ollama: {ollama_result}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
