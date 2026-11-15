"""Measure deterministic token-tree growth through the existing quine wafer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.eot_token_lattice import TokenProbability, TokenTableDistribution
from python.scbe.token_honeycomb_nest import validate_b256_table
from python.scbe.token_tree_wafer_growth import (
    ExternalQuineWaferAdapter,
    TokenTreeGrowthSpec,
    grow_token_trees,
)


def _load_table(path: Path, table_id: str | None, b256_prior: str) -> tuple[TokenTableDistribution, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input must be a JSON object")
    if payload.get("schema") == "clay.b256-token-table.v1":
        rows, _ = validate_b256_table(payload)
        if b256_prior == "uniform":
            masses = [1.0] * len(rows)
        else:
            masses = [1.0 / (index + 1.0) for index in range(len(rows))]
        normalizer = sum(masses)
        return (
            TokenTableDistribution(
                table_id=table_id or f"b256-{b256_prior}",
                tokenizer_fingerprint=payload.get("tokenizer_sha256", ""),
                tokens=tuple(
                    TokenProbability(
                        token_id=row["id"],
                        byte_hex=row["hex"],
                        probability=mass / normalizer,
                    )
                    for row, mass in zip(rows, masses, strict=True)
                ),
            ),
            str(payload["table_sha256"]),
        )
    if not isinstance(payload.get("tables"), list):
        raise ValueError("input must be an object containing a tables list")
    candidates = payload["tables"]
    if table_id is not None:
        candidates = [row for row in candidates if row.get("table_id") == table_id]
    if len(candidates) != 1:
        raise ValueError("select exactly one table with --table-id")
    table = candidates[0]
    return (
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
        ),
        None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--wafer-repo", type=Path, default=Path(r"C:\dev\clay-wafer-net"))
    parser.add_argument("--table-id")
    parser.add_argument("--b256-prior", choices=("uniform", "inverse-rank"), default="uniform")
    parser.add_argument("--generations", type=int, default=24)
    parser.add_argument("--depth-cycle", type=int, default=14)
    parser.add_argument("--global-rotation-step-degrees", type=float, default=0.0001)
    parser.add_argument("--patch-rotation-step-degrees", type=float, default=0.00001)
    parser.add_argument("--modulation-strength", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--coordinate-decimals", type=int, default=12)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        parser.error(f"output already exists (use --force): {args.output}")

    table, source_table_sha256 = _load_table(args.input, args.table_id, args.b256_prior)
    result = grow_token_trees(
        table,
        ExternalQuineWaferAdapter(args.wafer_repo),
        TokenTreeGrowthSpec(
            generations=args.generations,
            depth_cycle=args.depth_cycle,
            global_rotation_step_degrees=args.global_rotation_step_degrees,
            patch_rotation_step_degrees=args.patch_rotation_step_degrees,
            modulation_strength=args.modulation_strength,
            seed=args.seed,
            coordinate_decimals=args.coordinate_decimals,
        ),
        source_table_sha256=source_table_sha256,
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
                "receipt_sha256": result["receipt_sha256"],
                **result["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
