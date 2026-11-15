"""Compile explicit lattice-token bindings into a verified semantic-VM mask."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.token_action_lithography import (
    ActionTokenBinding,
    compile_token_action_mask,
)


def _read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lattice", type=Path)
    parser.add_argument("bindings", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-steps", type=int, default=10_000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        parser.error(f"output already exists (use --force): {args.output}")
    lattice_payload = _read_object(args.lattice)
    lattice = lattice_payload.get("lattice", lattice_payload)
    binding_payload = _read_object(args.bindings)
    rows = binding_payload.get("bindings")
    if not isinstance(rows, list):
        parser.error("bindings input must contain a bindings list")
    bindings = tuple(
        ActionTokenBinding(
            table_id=row["table_id"],
            token_id=row["token_id"],
            byte_hex=row["byte_hex"],
            semantic_token=row["semantic_token"],
            operands=tuple(row.get("operands", ())),
        )
        for row in rows
    )
    receipt = compile_token_action_mask(
        lattice,
        bindings,
        execute=args.execute,
        max_steps=args.max_steps,
        projection_receipt_sha256=binding_payload.get("projection_receipt_sha256"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "receipt_sha256": receipt["receipt_sha256"],
                "instruction_count": receipt["program"]["instruction_count"],
                "executed": receipt["execution"] is not None,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
