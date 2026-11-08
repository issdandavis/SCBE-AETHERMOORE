#!/usr/bin/env python3
"""Verify E92 late-output fusion on a synthetic catalog only."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.prime_token_catalog import (  # noqa: E402
    InputRecord,
    LATE_OUTPUT_FUSION_K,
    LATE_OUTPUT_FUSION_REVISION,
    PrimeTokenCatalogBuilder,
    VIEW_NAMES,
    search_goal,
    search_late_output_fused,
    sha256_file,
)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _fixture(root: Path) -> Path:
    builder = PrimeTokenCatalogBuilder(root / "catalog", section_chars=256, range_size=128)
    records = (
        (
            "fixture://prime.md",
            "The prime sieve marks composite multiples, preserves survivors, and records exact strike factors.",
        ),
        (
            "fixture://routing.md",
            "A highway junction sends a car beneath the bridge or onward toward town using an explicit route.",
        ),
        (
            "fixture://speech.md",
            "Active reading tracks nouns, verbs, sentence roles, spoken rhythm, and uncertain evidence.",
        ),
        (
            "fixture://package.md",
            "The package guide builds wheels, verifies hashes, and installs from an offline wheelhouse.",
        ),
    )
    for uri, text in records:
        builder.ingest_record(
            InputRecord(
                text=text,
                source_uri=uri,
                source_kind="fixture",
                license_name="fixture",
            )
        )
    builder.finalize()
    return root / "catalog" / "catalog.sqlite3"


def build_receipt() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(condition), "detail": detail})

    with TemporaryDirectory(prefix="scbe-e92-") as temporary:
        database = _fixture(Path(temporary))
        fallback_query = "survivors remain exact"
        lexical = search_goal(
            database,
            fallback_query,
            limit=8,
            ablate_views=[view for view in VIEW_NAMES if view != "lexical"],
        )
        fallback = search_late_output_fused(database, fallback_query, limit=8)
        lexical_ids = [row["section_id"] for row in lexical["results"]]
        fallback_ids = [row["section_id"] for row in fallback["results"]]
        lexical_scores = [float(row["score"]) for row in lexical["results"]]
        fallback_scores = [float(row["score"]) for row in fallback["results"]]
        check("fallback_core_pass", fallback["route_action"] == "CORE_PASS", fallback["route_action"])
        check("fallback_order_exact", fallback_ids == lexical_ids, len(fallback_ids))
        check("fallback_scores_exact", fallback_scores == lexical_scores, len(fallback_scores))
        check(
            "fallback_has_no_auxiliary_child",
            fallback["child_search_ids"]["auxiliary"] is None,
            fallback["child_search_ids"],
        )

        specialist_query = "Why does this prime sieve code preserve a composite factor?"
        specialist = search_late_output_fused(database, specialist_query, limit=8)
        repeated = search_late_output_fused(database, specialist_query, limit=8)
        null = search_late_output_fused(
            database,
            specialist_query,
            limit=8,
            null_control=True,
        )
        shuffled = search_late_output_fused(
            database,
            specialist_query,
            limit=8,
            control="shuffled",
            control_seed=17,
        )
        check("specialist_selected", specialist["route_action"] == "SPECIALIST", specialist["route_action"])
        check(
            "specialist_views_bounded",
            specialist["auxiliary_views"] == ["prime", "five_w"],
            specialist["auxiliary_views"],
        )
        check("receipt_deterministic", specialist == repeated, specialist["search_id"])
        check("fixed_rrf_constant", specialist["rrf_k"] == LATE_OUTPUT_FUSION_K == 60.0, specialist["rrf_k"])
        check("null_uses_rotated_views", null["auxiliary_views"] == ["source", "speech"], null["auxiliary_views"])
        check("shuffled_identity_changes", shuffled["search_id"] != specialist["search_id"], shuffled["search_id"])
        check(
            "shuffled_cardinality_preserved",
            len(shuffled["results"]) == len(specialist["results"]),
            len(shuffled["results"]),
        )
        rank_errors = []
        for row in specialist["results"]:
            component = row["late_output_fusion"]
            expected = float(component["lexical_contribution"]) + float(component["auxiliary_contribution"])
            if abs(float(component["fusion_score"]) - expected) > 1e-15:
                rank_errors.append(row["section_id"])
            if abs(float(row["score"]) - expected) > 1e-15:
                rank_errors.append(row["section_id"])
            if row["probability"] is not None:
                rank_errors.append(row["section_id"])
        check("rank_contributions_recomputed", not rank_errors, sorted(set(rank_errors)))

    errors = [item["name"] for item in checks if not item["passed"]]
    payload = {
        "schema": "scbe.late-output-fusion-mechanics.v1",
        "status": "MECHANICS_PASS_NO_PROSPECTIVE_ACCESS_NO_PROMOTION" if not errors else "MECHANICS_FAIL",
        "algorithm_revision": LATE_OUTPUT_FUSION_REVISION,
        "rrf_k": LATE_OUTPUT_FUSION_K,
        "catalog_kind": "ephemeral_synthetic_fixture",
        "prospective_catalog_accessed": False,
        "prospective_queries_accessed": False,
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
        "source_hashes": {
            "catalog": sha256_file(ROOT / "python" / "scbe" / "prime_token_catalog.py"),
            "benchmark": sha256_file(ROOT / "python" / "scbe" / "prime_token_benchmark.py"),
            "verifier": sha256_file(Path(__file__).resolve()),
        },
        "check_count": len(checks),
        "checks": checks,
        "errors": errors,
        "claim_boundary": (
            "This receipt proves deterministic mechanics on synthetic records only. "
            "It is not prospective retrieval, learned capability, serving, or promotion evidence."
        ),
    }
    payload["canonical_sha256"] = _canonical_sha256(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    receipt = build_receipt()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: receipt[key] for key in ("status", "check_count", "errors", "canonical_sha256")},
            indent=2,
        )
    )
    return 0 if not receipt["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
