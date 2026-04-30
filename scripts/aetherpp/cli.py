#!/usr/bin/env python3
"""Aether++ CLI: parse English-like program and emit route packet JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.aetherpp.lower import lower_ast
from scripts.aetherpp.parse import ast_to_dict, parse_program

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "aetherpp"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", help="Inline Aether++ source text.")
    parser.add_argument("--file", type=Path, help="Path to .aether file.")
    parser.add_argument("--source-name", default="inline.aether")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Parse/lower and print compact result only.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.program and not args.file:
        raise SystemExit("Provide --program or --file")
    if args.program and args.file:
        raise SystemExit("Use only one of --program or --file")

    program = args.program if args.program else args.file.read_text(encoding="utf-8")
    source_name = args.source_name if args.program else args.file.name
    nodes = parse_program(program)
    ast = ast_to_dict(nodes)
    packet = lower_ast(ast, source_name=source_name)

    if args.check:
        print(
            json.dumps(
                {
                    "ok": True,
                    "statement_count": len(ast),
                    "route_tongue": packet["shell_contract"]["route_packet"][
                        "route_tongue"
                    ],
                    "command_key": packet["shell_contract"]["route_packet"][
                        "command_key"
                    ],
                    "bijection_ok": packet["build_bijection"]["ok"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "latest_route_packet.json"
    out_ast = args.out_dir / "latest_ast.json"
    out_json.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    out_ast.write_text(
        json.dumps(ast, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"ok": True, "packet": str(out_json), "ast": str(out_ast)}, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
