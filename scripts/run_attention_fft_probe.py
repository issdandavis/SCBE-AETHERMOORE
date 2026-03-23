#!/usr/bin/env python3
"""Launch the live attention FFT probe with a Python runtime that has real torch support."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from scripts.run_legacy_hf_eval import choose_python_for_eval


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE_SCRIPT = PROJECT_ROOT / "scripts" / "probe_attention_fft.py"


def build_probe_command(python_path: Path, passthrough_args: list[str]) -> list[str]:
    return [str(python_path), str(PROBE_SCRIPT), *passthrough_args]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Launch the attention FFT probe using a Python runtime with working torch/transformers support."
    )
    parser.add_argument("--python", dest="preferred_python", help="Explicit Python interpreter to use.")
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="Print the resolved command before execution.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the interpreter and print the command without executing the probe.",
    )
    args, passthrough = parser.parse_known_args(argv)

    python_path = choose_python_for_eval(args.preferred_python)
    command = build_probe_command(python_path, passthrough)

    if args.print_command or args.dry_run:
        print("Resolved command:", " ".join(command))

    if args.dry_run:
        return 0

    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
