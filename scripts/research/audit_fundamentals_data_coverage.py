"""Write a receipt-backed coverage audit for a completed Clay campaign."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.training_data_coverage import (
    audit_campaign,
    render_markdown,
)  # noqa: E402


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


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
    json_output = args.json_output or root / "DATA_COVERAGE_AUDIT.json"
    markdown_output = args.markdown_output or root / "DATA_COVERAGE_AUDIT.md"
    report = audit_campaign(root)
    _atomic_text(json_output.resolve(), _json_text(report))
    _atomic_text(markdown_output.resolve(), render_markdown(report))
    print(
        json.dumps(
            {
                "audit_sha256": report["audit_sha256"],
                "all_stored_train_rows_seen_by_every_sampler": report["all_stored_train_rows_seen_by_every_sampler"],
                "json_output": str(json_output.resolve()),
                "markdown_output": str(markdown_output.resolve()),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
