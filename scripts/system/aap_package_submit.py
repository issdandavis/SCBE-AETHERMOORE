#!/usr/bin/env python3
"""Validate, package, and optionally submit Autonomous Agent Prediction agents.

This wraps the official AAP validator plus Kaggle CLI and prevents the common
root-layout mistake where `agent.yaml` is nested inside an `agent/` directory.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_COMPETITION = "autonomous-agent-prediction-beta"
DEFAULT_COMPETITION_DIR = Path(r"C:\Users\issda\kaggle\aap\competition")
DEFAULT_RECEIPT = Path(r"C:\Users\issda\SCBE-AETHERMOORE\reports\aap_package_submit_receipt.json")


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "cwd": str(cwd) if cwd else None,
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-6000:],
    }


def _resolve_agent_dir(raw: str, competition_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return competition_dir / path


def _zip_agent_dir(agent_dir: Path, out_zip: Path) -> dict[str, Any]:
    if not (agent_dir / "agent.yaml").exists():
        raise FileNotFoundError(f"agent.yaml must be at agent dir root: {agent_dir}")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(agent_dir.rglob("*")):
            if path.is_dir():
                continue
            if path.resolve() == out_zip.resolve():
                continue
            if path.name == ".DS_Store":
                continue
            zf.write(path, path.relative_to(agent_dir).as_posix())

    with zipfile.ZipFile(out_zip) as zf:
        names = zf.namelist()
    return {
        "zip": str(out_zip),
        "file_count": len(names),
        "has_root_agent_yaml": "agent.yaml" in names,
        "first_files": names[:20],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate/package/submit AAP agent dirs.")
    parser.add_argument("--agent-dir", required=True, help="Agent directory with agent.yaml at root.")
    parser.add_argument("--competition-dir", type=Path, default=DEFAULT_COMPETITION_DIR)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION)
    parser.add_argument("--out-zip", type=Path)
    parser.add_argument("--message", default="scbe aap packaged validated submission")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    competition_dir = args.competition_dir
    agent_dir = _resolve_agent_dir(args.agent_dir, competition_dir).resolve()
    out_zip = args.out_zip or (agent_dir.parent / "submission.zip")

    receipt: dict[str, Any] = {
        "ok": False,
        "competition": args.competition,
        "competition_dir": str(competition_dir),
        "agent_dir": str(agent_dir),
        "out_zip": str(out_zip),
        "steps": {},
    }

    validator = competition_dir / "validate_submission.py"
    if not validator.exists():
        raise FileNotFoundError(f"Missing official validator: {validator}")
    if args.submit and shutil.which("kaggle") is None:
        raise FileNotFoundError("kaggle CLI was not found on PATH")

    validate_arg = str(agent_dir)
    try:
        validate_arg = str(agent_dir.relative_to(competition_dir))
    except ValueError:
        pass

    receipt["steps"]["validate"] = _run(
        [sys.executable, str(validator), "--agent-dir", validate_arg],
        cwd=competition_dir,
        timeout=180,
    )
    if receipt["steps"]["validate"]["returncode"] != 0:
        _json_write(args.receipt, receipt)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        return 1

    receipt["steps"]["package"] = _zip_agent_dir(agent_dir, out_zip)
    if not receipt["steps"]["package"]["has_root_agent_yaml"]:
        receipt["error"] = "zip_missing_root_agent_yaml"
        _json_write(args.receipt, receipt)
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        return 1

    if args.submit:
        receipt["steps"]["submit"] = _run(
            ["kaggle", "competitions", "submit", args.competition, "-f", str(out_zip), "-m", args.message],
            cwd=competition_dir,
            timeout=180,
        )
        if receipt["steps"]["submit"]["returncode"] != 0:
            _json_write(args.receipt, receipt)
            if args.json:
                print(json.dumps(receipt, indent=2, sort_keys=True))
            return 1

    if args.status:
        receipt["steps"]["status"] = _run(
            ["kaggle", "competitions", "submissions", args.competition, "-v"],
            cwd=competition_dir,
            timeout=60,
        )

    receipt["ok"] = True
    _json_write(args.receipt, receipt)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print("AAP package guard passed")
        print(f"zip: {out_zip}")
        print(f"receipt: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
