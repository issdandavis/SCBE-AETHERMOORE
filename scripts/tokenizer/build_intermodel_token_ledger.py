"""Build an exact binary/token/code intermodel ledger from local source files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.intermodel_token_ledger import (
    CodeModelInput,
    build_code_intermodel_ledger,
    canonical_json,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Join code tokenizations through exact source bytes and existing " "language-neutral operation signatures."
        )
    )
    parser.add_argument(
        "--input",
        nargs=3,
        action="append",
        metavar=("MODEL_ID", "LANGUAGE", "PATH"),
        required=True,
        help="repeat at least twice; PATH is read as strict UTF-8",
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if len(args.input) < 2:
        raise SystemExit("at least two --input MODEL_ID LANGUAGE PATH groups are required")
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    rows: list[CodeModelInput] = []
    for model_id, language, raw_path in args.input:
        path = Path(raw_path).resolve()
        if not path.is_file():
            raise SystemExit(f"source file does not exist: {path}")
        rows.append(
            CodeModelInput(
                model_id=model_id,
                language=language,
                source=path.read_text(encoding="utf-8", errors="strict"),
                source_name=str(path),
            )
        )
    ledger = build_code_intermodel_ledger(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(ledger) + b"\n")
    print(
        f"wrote {output} models={ledger['model_count']} "
        f"aligned={ledger['aligned']} action_cells={len(ledger['action_cells'])} "
        f"sha256={ledger['ledger_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
