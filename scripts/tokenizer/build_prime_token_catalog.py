#!/usr/bin/env python3
"""Build and query the SCBE six-view prime token catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_catalog import (  # noqa: E402
    DEFAULT_TOKENIZER,
    DEFAULT_TOKENIZER_SHA256,
    PrimeTokenCatalogBuilder,
    audit_catalog_sources,
    audit_catalog_view_structure,
    search_goal,
    update_probability_lookup,
)


def _write_or_print(payload: dict, output: str | None) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output:
        path = Path(output).resolve()
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded + "\n", encoding="utf-8")
        print(path)
    else:
        print(encoded)


def build(args: argparse.Namespace) -> int:
    if not args.input and not args.source_manifest:
        raise ValueError("build needs --input or --source-manifest")
    builder = PrimeTokenCatalogBuilder(
        args.output,
        tokenizer_path=args.tokenizer,
        tokenizer_sha256=args.tokenizer_sha256,
        section_chars=args.section_chars,
        range_size=args.range_size,
    )
    if args.input:
        builder.ingest_paths(args.input, source_kind=args.source_kind, license_name=args.license)
    for source_manifest in args.source_manifest:
        builder.ingest_source_manifest(source_manifest)
    manifest = builder.finalize()
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def search(args: argparse.Namespace) -> int:
    receipt = search_goal(
        args.database,
        args.goal,
        limit=args.limit,
        topology_steps=args.topology_steps,
        damping=args.damping,
        ablate_views=args.ablate,
        control=args.control,
        control_seed=args.control_seed,
        source_kinds=args.prefer_source_kind,
    )
    if args.model_anchor_sha256:
        receipt["probability_update"] = update_probability_lookup(
            args.database,
            receipt,
            model_anchor_sha256=args.model_anchor_sha256,
            token_limit=args.token_limit,
            probability_database=args.probability_database,
        )
    _write_or_print(receipt, args.receipt)
    return 0


def probability(args: argparse.Namespace) -> int:
    receipt = json.loads(Path(args.search_receipt).read_text(encoding="utf-8"))
    result = update_probability_lookup(
        args.database,
        receipt,
        model_anchor_sha256=args.model_anchor_sha256,
        token_limit=args.token_limit,
        probability_database=args.probability_database,
    )
    _write_or_print(result, args.receipt)
    return 0


def audit(args: argparse.Namespace) -> int:
    result = audit_catalog_sources(args.database)
    _write_or_print(result, args.receipt)
    return 0 if result["status"] == "STRUCTURAL_GATE_PASS" else 1


def audit_views(args: argparse.Namespace) -> int:
    result = audit_catalog_view_structure(args.database)
    _write_or_print(result, args.receipt)
    return 0 if result["status"] == "STRUCTURAL_VIEW_AUDIT_PASS" else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    build_parser = commands.add_parser("build", help="build an immutable catalog")
    build_parser.add_argument("--input", action="append", default=[], help="file or directory; repeatable")
    build_parser.add_argument(
        "--source-manifest",
        action="append",
        default=[],
        help="hash-bound per-source attribution manifest; repeatable",
    )
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--source-kind", default="auto")
    build_parser.add_argument("--license", default="unknown")
    build_parser.add_argument("--section-chars", type=int, default=8192)
    build_parser.add_argument("--range-size", type=int, default=4096)
    build_parser.add_argument("--tokenizer", default=str(DEFAULT_TOKENIZER))
    build_parser.add_argument("--tokenizer-sha256", default=DEFAULT_TOKENIZER_SHA256)
    build_parser.set_defaults(run=build)

    search_parser = commands.add_parser("search", help="surf the six-view field toward a goal")
    search_parser.add_argument("--database", required=True)
    search_parser.add_argument("--goal", required=True)
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--topology-steps", type=int, default=2)
    search_parser.add_argument("--damping", type=float, default=0.35)
    search_parser.add_argument("--ablate", action="append", default=[])
    search_parser.add_argument("--control", choices=("aligned", "shuffled"), default="aligned")
    search_parser.add_argument("--control-seed", type=int, default=0)
    search_parser.add_argument("--prefer-source-kind", action="append", default=[])
    search_parser.add_argument("--model-anchor-sha256")
    search_parser.add_argument("--token-limit", type=int, default=256)
    search_parser.add_argument("--probability-database")
    search_parser.add_argument("--receipt")
    search_parser.set_defaults(run=search)

    probability_parser = commands.add_parser("update-probability", help="apply one audited lookup-table update")
    probability_parser.add_argument("--database", required=True)
    probability_parser.add_argument("--search-receipt", required=True)
    probability_parser.add_argument("--model-anchor-sha256", required=True)
    probability_parser.add_argument("--token-limit", type=int, default=256)
    probability_parser.add_argument("--probability-database")
    probability_parser.add_argument("--receipt")
    probability_parser.set_defaults(run=probability)

    audit_parser = commands.add_parser("audit", help="verify source diversity, rights, views, and manifest binding")
    audit_parser.add_argument("--database", required=True)
    audit_parser.add_argument("--receipt")
    audit_parser.set_defaults(run=audit)

    view_audit_parser = commands.add_parser(
        "audit-views",
        help="measure six-view coverage and signature collisions without scoring",
    )
    view_audit_parser.add_argument("--database", required=True)
    view_audit_parser.add_argument("--receipt")
    view_audit_parser.set_defaults(run=audit_views)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    raise SystemExit(main())
