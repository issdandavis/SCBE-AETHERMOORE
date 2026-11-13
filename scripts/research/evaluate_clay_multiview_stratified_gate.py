"""Evaluate the preregistered held-sector gate for a completed Clay campaign."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.clay_multiview_stratified_gate import (  # noqa: E402
    evaluate_stratified_gate,
    render_markdown,
)


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.parent / f".{path.name}.{os.getpid()}.pending"
    pending.write_text(value, encoding="utf-8", newline="\n")
    for attempt in range(6):
        try:
            os.replace(pending, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.1 * (attempt + 1))


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_root", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.campaign_root.resolve()
    result_path = root / "RESULT.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"completed producer result is absent: {result_path}")
    producer = json.loads(result_path.read_text(encoding="utf-8"))
    report = evaluate_stratified_gate(producer)
    json_output = (args.json_output or root / "STRATIFIED_GATE.json").resolve()
    markdown_output = (args.markdown_output or root / "STRATIFIED_GATE.md").resolve()
    _atomic_text(json_output, _json_text(report))
    _atomic_text(markdown_output, render_markdown(report))
    print(
        json.dumps(
            {
                "gate_sha256": report["gate_sha256"],
                "json_output": str(json_output),
                "markdown_output": str(markdown_output),
                "promotion_authorized": False,
                "verdict": report["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
