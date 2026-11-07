"""Source-record-disjoint evaluation for the six-view prime token catalog."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    LEXICAL_BAND_REVISION,
    LEXICAL_FIRST_REVISION,
    VIEW_NAMES,
    search_goal,
    search_explicit_routed,
    search_lexical_banded,
    search_lexical_first,
    sha256_file,
)

BENCHMARK_SCHEMA = "scbe.prime-token-benchmark.v1"
RESULT_SCHEMA = "scbe.prime-token-benchmark-result.v1"
CASCADE_RESULT_SCHEMA = "scbe.prime-token-cascade-benchmark-result.v1"
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


def _catalog_sources(database: Path) -> list[str]:
    connection = sqlite3.connect(database)
    try:
        return [
            str(row[0])
            for row in connection.execute(
                "SELECT source_uri FROM sources ORDER BY source_uri"
            )
        ]
    finally:
        connection.close()


def _validate_queries(
    database: Path, benchmark: Mapping[str, Any]
) -> list[dict[str, Any]]:
    sources = _catalog_sources(database)
    source_keys = {_normal_path(source) for source in sources}
    ids: set[str] = set()
    query_sources: set[str] = set()
    validated: list[dict[str, str]] = []
    for index, raw in enumerate(benchmark["queries"]):
        if not isinstance(raw, dict):
            raise ValueError(f"query {index} must be an object")
        query_id = str(raw.get("id") or "").strip()
        text = str(raw.get("query") or "").strip()
        query_source = str(raw.get("query_source_uri") or "").strip()
        suffix = _normal_path(str(raw.get("relevant_source_suffix") or "").strip())
        if not query_id or query_id in ids:
            raise ValueError(f"query {index} has a missing or duplicate id")
        if not text or not query_source or not suffix:
            raise ValueError(
                f"query {query_id} is missing text, query source, or relevance label"
            )
        if _normal_path(query_source) in source_keys:
            raise ValueError(f"query source entered the retrieval catalog: {query_id}")
        if query_source in query_sources:
            raise ValueError(f"query source must be unique per record: {query_id}")
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
                "query_source_uri": query_source,
                "relevant_source_uri": matches[0],
                "review_stratum": review_stratum,
            }
        )
    return validated


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
