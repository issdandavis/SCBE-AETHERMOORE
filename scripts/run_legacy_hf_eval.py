#!/usr/bin/env python3
"""Launch the live legacy HF eval with a Python runtime that supports local adapter fallback."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPT = PROJECT_ROOT / "scripts" / "eval_legacy_hf_model.py"


def candidate_python_paths() -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()

    for raw in [
        os.environ.get("SCBE_HF_EVAL_PYTHON", "").strip(),
        sys.executable,
        r"C:\Users\issda\Python312\python.exe",
        r"C:\Python312\python.exe",
    ]:
        if not raw:
            continue
        path = Path(raw)
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(path)
    return candidates


def python_supports_local_adapter(python_path: Path) -> bool:
    if not python_path.exists():
        return False

    probe = (
        "import huggingface_hub, peft, transformers, torch\n"
        "import torch.nn\n"
        "assert getattr(torch, '__version__', None)\n"
        "print('ok')\n"
    )
    try:
        completed = subprocess.run(
            [str(python_path), "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except OSError:
        return False
    return completed.returncode == 0


def choose_python_for_eval(preferred_python: str | None = None) -> Path:
    if preferred_python:
        preferred = Path(preferred_python)
        if python_supports_local_adapter(preferred):
            return preferred
        raise RuntimeError(f"Preferred Python runtime is not usable for local adapter eval: {preferred}")

    for candidate in candidate_python_paths():
        if python_supports_local_adapter(candidate):
            return candidate

    tried = ", ".join(str(path) for path in candidate_python_paths())
    raise RuntimeError(f"No compatible Python runtime found for live adapter evaluation. Tried: {tried}")


def build_eval_command(python_path: Path, passthrough_args: list[str]) -> list[str]:
    return [str(python_path), str(EVAL_SCRIPT), *passthrough_args]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Launch the legacy HF eval using a Python runtime with working torch/transformers/peft support."
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
        help="Resolve the interpreter and print the command without executing the eval.",
    )
    args, passthrough = parser.parse_known_args(argv)

    python_path = choose_python_for_eval(args.preferred_python)
    command = build_eval_command(python_path, passthrough)

    if args.print_command or args.dry_run:
        print("Resolved command:", " ".join(command))

    if args.dry_run:
        return 0

    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
