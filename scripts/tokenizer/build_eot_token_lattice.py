"""Build and optionally race an exact interwoven EOT token lattice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.eot_token_lattice import (
    CompositeRaceSpec,
    TokenProbability,
    TokenTableDistribution,
    build_interwoven_eot_lattice,
    race_interwoven_token_paths,
)


def _load(path: Path) -> tuple[TokenTableDistribution, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), list):
        raise ValueError("input must be an object containing a tables list")
    tables = []
    for table in payload["tables"]:
        tables.append(
            TokenTableDistribution(
                table_id=table["table_id"],
                tokenizer_fingerprint=table.get("tokenizer_fingerprint", ""),
                tokens=tuple(
                    TokenProbability(
                        token_id=row["token_id"],
                        byte_hex=row["byte_hex"],
                        probability=row["probability"],
                        label=row.get("label", ""),
                    )
                    for row in table["tokens"]
                ),
            )
        )
    return tuple(tables)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--race", action="store_true")
    parser.add_argument("--start-prefix-hex", default="")
    parser.add_argument("--beam-width", type=int, default=32)
    parser.add_argument("--max-steps", type=int, default=64)
    parser.add_argument("--edge-probability-floor", type=float, default=0.0)
    parser.add_argument("--path-probability-floor", type=float, default=0.0)
    parser.add_argument("--probability-power", type=float, default=1.0)
    parser.add_argument("--score-basis", choices=("conditional", "absolute"), default="conditional")
    parser.add_argument("--max-completed-paths", type=int, default=4096)
    parser.add_argument("--max-expansions", type=int, default=100_000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        parser.error(f"output already exists (use --force): {args.output}")

    lattice = build_interwoven_eot_lattice(_load(args.input))
    result: dict[str, object] = {"lattice": lattice}
    if args.race:
        result["race"] = race_interwoven_token_paths(
            lattice,
            start_prefix=bytes.fromhex(args.start_prefix_hex),
            spec=CompositeRaceSpec(
                beam_width=args.beam_width,
                max_steps=args.max_steps,
                edge_probability_floor=args.edge_probability_floor,
                path_probability_floor=args.path_probability_floor,
                probability_power=args.probability_power,
                score_basis=args.score_basis,
                max_completed_paths=args.max_completed_paths,
                max_expansions=args.max_expansions,
            ),
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "lattice_sha256": lattice["receipt_sha256"],
                "node_count": lattice["metrics"]["prefix_node_count"],
                "token_count": lattice["metrics"]["token_count"],
                "race_built": args.race,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
