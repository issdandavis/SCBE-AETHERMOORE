"""Side-effect-free verifier and optional Docker boundary for Clay tool tapes."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from clay_tool_sequence_curriculum import parse_call_tape
from clay_bijective_router import verify_tool_call


SCHEMA = "clay.tool-sandbox.v1"
HERE = Path(__file__).resolve().parent
DEFAULT_IMAGE = "clay-tool-sandbox:local"


def static_seal(lines: Sequence[str]) -> dict[str, Any]:
    receipts = [verify_tool_call(line) for line in lines]
    return {
        "calls": len(lines),
        "valid": sum(int(receipt["valid"]) for receipt in receipts),
        "all_valid": bool(lines) and all(receipt["valid"] for receipt in receipts),
        "receipts": receipts,
    }


def docker_available() -> bool:
    executable = shutil.which("docker")
    if not executable:
        return False
    result = subprocess.run(
        [executable, "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return result.returncode == 0


def docker_command(image: str = DEFAULT_IMAGE) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "1",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=32m",
        "-i",
        image,
        "python",
        "clay_tool_sandbox.py",
        "--stdin",
        "--static-only",
    ]


def verify_tape(
    text: str,
    *,
    use_docker: bool,
    image: str = DEFAULT_IMAGE,
) -> dict[str, Any]:
    lines = parse_call_tape(text)
    local = static_seal(lines)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "static_only",
        "local": local,
        "docker": {
            "requested": use_docker,
            "available": docker_available(),
            "executed": False,
        },
        "accepted": local["all_valid"],
    }
    if not use_docker or not report["docker"]["available"] or not local["all_valid"]:
        return report
    result = subprocess.run(
        docker_command(image),
        input=text,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    report["docker"].update(
        {
            "executed": True,
            "returncode": result.returncode,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
        }
    )
    report["mode"] = "docker_static_seal"
    report["accepted"] = local["all_valid"] and result.returncode == 0
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tape", nargs="?")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--docker", action="store_true")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.stdin:
        text = sys.stdin.read()
    elif args.tape:
        text = Path(args.tape).read_text(encoding="utf-8")
    else:
        raise SystemExit("provide a tape file or --stdin")
    report = verify_tape(
        text,
        use_docker=args.docker and not args.static_only,
        image=args.image,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
