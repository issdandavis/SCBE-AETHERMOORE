#!/usr/bin/env python3
"""Run the v8 DSL promotion eval suite for one adapter.

Suite:
1. DSL executable accuracy.
2. Stage 6 regression guard.
3. Frozen assistant-token perplexity.

This wrapper is deliberately thin. It preserves each scorer's own contract and
exit code, then writes one summary JSON/Markdown for promotion review.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "dsl_eval_reports" / "v8_suite"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def adapter_exists(adapter: str) -> bool:
    if "/" in adapter and not Path(adapter).exists():
        return True
    return Path(adapter).exists()


def run_step(name: str, command: list[str], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "name": name,
            "command": command,
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "status": "dry_run",
        }
    proc = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "name": name,
        "command": command,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-3000:],
        "status": "pass" if proc.returncode == 0 else "fail",
    }


def latest_matching_report(root: Path, suffix: str) -> str:
    matches = sorted(root.glob(f"*{suffix}"), key=lambda path: path.stat().st_mtime, reverse=True)
    return str(matches[0]) if matches else ""


def write_summary(out_dir: Path, payload: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# DSL v8 Eval Suite",
        "",
        f"- Adapter: `{payload['adapter']}`",
        f"- Base: `{payload['base_model']}`",
        f"- Overall pass: `{payload['overall_pass']}`",
        "",
        "| Step | Status | Return Code | Report |",
        "| --- | --- | ---: | --- |",
    ]
    for step in payload["steps"]:
        lines.append(
            f"| `{step['name']}` | `{step['status']}` | {step['returncode']} | `{step.get('report_path', '')}` |"
        )
    lines.append("")
    lines.append("## Commands")
    for step in payload["steps"]:
        lines.extend(["", f"### {step['name']}", "", "```powershell", " ".join(step["command"]), "```"])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, help="HF repo id or local LoRA adapter path.")
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dsl-limit", type=int, default=0, help="Limit DSL holdout rows; 0 = full holdout.")
    parser.add_argument("--frozen-per-file-limit", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit quantization for frozen perplexity.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not adapter_exists(args.adapter):
        print(f"BLOCKED: adapter path does not exist: {args.adapter}", file=sys.stderr)
        return 2

    stamp = utc_stamp()
    out_dir = args.out_root / stamp
    common_python = sys.executable
    dsl_out = PROJECT_ROOT / "artifacts" / "dsl_eval_reports"
    frozen_out = PROJECT_ROOT / "artifacts" / "model_evals" / "frozen"

    commands: list[tuple[str, list[str]]] = [
        (
            "dsl_executable",
            [
                common_python,
                "scripts/eval/score_dsl_executable.py",
                "--adapter",
                args.adapter,
                "--base",
                args.base,
                "--max-new-tokens",
                str(args.max_new_tokens),
            ],
        ),
        (
            "stage6_regression",
            [
                common_python,
                "scripts/eval/score_stage6_regression.py",
                "--adapter",
                args.adapter,
                "--base",
                args.base,
            ],
        ),
        (
            "frozen_perplexity",
            [
                common_python,
                "scripts/eval/score_adapter_frozen.py",
                "--adapter",
                args.adapter,
                "--base-model",
                args.base,
                "--per-file-limit",
                str(args.frozen_per_file_limit),
            ],
        ),
    ]
    if args.no_4bit:
        commands[2][1].append("--no-4bit")
    if args.dsl_limit:
        commands[0][1].extend(["--limit", str(args.dsl_limit)])

    steps = []
    for name, command in commands:
        print(f"[v8-suite] running {name}", flush=True)
        row = run_step(name, command, dry_run=args.dry_run)
        if name == "dsl_executable":
            row["report_path"] = latest_matching_report(dsl_out, "_executable_accuracy.json")
        elif name == "stage6_regression":
            row["report_path"] = latest_matching_report(dsl_out, "_stage6_regression.json")
        elif name == "frozen_perplexity":
            row["report_path"] = str(frozen_out / "latest" / "report.json")
        steps.append(row)
        if row["status"] == "fail":
            print(f"[v8-suite] {name} failed; continuing to collect all diagnostics", flush=True)

    overall_pass = all(step["status"] in {"pass", "dry_run"} for step in steps)
    payload = {
        "schema_version": "scbe_dsl_v8_eval_suite_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "adapter": args.adapter,
        "base_model": args.base,
        "dry_run": args.dry_run,
        "overall_pass": overall_pass,
        "steps": steps,
    }
    write_summary(out_dir, payload)
    print(f"Suite JSON: {out_dir / 'summary.json'}")
    print(f"Suite MD:   {out_dir / 'summary.md'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
