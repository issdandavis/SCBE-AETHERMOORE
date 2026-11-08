"""Source-record-disjoint evaluation for the six-view prime token catalog."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
from statistics import mean, stdev
from typing import Any

from python.scbe.prime_token_catalog import (
    ALGORITHM_REVISION,
    EXPLICIT_ROUTE_REVISION,
    LATE_OUTPUT_FUSION_REVISION,
    LEXICAL_BAND_REVISION,
    LEXICAL_FIRST_REVISION,
    VIEW_NAMES,
    WORD_RE,
    normalize_word,
    search_goal,
    search_explicit_routed,
    search_late_output_fused,
    search_lexical_banded,
    search_lexical_first,
    sha256_file,
)

BENCHMARK_SCHEMA = "scbe.prime-token-benchmark.v1"
RESULT_SCHEMA = "scbe.prime-token-benchmark-result.v1"
CASCADE_RESULT_SCHEMA = "scbe.prime-token-cascade-benchmark-result.v1"
DISJOINT_AUDIT_SCHEMA = "scbe.prime-token-disjoint-audit.v1"
ROUTE_EVIDENCE_SCHEMA = "scbe.prime-token-route-evidence.v1"
MIN_CAPABILITY_QUERIES = 30
ARMS: dict[str, dict[str, Any]] = {
    "full": {"control": "aligned", "ablate_views": []},
    "lexical_only": {
        "control": "aligned",
        "ablate_views": [view for view in VIEW_NAMES if view != "lexical"],
    },
    "no_intervention": {
        "control": "aligned",
        "ablate_views": ["five_w", "prime", "source"],
    },
    "no_five_w": {"control": "aligned", "ablate_views": ["five_w"]},
    "no_prime": {"control": "aligned", "ablate_views": ["prime"]},
    "no_source": {"control": "aligned", "ablate_views": ["source"]},
    "no_atomic": {"control": "aligned", "ablate_views": ["atomic"]},
    "no_speech": {"control": "aligned", "ablate_views": ["speech"]},
    "no_topology": {"control": "aligned", "ablate_views": [], "topology_steps": 0},
    "shuffled_binding": {"control": "shuffled", "ablate_views": []},
}


def _normal_path(value: str) -> str:
    return value.replace("\\", "/").casefold()


def _aware_timestamp(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is missing a timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} has an invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} timestamp must include a timezone")
    return parsed


def load_benchmark(path: str | Path) -> tuple[dict[str, Any], str]:
    benchmark_path = Path(path).resolve()
    raw = benchmark_path.read_bytes()
    payload = json.loads(raw)
    if payload.get("schema") != BENCHMARK_SCHEMA:
        raise ValueError("unknown benchmark schema")
    queries = payload.get("queries")
    if not isinstance(queries, list) or not queries:
        raise ValueError("benchmark requires a nonempty queries list")
    return payload, sha256(raw).hexdigest()


def _sequence_sha256(words: Sequence[str]) -> str:
    digest = sha256()
    for word in words:
        digest.update(word.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _query_token_sha256(text: str) -> str:
    return _sequence_sha256(
        [normalize_word(match.group(0)) for match in WORD_RE.finditer(text)]
    )


def _grouped_token_hashes(
    connection: sqlite3.Connection,
    *,
    key_column: str,
) -> set[str]:
    hashes: set[str] = set()
    current_key: str | None = None
    digest = sha256()
    query = f"""
        SELECT o.{key_column}, t.normalized
        FROM occurrences o JOIN tokens t ON t.token_id = o.token_id
        ORDER BY o.{key_column}, o.global_ordinal
    """
    for raw_key, raw_word in connection.execute(query):
        key = str(raw_key)
        if current_key is not None and key != current_key:
            hashes.add(digest.hexdigest())
            digest = sha256()
        current_key = key
        digest.update(str(raw_word).encode("utf-8"))
        digest.update(b"\0")
    if current_key is not None:
        hashes.add(digest.hexdigest())
    return hashes


def _catalog_identity(database: Path) -> dict[str, Any]:
    if not database.is_file():
        raise FileNotFoundError(database)
    connection = sqlite3.connect(database)
    try:
        source_rows = list(
            connection.execute(
                "SELECT source_uri, content_sha256 FROM sources ORDER BY source_uri"
            )
        )
        return {
            "source_uris": [str(row[0]) for row in source_rows],
            "source_content_sha256": {str(row[1]) for row in source_rows},
            "section_text_sha256": {
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT text_sha256 FROM sections"
                )
            },
            "source_token_sha256": _grouped_token_hashes(
                connection, key_column="source_id"
            ),
            "section_token_sha256": _grouped_token_hashes(
                connection, key_column="section_id"
            ),
        }
    finally:
        connection.close()


def _inspect_queries(
    database: Path, benchmark: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    prospective_boundary = benchmark.get("prospective_boundary")
    prospective_cutoff = None
    if prospective_boundary is not None:
        if not isinstance(prospective_boundary, Mapping):
            raise ValueError("prospective boundary must be an object")
        boundary_catalog_hash = str(
            prospective_boundary.get("catalog_sha256") or ""
        ).strip()
        if boundary_catalog_hash != sha256_file(database):
            raise ValueError("prospective benchmark targets a different catalog hash")
        prospective_cutoff = _aware_timestamp(
            prospective_boundary.get("catalog_generated_at_utc"),
            label="prospective catalog boundary",
        )
    identity = _catalog_identity(database)
    sources = identity["source_uris"]
    source_keys = {_normal_path(source) for source in sources}
    ids: set[str] = set()
    query_sources: set[str] = set()
    validated: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    for index, raw in enumerate(benchmark["queries"]):
        if not isinstance(raw, dict):
            raise ValueError(f"query {index} must be an object")
        query_id = str(raw.get("id") or "").strip()
        text = str(raw.get("query") or "").strip()
        query_source = str(raw.get("query_source_uri") or "").strip()
        authored_at = str(raw.get("authored_at_utc") or "").strip()
        suffix = _normal_path(str(raw.get("relevant_source_suffix") or "").strip())
        if not query_id or query_id in ids:
            raise ValueError(f"query {index} has a missing or duplicate id")
        if not text or not query_source or not suffix:
            raise ValueError(
                f"query {query_id} is missing text, query source, or relevance label"
            )
        if query_source in query_sources:
            raise ValueError(f"query source must be unique per record: {query_id}")
        if prospective_cutoff is not None:
            query_authored_at = _aware_timestamp(
                authored_at, label=f"prospective query {query_id}"
            )
            if query_authored_at <= prospective_cutoff:
                raise ValueError(
                    f"prospective query is not strictly after catalog freeze: {query_id}"
                )
        query_sha256 = sha256(text.encode("utf-8")).hexdigest()
        declared_query_sha256 = str(raw.get("query_sha256") or "").strip()
        if declared_query_sha256 and declared_query_sha256 != query_sha256:
            raise ValueError(f"query text hash mismatch: {query_id}")
        query_token_sha256 = _query_token_sha256(text)
        reasons = []
        if _normal_path(query_source) in source_keys:
            reasons.append("query_source_uri")
        if query_sha256 in identity["source_content_sha256"]:
            reasons.append("source_content_sha256")
        if query_sha256 in identity["section_text_sha256"]:
            reasons.append("section_text_sha256")
        if query_token_sha256 in identity["source_token_sha256"]:
            reasons.append("source_token_sha256")
        if query_token_sha256 in identity["section_token_sha256"]:
            reasons.append("section_token_sha256")
        if reasons:
            collisions.append(
                {
                    "query_id": query_id,
                    "query_sha256": query_sha256,
                    "reasons": reasons,
                }
            )
        matches = [
            source for source in sources if _normal_path(source).endswith(suffix)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"query {query_id} relevance suffix matched {len(matches)} catalog sources"
            )
        review = raw.get("review")
        review_stratum = (
            str(review.get("review_stratum") or "").strip()
            if isinstance(review, Mapping)
            else ""
        )
        ids.add(query_id)
        query_sources.add(query_source)
        validated.append(
            {
                "id": query_id,
                "query": text,
                "query_sha256": query_sha256,
                "query_source_uri": query_source,
                "authored_at_utc": authored_at or None,
                "relevant_source_uri": matches[0],
                "review_stratum": review_stratum,
            }
        )
    counts = {
        "catalog_sources": len(identity["source_uris"]),
        "distinct_source_content_hashes": len(identity["source_content_sha256"]),
        "distinct_section_text_hashes": len(identity["section_text_sha256"]),
        "distinct_source_token_hashes": len(identity["source_token_sha256"]),
        "distinct_section_token_hashes": len(identity["section_token_sha256"]),
    }
    return validated, collisions, counts


def _validate_queries(
    database: Path, benchmark: Mapping[str, Any]
) -> list[dict[str, Any]]:
    validated, collisions, _ = _inspect_queries(database, benchmark)
    if collisions:
        query_ids = ", ".join(row["query_id"] for row in collisions[:3])
        remainder = len(collisions) - min(len(collisions), 3)
        suffix = f" (+{remainder} more)" if remainder else ""
        raise ValueError(
            f"query text or source entered the retrieval catalog: {query_ids}{suffix}"
        )
    return validated


def audit_benchmark_disjointness(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
) -> dict[str, Any]:
    """Audit exact and normalized query/catalog identity without running retrieval."""
    database_path = Path(database).resolve()
    validated, collisions, catalog_counts = _inspect_queries(database_path, benchmark)
    return {
        "schema": DISJOINT_AUDIT_SCHEMA,
        "status": (
            "EXACT_LEAKAGE_DETECTED" if collisions else "NO_EXACT_LEAKAGE_DETECTED"
        ),
        "catalog": str(database_path),
        "catalog_sha256": sha256_file(database_path),
        "benchmark_sha256": benchmark_sha256,
        "query_count": len(validated),
        "collision_count": len(collisions),
        "collisions": collisions,
        "catalog_counts": catalog_counts,
        "checks": [
            "query_source_uri",
            "source_content_sha256",
            "section_text_sha256",
            "source_token_sha256",
            "section_token_sha256",
        ],
        "claim_boundary": (
            "This receipt checks exact URI, byte-hash, and normalized token-stream identity only. "
            "It does not establish prospective authorship, semantic independence, retrieval capability, "
            "or permission to promote a probability table, deployment, tokenizer, or neural weight."
        ),
    }


def _sign_trit(value: float, *, epsilon: float = 1e-15) -> int:
    """Project a signed scalar to {-1, 0, +1} without hiding the scalar."""
    if value > epsilon:
        return 1
    if value < -epsilon:
        return -1
    return 0


def build_late_output_route_evidence(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
    control_seeds: Sequence[int] = (11, 29, 47),
    limit: int = 20,
) -> dict[str, Any]:
    """Build an offline, rank-only route receipt with aligned/shuffled evidence.

    Trits are derived telemetry only. Every trit is emitted beside the raw
    ranks, reciprocal-rank contributions, and signed deltas that produced it.
    This function does not change routing, model state, or serving defaults.
    """
    database_path = Path(database).resolve()
    seeds = tuple(int(seed) for seed in control_seeds)
    if len(set(seeds)) < 3:
        raise ValueError("at least three distinct control seeds are required")
    if limit < 5:
        raise ValueError("limit must be at least 5")
    catalog_hash = sha256_file(database_path)
    audit = audit_benchmark_disjointness(
        database_path,
        benchmark,
        benchmark_sha256=benchmark_sha256,
    )
    if audit["collision_count"]:
        raise ValueError("route evidence requires an exact-source-disjoint benchmark")
    queries = _validate_queries(database_path, benchmark)
    winner_counts = {
        "lexical": 0,
        "auxiliary": 0,
        "tie": 0,
        "lexical_only": 0,
    }
    trit_counts = {
        "primary": {"-1": 0, "0": 0, "1": 0},
        "mirror": {"-1": 0, "0": 0, "1": 0},
    }
    route_usage: dict[str, int] = {}
    no_marker_queries = 0
    no_marker_exact_identity = 0
    query_receipts = []
    missing_rank = limit + 1

    for query in queries:
        aligned = search_late_output_fused(
            database_path,
            query["query"],
            limit=limit,
            expected_catalog_sha256=catalog_hash,
        )
        lexical = search_goal(
            database_path,
            query["query"],
            limit=limit,
            ablate_views=[view for view in VIEW_NAMES if view != "lexical"],
            expected_catalog_sha256=catalog_hash,
        )
        shuffled = [
            search_late_output_fused(
                database_path,
                query["query"],
                limit=limit,
                control="shuffled",
                control_seed=seed,
                expected_catalog_sha256=catalog_hash,
            )
            for seed in seeds
        ]
        selected_views = list(aligned["auxiliary_views"])
        route_key = "+".join(selected_views) or "lexical_only"
        route_usage[route_key] = route_usage.get(route_key, 0) + 1
        lexical_identity = [row["section_id"] for row in aligned["results"]] == [
            row["section_id"] for row in lexical["results"]
        ] and [row["score"] for row in aligned["results"]] == [
            row["score"] for row in lexical["results"]
        ]
        if not selected_views:
            no_marker_queries += 1
            no_marker_exact_identity += int(lexical_identity)

        shuffled_rank_maps = [
            {
                row["section_id"]: rank
                for rank, row in enumerate(receipt["results"], start=1)
            }
            for receipt in shuffled
        ]
        rows = []
        for aligned_rank, row in enumerate(aligned["results"], start=1):
            fusion = row["late_output_fusion"]
            lexical_contribution = float(fusion["lexical_contribution"])
            auxiliary_contribution = float(fusion["auxiliary_contribution"])
            if not selected_views:
                winner = "lexical_only"
            elif lexical_contribution > auxiliary_contribution:
                winner = "lexical"
            elif auxiliary_contribution > lexical_contribution:
                winner = "auxiliary"
            else:
                winner = "tie"
            winner_counts[winner] += 1
            primary_value = auxiliary_contribution - lexical_contribution
            primary_trit = _sign_trit(primary_value)
            rank_deltas = []
            shuffled_rows = []
            for seed, rank_map in zip(seeds, shuffled_rank_maps, strict=True):
                shuffled_rank = rank_map.get(row["section_id"])
                delta = (
                    shuffled_rank if shuffled_rank is not None else missing_rank
                ) - aligned_rank
                rank_deltas.append(float(delta))
                shuffled_rows.append(
                    {
                        "control_seed": seed,
                        "aligned_output_rank": aligned_rank,
                        "shuffled_output_rank": shuffled_rank,
                        "missing_rank_sentinel": missing_rank,
                        "aligned_advantage_rank_delta": delta,
                    }
                )
            mirror_value = mean(rank_deltas)
            mirror_trit = _sign_trit(mirror_value)
            trit_counts["primary"][str(primary_trit)] += 1
            trit_counts["mirror"][str(mirror_trit)] += 1
            rows.append(
                {
                    "section_id": row["section_id"],
                    "source_uri": row["source_uri"],
                    "aligned_output_rank": aligned_rank,
                    "lexical_rank": fusion["lexical_rank"],
                    "auxiliary_rank": fusion["auxiliary_rank"],
                    "lexical_contribution": lexical_contribution,
                    "auxiliary_contribution": auxiliary_contribution,
                    "fusion_score": float(fusion["fusion_score"]),
                    "winner": winner,
                    "primary_signed_value": primary_value,
                    "primary_trit": primary_trit,
                    "aligned_vs_shuffled": shuffled_rows,
                    "mirror_signed_value": mirror_value,
                    "mirror_trit": mirror_trit,
                }
            )

        aligned_relevant_rank = _rank(aligned["results"], query["relevant_source_uri"])
        lexical_relevant_rank = _rank(lexical["results"], query["relevant_source_uri"])
        shuffled_relevant_ranks = [
            _rank(receipt["results"], query["relevant_source_uri"])
            for receipt in shuffled
        ]
        query_receipts.append(
            {
                "query_id": query["id"],
                "query_sha256": query["query_sha256"],
                "query_source_uri": query["query_source_uri"],
                "review_stratum": query["review_stratum"],
                "relevant_source_uri": query["relevant_source_uri"],
                "route_action": aligned["route_action"],
                "selected_views": selected_views,
                "aligned_search_id": aligned["search_id"],
                "lexical_search_id": lexical["search_id"],
                "shuffled_search_ids": [receipt["search_id"] for receipt in shuffled],
                "no_marker_exact_lexical_identity": (
                    lexical_identity if not selected_views else None
                ),
                "relevant_source_ranks": {
                    "aligned": aligned_relevant_rank,
                    "lexical_only": lexical_relevant_rank,
                    "shuffled": [
                        {"control_seed": seed, "rank": rank}
                        for seed, rank in zip(
                            seeds, shuffled_relevant_ranks, strict=True
                        )
                    ],
                },
                "rows": rows,
            }
        )

    final_catalog_hash = sha256_file(database_path)
    if final_catalog_hash != catalog_hash:
        raise RuntimeError("catalog changed during route evidence collection")
    return {
        "schema": ROUTE_EVIDENCE_SCHEMA,
        "status": "EVIDENCE_ONLY_NO_PROMOTION",
        "catalog": str(database_path),
        "catalog_sha256": catalog_hash,
        "benchmark_sha256": benchmark_sha256,
        "query_count": len(queries),
        "control_seeds": list(seeds),
        "result_limit": limit,
        "disjointness_audit": audit,
        "route_usage": dict(sorted(route_usage.items())),
        "winner_counts": winner_counts,
        "tie_count": winner_counts["tie"],
        "trit_counts": trit_counts,
        "no_marker_identity": {
            "queries": no_marker_queries,
            "exact": no_marker_exact_identity,
            "passes": no_marker_queries == no_marker_exact_identity,
        },
        "queries": query_receipts,
        "promotion": "NONE",
        "claim_boundary": (
            "This is offline rank telemetry. Trits are lossy projections with raw evidence retained; "
            "they do not authorize governance actions or change probabilities, hidden states, tokenizers, "
            "model weights, serving pointers, package defaults, or deployments."
        ),
    }


def _rank(results: Sequence[Mapping[str, Any]], relevant_source: str) -> int | None:
    for rank, result in enumerate(results, 1):
        if _normal_path(str(result["source_uri"])) == _normal_path(relevant_source):
            return rank
    return None


def _metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    count = len(rows)
    reciprocal = [
        0.0 if row["rank"] is None else 1.0 / int(row["rank"]) for row in rows
    ]
    return {
        "queries": count,
        "mrr": mean(reciprocal) if reciprocal else 0.0,
        "recall_at_1": sum(row["rank"] == 1 for row in rows) / count if count else 0.0,
        "recall_at_5": (
            sum(row["rank"] is not None and int(row["rank"]) <= 5 for row in rows)
            / count
            if count
            else 0.0
        ),
        "missed_within_limit": sum(row["rank"] is None for row in rows),
    }


def _macro_source_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        source = str(row["relevant_source_uri"])
        grouped.setdefault(source, []).append(float(row["reciprocal_rank"]))
    by_source = {
        source: {"queries": len(values), "mrr": mean(values)}
        for source, values in sorted(grouped.items())
    }
    return {
        "sources": len(by_source),
        "macro_mrr": (
            mean(value["mrr"] for value in by_source.values()) if by_source else 0.0
        ),
        "by_source": by_source,
    }


def _paired_gate(
    candidate: Sequence[float], control: Sequence[float]
) -> dict[str, Any]:
    if len(candidate) != len(control) or not candidate:
        raise ValueError("paired gate requires nonempty equal-length samples")
    differences = [left - right for left, right in zip(candidate, control, strict=True)]
    difference_mean = mean(differences)
    pooled_sd = math.sqrt(
        (
            (stdev(candidate) ** 2 if len(candidate) > 1 else 0.0)
            + (stdev(control) ** 2 if len(control) > 1 else 0.0)
        )
        / 2.0
    )
    threshold = 2.0 * pooled_sd
    return {
        "mean_difference": difference_mean,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": threshold,
        "passes_two_pooled_sd": difference_mean > threshold,
    }


def evaluate_catalog(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
    control_seeds: Sequence[int] = (0, 1, 2),
    limit: int = 20,
) -> dict[str, Any]:
    """Evaluate retrieval while keeping relevance labels outside query features."""
    database_path = Path(database).resolve()
    if len(set(control_seeds)) < 3:
        raise ValueError("at least three distinct control seeds are required")
    if limit < 5:
        raise ValueError("limit must be at least 5")
    queries = _validate_queries(database_path, benchmark)
    arm_runs: dict[str, list[dict[str, Any]]] = {}
    for arm_name, config in ARMS.items():
        runs = []
        seeds = control_seeds if config["control"] == "shuffled" else (0,)
        for seed in seeds:
            outcomes = []
            control_offset = 0
            for query in queries:
                receipt = search_goal(
                    database_path,
                    query["query"],
                    limit=limit,
                    topology_steps=int(config.get("topology_steps", 2)),
                    ablate_views=config["ablate_views"],
                    control=config["control"],
                    control_seed=seed,
                )
                control_offset = int(receipt["control_offset"])
                rank = _rank(receipt["results"], query["relevant_source_uri"])
                outcomes.append(
                    {
                        "query_id": query["id"],
                        "query_source_uri": query["query_source_uri"],
                        "relevant_source_uri": query["relevant_source_uri"],
                        "rank": rank,
                        "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
                        "search_id": receipt["search_id"],
                    }
                )
            runs.append(
                {
                    "control_seed": seed,
                    "control_offset": control_offset,
                    "metrics": _metrics(outcomes),
                    "outcomes": outcomes,
                }
            )
        arm_runs[arm_name] = runs

    full_rr = [float(row["reciprocal_rank"]) for row in arm_runs["full"][0]["outcomes"]]
    gates: dict[str, Any] = {}
    for control_name in ("lexical_only", "no_intervention"):
        control_rr = [
            float(row["reciprocal_rank"])
            for row in arm_runs[control_name][0]["outcomes"]
        ]
        gates[control_name] = _paired_gate(full_rr, control_rr)
    shuffled_rr = []
    full_repeated = []
    for run in arm_runs["shuffled_binding"]:
        shuffled_rr.extend(float(row["reciprocal_rank"]) for row in run["outcomes"])
        full_repeated.extend(full_rr)
    gates["shuffled_binding"] = _paired_gate(full_repeated, shuffled_rr)
    underpowered_reasons = []
    if len(queries) < MIN_CAPABILITY_QUERIES:
        underpowered_reasons.append(
            f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
        )
    if benchmark.get("query_provenance") != "independent_external":
        underpowered_reasons.append(
            "queries are curated paraphrases rather than independent external requests"
        )
    all_gates_pass = all(gate["passes_two_pooled_sd"] for gate in gates.values())
    status = (
        "UNDERPOWERED"
        if underpowered_reasons
        else ("CANDIDATE_PASS" if all_gates_pass else "NO_GAIN")
    )
    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "catalog": str(database_path),
        "catalog_sha256": sha256_file(database_path),
        "benchmark_sha256": benchmark_sha256,
        "algorithm_revision": ALGORITHM_REVISION,
        "query_count": len(queries),
        "query_provenance": benchmark.get("query_provenance", "UNKNOWN"),
        "control_seeds": list(control_seeds),
        "result_limit": limit,
        "arms": arm_runs,
        "gates": gates,
        "underpowered_reasons": underpowered_reasons,
        "claim_boundary": (
            "Source records and relevance labels are disjoint from the catalog query features. "
            "This receipt is not evidence of learned model capability or weight promotion."
        ),
    }


def evaluate_lexical_first_catalog(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
    control_seeds: Sequence[int] = (0, 1, 2),
    limit: int = 20,
) -> dict[str, Any]:
    """Evaluate the frozen lexical-primary, auxiliary-tiebreak cascade."""
    database_path = Path(database).resolve()
    if len(set(control_seeds)) < 3:
        raise ValueError("at least three distinct control seeds are required")
    if limit < 5:
        raise ValueError("limit must be at least 5")
    queries = _validate_queries(database_path, benchmark)
    arm_runs: dict[str, list[dict[str, Any]]] = {}
    configs = {
        "lexical_first": ("cascade", "aligned", (0,)),
        "full": ("goal", "aligned", (0,)),
        "lexical_only": ("lexical", "aligned", (0,)),
        "no_intervention": ("no_intervention", "aligned", (0,)),
        "shuffled_binding": ("cascade", "shuffled", tuple(control_seeds)),
    }
    for arm_name, (mode, control, seeds) in configs.items():
        runs = []
        for seed in seeds:
            outcomes = []
            control_offset = 0
            for query in queries:
                if mode == "cascade":
                    receipt = search_lexical_first(
                        database_path,
                        query["query"],
                        limit=limit,
                        control=control,
                        control_seed=seed,
                    )
                else:
                    ablations: Sequence[str] = ()
                    if mode == "lexical":
                        ablations = [view for view in VIEW_NAMES if view != "lexical"]
                    elif mode == "no_intervention":
                        ablations = ("five_w", "prime", "source")
                    receipt = search_goal(
                        database_path,
                        query["query"],
                        limit=limit,
                        ablate_views=ablations,
                    )
                control_offset = int(receipt["control_offset"])
                rank = _rank(receipt["results"], query["relevant_source_uri"])
                outcomes.append(
                    {
                        "query_id": query["id"],
                        "query_source_uri": query["query_source_uri"],
                        "relevant_source_uri": query["relevant_source_uri"],
                        "rank": rank,
                        "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
                        "search_id": receipt["search_id"],
                    }
                )
            runs.append(
                {
                    "control_seed": seed,
                    "control_offset": control_offset,
                    "metrics": _metrics(outcomes),
                    "outcomes": outcomes,
                }
            )
        arm_runs[arm_name] = runs

    candidate_rr = [
        float(row["reciprocal_rank"])
        for row in arm_runs["lexical_first"][0]["outcomes"]
    ]
    gates: dict[str, Any] = {}
    for control_name in ("lexical_only", "no_intervention"):
        control_rr = [
            float(row["reciprocal_rank"])
            for row in arm_runs[control_name][0]["outcomes"]
        ]
        gates[control_name] = _paired_gate(candidate_rr, control_rr)
    shuffled_rr = []
    candidate_repeated = []
    for run in arm_runs["shuffled_binding"]:
        shuffled_rr.extend(float(row["reciprocal_rank"]) for row in run["outcomes"])
        candidate_repeated.extend(candidate_rr)
    gates["shuffled_binding"] = _paired_gate(candidate_repeated, shuffled_rr)
    underpowered_reasons = []
    if len(queries) < MIN_CAPABILITY_QUERIES:
        underpowered_reasons.append(
            f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
        )
    if benchmark.get("query_provenance") != "independent_external":
        underpowered_reasons.append(
            "queries are curated paraphrases rather than independent external requests"
        )
    all_gates_pass = all(gate["passes_two_pooled_sd"] for gate in gates.values())
    status = (
        "UNDERPOWERED"
        if underpowered_reasons
        else ("CANDIDATE_PASS" if all_gates_pass else "NO_GAIN")
    )
    return {
        "schema": CASCADE_RESULT_SCHEMA,
        "status": status,
        "candidate_arm": "lexical_first",
        "catalog": str(database_path),
        "catalog_sha256": sha256_file(database_path),
        "benchmark_sha256": benchmark_sha256,
        "algorithm_revision": LEXICAL_FIRST_REVISION,
        "query_count": len(queries),
        "query_provenance": benchmark.get("query_provenance", "UNKNOWN"),
        "control_seeds": list(control_seeds),
        "result_limit": limit,
        "arms": arm_runs,
        "gates": gates,
        "underpowered_reasons": underpowered_reasons,
        "claim_boundary": (
            "The candidate is a deterministic retrieval cascade, not learned model capability. "
            "No probability table, serving pointer, tokenizer, or neural weight is promoted."
        ),
    }


def evaluate_lexical_banded_catalog(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
    lexical_band_width: float,
    control_seeds: Sequence[int] = (0, 1, 2),
    limit: int = 20,
) -> dict[str, Any]:
    """Evaluate one frozen lexical-band width against explicit controls."""
    database_path = Path(database).resolve()
    if len(set(control_seeds)) < 3:
        raise ValueError("at least three distinct control seeds are required")
    if limit < 5:
        raise ValueError("limit must be at least 5")
    if not 0.0 <= lexical_band_width <= 1.0:
        raise ValueError("lexical_band_width must be between 0 and 1")
    queries = _validate_queries(database_path, benchmark)
    arm_runs: dict[str, list[dict[str, Any]]] = {}
    configs = {
        "lexical_banded": ("cascade", "aligned", (0,)),
        "full": ("goal", "aligned", (0,)),
        "lexical_only": ("lexical", "aligned", (0,)),
        "no_intervention": ("no_intervention", "aligned", (0,)),
        "shuffled_binding": ("cascade", "shuffled", tuple(control_seeds)),
    }
    for arm_name, (mode, control, seeds) in configs.items():
        runs = []
        for seed in seeds:
            outcomes = []
            control_offset = 0
            for query in queries:
                if mode == "cascade":
                    receipt = search_lexical_banded(
                        database_path,
                        query["query"],
                        lexical_band_width=lexical_band_width,
                        limit=limit,
                        control=control,
                        control_seed=seed,
                    )
                else:
                    ablations: Sequence[str] = ()
                    if mode == "lexical":
                        ablations = [view for view in VIEW_NAMES if view != "lexical"]
                    elif mode == "no_intervention":
                        ablations = ("five_w", "prime", "source")
                    receipt = search_goal(
                        database_path,
                        query["query"],
                        limit=limit,
                        ablate_views=ablations,
                    )
                control_offset = int(receipt["control_offset"])
                rank = _rank(receipt["results"], query["relevant_source_uri"])
                outcomes.append(
                    {
                        "query_id": query["id"],
                        "query_source_uri": query["query_source_uri"],
                        "relevant_source_uri": query["relevant_source_uri"],
                        "rank": rank,
                        "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
                        "search_id": receipt["search_id"],
                    }
                )
            runs.append(
                {
                    "control_seed": seed,
                    "control_offset": control_offset,
                    "metrics": _metrics(outcomes),
                    "outcomes": outcomes,
                }
            )
        arm_runs[arm_name] = runs

    candidate_rr = [
        float(row["reciprocal_rank"])
        for row in arm_runs["lexical_banded"][0]["outcomes"]
    ]
    lexical_rr = [
        float(row["reciprocal_rank"]) for row in arm_runs["lexical_only"][0]["outcomes"]
    ]
    query_differences = [
        candidate - lexical
        for candidate, lexical in zip(candidate_rr, lexical_rr, strict=True)
    ]
    gates: dict[str, Any] = {}
    for control_name in ("lexical_only", "no_intervention"):
        control_rr = [
            float(row["reciprocal_rank"])
            for row in arm_runs[control_name][0]["outcomes"]
        ]
        gates[control_name] = _paired_gate(candidate_rr, control_rr)
    shuffled_rr = []
    candidate_repeated = []
    for run in arm_runs["shuffled_binding"]:
        shuffled_rr.extend(float(row["reciprocal_rank"]) for row in run["outcomes"])
        candidate_repeated.extend(candidate_rr)
    gates["shuffled_binding"] = _paired_gate(candidate_repeated, shuffled_rr)
    underpowered_reasons = []
    if len(queries) < MIN_CAPABILITY_QUERIES:
        underpowered_reasons.append(
            f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
        )
    if benchmark.get("query_provenance") != "independent_external":
        underpowered_reasons.append(
            "queries are curated paraphrases rather than independent external requests"
        )
    all_gates_pass = all(gate["passes_two_pooled_sd"] for gate in gates.values())
    status = (
        "UNDERPOWERED"
        if underpowered_reasons
        else ("CANDIDATE_PASS" if all_gates_pass else "NO_GAIN")
    )
    return {
        "schema": CASCADE_RESULT_SCHEMA,
        "status": status,
        "candidate_arm": "lexical_banded",
        "catalog": str(database_path),
        "catalog_sha256": sha256_file(database_path),
        "benchmark_sha256": benchmark_sha256,
        "algorithm_revision": LEXICAL_BAND_REVISION,
        "lexical_band_width": lexical_band_width,
        "query_count": len(queries),
        "query_provenance": benchmark.get("query_provenance", "UNKNOWN"),
        "control_seeds": list(control_seeds),
        "result_limit": limit,
        "arms": arm_runs,
        "gates": gates,
        "query_changes_vs_lexical": {
            "improved": sum(value > 0 for value in query_differences),
            "harmed": sum(value < 0 for value in query_differences),
            "unchanged": sum(value == 0 for value in query_differences),
        },
        "underpowered_reasons": underpowered_reasons,
        "claim_boundary": (
            "The candidate is a deterministic retrieval cascade, not learned model capability. "
            "No probability table, serving pointer, tokenizer, or neural weight is promoted."
        ),
    }


def evaluate_explicit_routed_catalog(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
    lexical_band_width: float = 0.005,
    control_seeds: Sequence[int] = (11, 29, 47),
    limit: int = 20,
) -> dict[str, Any]:
    """Evaluate the frozen explicit-intent route against every declared control."""
    database_path = Path(database).resolve()
    if len(set(control_seeds)) < 3:
        raise ValueError("at least three distinct control seeds are required")
    if limit < 5:
        raise ValueError("limit must be at least 5")
    if lexical_band_width != 0.005:
        raise ValueError("explicit-route v1 requires frozen lexical band width 0.005")
    queries = _validate_queries(database_path, benchmark)
    configs = {
        "explicit_routed": ("routed", "aligned", (0,), False),
        "route_null": ("routed", "aligned", (0,), True),
        "full": ("goal", "aligned", (0,), False),
        "lexical_banded": ("band", "aligned", (0,), False),
        "lexical_only": ("lexical", "aligned", (0,), False),
        "no_intervention": ("no_intervention", "aligned", (0,), False),
        "shuffled_binding": (
            "routed",
            "shuffled",
            tuple(control_seeds),
            False,
        ),
    }
    arm_runs: dict[str, list[dict[str, Any]]] = {}
    for arm_name, (mode, control, seeds, null_control) in configs.items():
        runs = []
        for seed in seeds:
            outcomes = []
            control_offset = 0
            for query in queries:
                if mode == "routed":
                    receipt = search_explicit_routed(
                        database_path,
                        query["query"],
                        lexical_band_width=lexical_band_width,
                        limit=limit,
                        control=control,
                        control_seed=seed,
                        null_control=null_control,
                    )
                elif mode == "band":
                    receipt = search_lexical_banded(
                        database_path,
                        query["query"],
                        lexical_band_width=lexical_band_width,
                        limit=limit,
                    )
                else:
                    ablations: Sequence[str] = ()
                    if mode == "lexical":
                        ablations = [view for view in VIEW_NAMES if view != "lexical"]
                    elif mode == "no_intervention":
                        ablations = ("five_w", "prime", "source")
                    receipt = search_goal(
                        database_path,
                        query["query"],
                        limit=limit,
                        ablate_views=ablations,
                    )
                control_offset = int(receipt["control_offset"])
                rank = _rank(receipt["results"], query["relevant_source_uri"])
                route = receipt.get("explicit_route", {})
                outcomes.append(
                    {
                        "query_id": query["id"],
                        "query_source_uri": query["query_source_uri"],
                        "review_stratum": query["review_stratum"],
                        "relevant_source_uri": query["relevant_source_uri"],
                        "rank": rank,
                        "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
                        "selected_views": list(route.get("selected_views", [])),
                        "search_id": receipt["search_id"],
                    }
                )
            runs.append(
                {
                    "control_seed": seed,
                    "control_offset": control_offset,
                    "metrics": _metrics(outcomes),
                    "macro_source_metrics": _macro_source_metrics(outcomes),
                    "outcomes": outcomes,
                }
            )
        arm_runs[arm_name] = runs

    candidate_outcomes = arm_runs["explicit_routed"][0]["outcomes"]
    candidate_rr = [float(row["reciprocal_rank"]) for row in candidate_outcomes]
    gates: dict[str, Any] = {}
    for control_name in ("lexical_only", "no_intervention", "route_null"):
        control_rr = [
            float(row["reciprocal_rank"])
            for row in arm_runs[control_name][0]["outcomes"]
        ]
        gates[control_name] = _paired_gate(candidate_rr, control_rr)
    for run in arm_runs["shuffled_binding"]:
        seed = int(run["control_seed"])
        shuffled_rr = [float(row["reciprocal_rank"]) for row in run["outcomes"]]
        gates[f"shuffled_binding_seed_{seed}"] = _paired_gate(
            candidate_rr,
            shuffled_rr,
        )

    lexical_outcomes = arm_runs["lexical_only"][0]["outcomes"]
    candidate_sources = arm_runs["explicit_routed"][0]["macro_source_metrics"]
    lexical_sources = arm_runs["lexical_only"][0]["macro_source_metrics"]
    source_deltas = {
        source: (
            float(candidate_sources["by_source"][source]["mrr"])
            - float(lexical_sources["by_source"][source]["mrr"])
        )
        for source in candidate_sources["by_source"]
    }
    macro_source_gate = {
        "candidate_macro_mrr": float(candidate_sources["macro_mrr"]),
        "lexical_macro_mrr": float(lexical_sources["macro_mrr"]),
        "passes": float(candidate_sources["macro_mrr"])
        > float(lexical_sources["macro_mrr"]),
    }
    source_change_gate = {
        "improved_sources": sum(delta > 0 for delta in source_deltas.values()),
        "harmed_sources": sum(delta < 0 for delta in source_deltas.values()),
        "worst_source_delta": min(source_deltas.values(), default=0.0),
        "per_source_delta": source_deltas,
    }
    source_change_gate["passes"] = (
        source_change_gate["improved_sources"] >= 3
        and source_change_gate["worst_source_delta"] >= -0.05
    )
    query_differences = [
        float(candidate["reciprocal_rank"]) - float(lexical["reciprocal_rank"])
        for candidate, lexical in zip(
            candidate_outcomes,
            lexical_outcomes,
            strict=True,
        )
    ]
    source_counts: dict[str, int] = {}
    for query in queries:
        source = str(query["relevant_source_uri"])
        source_counts[source] = source_counts.get(source, 0) + 1
    strata = sorted(
        {str(query["review_stratum"]) for query in queries if query["review_stratum"]}
    )
    max_source_share = max(source_counts.values(), default=0) / len(queries)
    diversity = {
        "topic_strata": strata,
        "topic_strata_count": len(strata),
        "relevant_source_count": len(source_counts),
        "max_relevant_source_share": max_source_share,
        "relevant_source_query_counts": dict(sorted(source_counts.items())),
    }
    underpowered_reasons = []
    if len(queries) < MIN_CAPABILITY_QUERIES:
        underpowered_reasons.append(
            f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
        )
    if benchmark.get("query_provenance") != "independent_external":
        underpowered_reasons.append(
            "queries are not independently authored external requests"
        )
    if len(strata) < 3:
        underpowered_reasons.append("fewer than three reviewed topic strata")
    if len(source_counts) < 6:
        underpowered_reasons.append("fewer than six distinct relevant catalog sources")
    if max_source_share > 0.4:
        underpowered_reasons.append("one relevant source exceeds the 40-percent cap")
    micro_gates_pass = all(
        bool(gate["passes_two_pooled_sd"]) for gate in gates.values()
    )
    all_gates_pass = (
        micro_gates_pass
        and bool(macro_source_gate["passes"])
        and bool(source_change_gate["passes"])
    )
    status = (
        "UNDERPOWERED"
        if underpowered_reasons
        else ("CANDIDATE_PASS" if all_gates_pass else "NO_GAIN")
    )
    route_usage: dict[str, int] = {}
    for row in candidate_outcomes:
        route_key = "+".join(row["selected_views"]) or "lexical_only"
        route_usage[route_key] = route_usage.get(route_key, 0) + 1
    return {
        "schema": CASCADE_RESULT_SCHEMA,
        "status": status,
        "candidate_arm": "explicit_routed",
        "catalog": str(database_path),
        "catalog_sha256": sha256_file(database_path),
        "benchmark_sha256": benchmark_sha256,
        "algorithm_revision": EXPLICIT_ROUTE_REVISION,
        "lexical_band_width": lexical_band_width,
        "query_count": len(queries),
        "query_provenance": benchmark.get("query_provenance", "UNKNOWN"),
        "control_seeds": list(control_seeds),
        "result_limit": limit,
        "arms": arm_runs,
        "gates": gates,
        "macro_source_gate": macro_source_gate,
        "source_change_gate": source_change_gate,
        "diversity": diversity,
        "route_usage": dict(sorted(route_usage.items())),
        "query_changes_vs_lexical": {
            "improved": sum(value > 0 for value in query_differences),
            "harmed": sum(value < 0 for value in query_differences),
            "unchanged": sum(value == 0 for value in query_differences),
        },
        "underpowered_reasons": underpowered_reasons,
        "claim_boundary": (
            "The explicit route is a deterministic retrieval sidecar. This result cannot promote a "
            "probability table, serving pointer, tokenizer, package default, deployment, or neural weight."
        ),
    }


def evaluate_late_output_fused_catalog(
    database: str | Path,
    benchmark: Mapping[str, Any],
    *,
    benchmark_sha256: str,
    control_seeds: Sequence[int] = (11, 29, 47),
    limit: int = 20,
) -> dict[str, Any]:
    """Evaluate fixed rank-only late fusion against declared controls."""
    database_path = Path(database).resolve()
    if len(set(control_seeds)) < 3:
        raise ValueError("at least three distinct control seeds are required")
    if limit < 5:
        raise ValueError("limit must be at least 5")
    catalog_hash = sha256_file(database_path)
    queries = _validate_queries(database_path, benchmark)
    configs = {
        "late_output_fused": ("late", "aligned", (0,), False),
        "route_null": ("late", "aligned", (0,), True),
        "explicit_routed": ("explicit", "aligned", (0,), False),
        "lexical_only": ("lexical", "aligned", (0,), False),
        "no_intervention": ("no_intervention", "aligned", (0,), False),
        "shuffled_binding": (
            "late",
            "shuffled",
            tuple(control_seeds),
            False,
        ),
    }
    arm_runs: dict[str, list[dict[str, Any]]] = {}
    for arm_name, (mode, control, seeds, null_control) in configs.items():
        runs = []
        for seed in seeds:
            outcomes = []
            control_offset = 0
            for query in queries:
                if mode == "late":
                    receipt = search_late_output_fused(
                        database_path,
                        query["query"],
                        limit=limit,
                        control=control,
                        control_seed=seed,
                        null_control=null_control,
                        expected_catalog_sha256=catalog_hash,
                    )
                elif mode == "explicit":
                    receipt = search_explicit_routed(
                        database_path,
                        query["query"],
                        limit=limit,
                        expected_catalog_sha256=catalog_hash,
                    )
                else:
                    ablations: Sequence[str] = ()
                    if mode == "lexical":
                        ablations = [view for view in VIEW_NAMES if view != "lexical"]
                    elif mode == "no_intervention":
                        ablations = ("five_w", "prime", "source")
                    receipt = search_goal(
                        database_path,
                        query["query"],
                        limit=limit,
                        ablate_views=ablations,
                        expected_catalog_sha256=catalog_hash,
                    )
                control_offset = int(receipt["control_offset"])
                rank = _rank(receipt["results"], query["relevant_source_uri"])
                route = receipt.get("explicit_route", {})
                outcomes.append(
                    {
                        "query_id": query["id"],
                        "query_source_uri": query["query_source_uri"],
                        "review_stratum": query["review_stratum"],
                        "relevant_source_uri": query["relevant_source_uri"],
                        "rank": rank,
                        "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
                        "selected_views": list(route.get("selected_views", [])),
                        "fusion_active": bool(receipt.get("fusion_active", False)),
                        "search_id": receipt["search_id"],
                    }
                )
            runs.append(
                {
                    "control_seed": seed,
                    "control_offset": control_offset,
                    "metrics": _metrics(outcomes),
                    "macro_source_metrics": _macro_source_metrics(outcomes),
                    "outcomes": outcomes,
                }
            )
        arm_runs[arm_name] = runs

    candidate_outcomes = arm_runs["late_output_fused"][0]["outcomes"]
    candidate_rr = [float(row["reciprocal_rank"]) for row in candidate_outcomes]
    gates: dict[str, Any] = {}
    for control_name in ("lexical_only", "no_intervention", "route_null"):
        control_rr = [
            float(row["reciprocal_rank"])
            for row in arm_runs[control_name][0]["outcomes"]
        ]
        gates[control_name] = _paired_gate(candidate_rr, control_rr)
    for run in arm_runs["shuffled_binding"]:
        seed = int(run["control_seed"])
        shuffled_rr = [float(row["reciprocal_rank"]) for row in run["outcomes"]]
        gates[f"shuffled_binding_seed_{seed}"] = _paired_gate(
            candidate_rr,
            shuffled_rr,
        )

    lexical_outcomes = arm_runs["lexical_only"][0]["outcomes"]
    candidate_sources = arm_runs["late_output_fused"][0]["macro_source_metrics"]
    lexical_sources = arm_runs["lexical_only"][0]["macro_source_metrics"]
    source_deltas = {
        source: (
            float(candidate_sources["by_source"][source]["mrr"])
            - float(lexical_sources["by_source"][source]["mrr"])
        )
        for source in candidate_sources["by_source"]
    }
    macro_source_gate = {
        "candidate_macro_mrr": float(candidate_sources["macro_mrr"]),
        "lexical_macro_mrr": float(lexical_sources["macro_mrr"]),
        "passes": float(candidate_sources["macro_mrr"])
        > float(lexical_sources["macro_mrr"]),
    }
    source_change_gate = {
        "improved_sources": sum(delta > 0 for delta in source_deltas.values()),
        "harmed_sources": sum(delta < 0 for delta in source_deltas.values()),
        "worst_source_delta": min(source_deltas.values(), default=0.0),
        "per_source_delta": source_deltas,
    }
    source_change_gate["passes"] = (
        source_change_gate["improved_sources"] >= 3
        and source_change_gate["worst_source_delta"] >= -0.05
    )
    query_differences = [
        float(candidate["reciprocal_rank"]) - float(lexical["reciprocal_rank"])
        for candidate, lexical in zip(
            candidate_outcomes,
            lexical_outcomes,
            strict=True,
        )
    ]
    source_counts: dict[str, int] = {}
    for query in queries:
        source = str(query["relevant_source_uri"])
        source_counts[source] = source_counts.get(source, 0) + 1
    strata = sorted(
        {str(query["review_stratum"]) for query in queries if query["review_stratum"]}
    )
    max_source_share = max(source_counts.values(), default=0) / len(queries)
    diversity = {
        "topic_strata": strata,
        "topic_strata_count": len(strata),
        "relevant_source_count": len(source_counts),
        "max_relevant_source_share": max_source_share,
        "relevant_source_query_counts": dict(sorted(source_counts.items())),
    }
    underpowered_reasons = []
    if len(queries) < MIN_CAPABILITY_QUERIES:
        underpowered_reasons.append(
            f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
        )
    if benchmark.get("query_provenance") != "independent_external":
        underpowered_reasons.append(
            "queries are not independently authored external requests"
        )
    if len(strata) < 3:
        underpowered_reasons.append("fewer than three reviewed topic strata")
    if len(source_counts) < 6:
        underpowered_reasons.append("fewer than six distinct relevant catalog sources")
    if max_source_share > 0.4:
        underpowered_reasons.append("one relevant source exceeds the 40-percent cap")
    micro_gates_pass = all(
        bool(gate["passes_two_pooled_sd"]) for gate in gates.values()
    )
    all_gates_pass = (
        micro_gates_pass
        and bool(macro_source_gate["passes"])
        and bool(source_change_gate["passes"])
    )
    status = (
        "UNDERPOWERED"
        if underpowered_reasons
        else ("CANDIDATE_PASS" if all_gates_pass else "NO_GAIN")
    )
    route_usage: dict[str, int] = {}
    for row in candidate_outcomes:
        route_key = "+".join(row["selected_views"]) or "lexical_only"
        route_usage[route_key] = route_usage.get(route_key, 0) + 1
    final_catalog_hash = sha256_file(database_path)
    if final_catalog_hash != catalog_hash:
        raise RuntimeError("catalog changed during E92 prospective evaluation")
    return {
        "schema": CASCADE_RESULT_SCHEMA,
        "status": status,
        "candidate_arm": "late_output_fused",
        "catalog": str(database_path),
        "catalog_sha256": catalog_hash,
        "benchmark_sha256": benchmark_sha256,
        "algorithm_revision": LATE_OUTPUT_FUSION_REVISION,
        "query_count": len(queries),
        "query_provenance": benchmark.get("query_provenance", "UNKNOWN"),
        "control_seeds": list(control_seeds),
        "result_limit": limit,
        "arms": arm_runs,
        "gates": gates,
        "macro_source_gate": macro_source_gate,
        "source_change_gate": source_change_gate,
        "diversity": diversity,
        "route_usage": dict(sorted(route_usage.items())),
        "query_changes_vs_lexical": {
            "improved": sum(value > 0 for value in query_differences),
            "harmed": sum(value < 0 for value in query_differences),
            "unchanged": sum(value == 0 for value in query_differences),
        },
        "underpowered_reasons": underpowered_reasons,
        "claim_boundary": (
            "Late output fusion is deterministic rank composition, not learned model capability. "
            "No probability table, serving pointer, package default, tokenizer, or neural weight is promoted."
        ),
    }
