"""Independent aggregate verifier for a completed E92 prospective bundle."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any

E92_RUN_SCHEMA = "scbe.e92-prospective-run.v2"
BENCHMARK_SCHEMA = "scbe.prime-token-benchmark.v1"
RESULT_SCHEMA = "scbe.prime-token-cascade-benchmark-result.v1"
REVIEW_QUEUE_SCHEMA = "scbe.prime-token-independent-review-queue.v1"
REVIEW_LABEL_SCHEMA = "scbe.prime-token-independent-review-labels.v1"
PREPARATION_SCHEMA = "clay.prime-token-prospective-review-preparation.v1"
SOURCE_INVENTORY_SCHEMA = "clay.prime-token-catalog-source-suffixes.v1"
ALGORITHM_REVISION = "six-view-late-output-fusion-v1"
MIN_CAPABILITY_QUERIES = 30
DEFAULT_CONTROL_SEEDS = (11, 29, 47)
EXPECTED_ARMS = {
    "late_output_fused",
    "route_null",
    "explicit_routed",
    "lexical_only",
    "no_intervention",
    "shuffled_binding",
    "random_rank_fusion",
}
SOURCE_CHAIN_BUNDLE_FILES = {
    "queue": "SOURCE_QUEUE.json",
    "labels": "SOURCE_LABELS.json",
    "preparation_receipt": "SOURCE_PREPARATION_RECEIPT.json",
    "source_inventory": "SOURCE_INVENTORY.json",
}
SOURCE_HASH_FIELDS = {
    "queue": "queue_file_sha256",
    "labels": "labels_file_sha256",
    "preparation_receipt": "preparation_receipt_file_sha256",
    "source_inventory": "source_inventory_file_sha256",
}


def _canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _review_queue_sha256(queue: Mapping[str, Any]) -> str:
    payload = dict(queue)
    payload.pop("queue_sha256", None)
    return _canonical_sha256(payload)


def _load_source_chain(
    root: Path,
    receipt: Mapping[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    declaration = receipt.get("source_chain_bundle")
    if not isinstance(declaration, Mapping) or set(declaration) != set(
        SOURCE_CHAIN_BUNDLE_FILES
    ):
        errors.append("source-chain bundle declaration mismatch")
        return {}
    loaded: dict[str, dict[str, Any]] = {}
    for role, expected_name in SOURCE_CHAIN_BUNDLE_FILES.items():
        item = declaration.get(role)
        if not isinstance(item, Mapping) or set(item) != {
            "file",
            "sha256",
            "source_file_sha256",
        }:
            errors.append(f"source-chain {role} declaration mismatch")
            continue
        if item.get("file") != expected_name:
            errors.append(f"source-chain {role} filename mismatch")
            continue
        path = root / expected_name
        if not path.is_file():
            errors.append(f"source-chain {role} file missing")
            continue
        if _sha256_file(path) != item.get("sha256"):
            errors.append(f"source-chain {role} bundled file hash mismatch")
            continue
        if item.get("source_file_sha256") != receipt.get(SOURCE_HASH_FIELDS[role]):
            errors.append(f"source-chain {role} source file hash mismatch")
        try:
            loaded[role] = _load(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"source-chain {role} JSON invalid: {exc}")
    return loaded


def _verify_source_chain(
    source_chain: Mapping[str, Mapping[str, Any]],
    *,
    benchmark: Mapping[str, Any],
    receipt: Mapping[str, Any],
    errors: list[str],
) -> None:
    if set(source_chain) != set(SOURCE_CHAIN_BUNDLE_FILES):
        return
    queue = source_chain["queue"]
    labels = source_chain["labels"]
    preparation = source_chain["preparation_receipt"]
    source_inventory = source_chain["source_inventory"]

    if queue.get("schema") != REVIEW_QUEUE_SCHEMA:
        errors.append("source queue schema mismatch")
    queue_hash = _review_queue_sha256(queue)
    if queue.get("queue_sha256") != queue_hash:
        errors.append("source queue content hash mismatch")
    if receipt.get("queue_content_sha256") != queue_hash:
        errors.append("run receipt source queue binding mismatch")
    candidates = queue.get("candidates")
    if not isinstance(candidates, list):
        errors.append("source queue candidates missing")
        candidates = []
    if queue.get("candidate_count") != len(candidates):
        errors.append("source queue candidate count mismatch")
    candidate_by_hash: dict[str, Mapping[str, Any]] = {}
    candidate_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            errors.append(f"source queue candidate {index} is not an object")
            continue
        query = str(candidate.get("query") or "")
        query_hash = str(candidate.get("query_sha256") or "")
        candidate_id = str(candidate.get("candidate_id") or "")
        if sha256(query.encode("utf-8")).hexdigest() != query_hash:
            errors.append(f"source queue candidate {index} query hash mismatch")
        if not candidate_id or candidate_id in candidate_ids:
            errors.append(f"source queue candidate {index} identity mismatch")
        if not query_hash or query_hash in candidate_by_hash:
            errors.append(f"source queue candidate {index} query identity mismatch")
        else:
            candidate_by_hash[query_hash] = candidate
        candidate_ids.add(candidate_id)

    boundary = queue.get("prospective_boundary")
    if not isinstance(boundary, Mapping) or boundary.get(
        "catalog_sha256"
    ) != receipt.get("catalog_sha256"):
        errors.append("source queue catalog boundary mismatch")
    if benchmark.get("prospective_boundary") != boundary:
        errors.append("benchmark prospective boundary differs from source queue")
    if benchmark.get("review_scope_sha256") != queue_hash:
        errors.append("benchmark review scope differs from source queue")
    if benchmark.get("source_dataset_sha256") != queue.get("dataset_sha256"):
        errors.append("benchmark dataset hash differs from source queue")

    if source_inventory.get("schema") != SOURCE_INVENTORY_SCHEMA:
        errors.append("source inventory schema mismatch")
    if source_inventory.get("catalog_sha256") != receipt.get("catalog_sha256"):
        errors.append("source inventory catalog binding mismatch")
    source_rows = source_inventory.get("sources")
    if not isinstance(source_rows, list):
        errors.append("source inventory rows missing")
        source_rows = []
    if source_inventory.get("source_count") != len(source_rows):
        errors.append("source inventory count mismatch")
    suffixes = {
        str(row.get("unique_suffix") or "")
        for row in source_rows
        if isinstance(row, Mapping) and row.get("unique_suffix")
    }
    if len(suffixes) != len(source_rows):
        errors.append("source inventory suffixes are incomplete or duplicated")

    if labels.get("schema") != REVIEW_LABEL_SCHEMA:
        errors.append("source labels schema mismatch")
    if labels.get("queue_sha256") != queue_hash:
        errors.append("source labels queue binding mismatch")
    raw_labels = labels.get("labels")
    if not isinstance(raw_labels, list):
        errors.append("source labels missing")
        raw_labels = []
    reviewer = str(labels.get("reviewer") or "")
    reviewed_at = str(labels.get("reviewed_at_utc") or "")
    if not reviewer or not reviewed_at:
        errors.append("source label reviewer identity or time missing")
    expected_queries: list[dict[str, Any]] = []
    used_hashes: set[str] = set()
    for index, label in enumerate(raw_labels):
        if not isinstance(label, Mapping):
            errors.append(f"source label {index} is not an object")
            continue
        query_hash = str(label.get("query_sha256") or "")
        if query_hash not in candidate_by_hash or query_hash in used_hashes:
            errors.append(f"source label {index} query identity mismatch")
            continue
        used_hashes.add(query_hash)
        decision = str(label.get("decision") or "")
        if decision == "reject":
            continue
        suffix = str(label.get("relevant_source_suffix") or "")
        if decision != "accept" or suffix not in suffixes:
            errors.append(f"source label {index} decision or suffix mismatch")
            continue
        candidate = candidate_by_hash[query_hash]
        query_source = (
            f"private-session://{candidate.get('session_id')}/"
            f"{candidate.get('chunk_index')}/{candidate.get('turn_ordinal')}/"
            f"{query_hash[:16]}"
        )
        expected_queries.append(
            {
                "id": candidate.get("candidate_id"),
                "query_source_uri": query_source,
                "query_sha256": query_hash,
                "authored_at_utc": candidate.get("authored_at_utc"),
                "query": candidate.get("query"),
                "relevant_source_suffix": suffix,
                "review": {
                    "reviewer": reviewer,
                    "reviewed_at_utc": reviewed_at,
                    "topic_groups": candidate.get("topic_groups"),
                    "review_stratum": (
                        str(label.get("review_stratum") or "").strip()
                        or candidate.get("review_stratum")
                    ),
                    "rationale": str(label.get("rationale") or "").strip(),
                },
            }
        )
    if used_hashes != set(candidate_by_hash):
        errors.append("source labels do not cover every queued candidate")
    if benchmark.get("queries") != expected_queries:
        errors.append("benchmark queries do not reconstruct from the source chain")

    if preparation.get("schema") != PREPARATION_SCHEMA:
        errors.append("source preparation receipt schema mismatch")
    preparation_core = dict(preparation)
    preparation_hash = str(preparation_core.pop("receipt_sha256", ""))
    if preparation_hash != _canonical_sha256(preparation_core):
        errors.append("source preparation receipt content hash mismatch")
    if (
        preparation.get("status")
        != "READY_FOR_INDEPENDENT_HASH_BOUND_REVIEW_NO_SCORING"
    ):
        errors.append("source preparation receipt status mismatch")
    if preparation.get("queue_file_sha256") != receipt.get("queue_file_sha256"):
        errors.append("source preparation queue file binding mismatch")
    if preparation.get("queue_content_sha256") != queue_hash:
        errors.append("source preparation queue content binding mismatch")
    if preparation.get("catalog_sha256") != receipt.get("catalog_sha256"):
        errors.append("source preparation catalog binding mismatch")
    if preparation.get("candidate_count") != len(candidates):
        errors.append("source preparation candidate count mismatch")
    if preparation.get("source_count") != len(source_rows):
        errors.append("source preparation source count mismatch")
    if preparation.get("source_inventory_sha256") != _canonical_sha256(
        source_inventory
    ):
        errors.append("source preparation inventory binding mismatch")
    if preparation.get("scoring") != "NOT_AUTHORIZED_BY_PREPARATION" or any(
        preparation.get(field) != "NOT_AUTHORIZED"
        for field in ("training_intake", "serving", "merge", "promotion")
    ):
        errors.append("source preparation receipt weakens a no-promotion boundary")


def _same_number(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    except (TypeError, ValueError):
        return False


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


def _macro(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["relevant_source_uri"]), []).append(
            float(row["reciprocal_rank"])
        )
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
    pooled_sd = math.sqrt(
        (
            (stdev(candidate) ** 2 if len(candidate) > 1 else 0.0)
            + (stdev(control) ** 2 if len(control) > 1 else 0.0)
        )
        / 2.0
    )
    threshold = 2.0 * pooled_sd
    difference_mean = mean(differences)
    return {
        "mean_difference": difference_mean,
        "pooled_sd": pooled_sd,
        "two_pooled_sd": threshold,
        "passes_two_pooled_sd": difference_mean > threshold,
    }


def _check_mapping(
    errors: list[str],
    label: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    if set(actual) != set(expected):
        errors.append(f"{label}: key set mismatch")
        return
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if isinstance(expected_value, (float, int)) and not isinstance(
            expected_value, bool
        ):
            if not _same_number(actual_value, expected_value):
                errors.append(f"{label}.{key}: numeric mismatch")
        elif actual_value != expected_value:
            errors.append(f"{label}.{key}: value mismatch")


def verify_e92_prospective_bundle(
    output_dir: str | Path,
    *,
    expected_control_seeds: Sequence[int] = DEFAULT_CONTROL_SEEDS,
) -> dict[str, Any]:
    root = Path(output_dir).resolve(strict=True)
    benchmark_path = root / "BENCHMARK.json"
    result_path = root / "RESULT.json"
    receipt_path = root / "RUN_RECEIPT.json"
    benchmark = _load(benchmark_path)
    result = _load(result_path)
    receipt = _load(receipt_path)
    errors: list[str] = []
    expected_seeds = list(expected_control_seeds)
    if (
        len(expected_seeds) < 3
        or len(set(expected_seeds)) != len(expected_seeds)
        or any(
            isinstance(seed, bool) or not isinstance(seed, int)
            for seed in expected_seeds
        )
    ):
        raise ValueError(
            "expected_control_seeds must contain at least three distinct integers"
        )

    if benchmark.get("schema") != BENCHMARK_SCHEMA:
        errors.append("benchmark schema mismatch")
    if result.get("schema") != RESULT_SCHEMA:
        errors.append("result schema mismatch")
    if receipt.get("schema") != E92_RUN_SCHEMA:
        errors.append("run receipt schema mismatch")
    receipt_core = dict(receipt)
    claimed_receipt_hash = str(receipt_core.pop("receipt_sha256", ""))
    if claimed_receipt_hash != _canonical_sha256(receipt_core):
        errors.append("run receipt content hash mismatch")
    benchmark_hash = _sha256_file(benchmark_path)
    result_hash = _sha256_file(result_path)
    if receipt.get("benchmark_sha256") != benchmark_hash:
        errors.append("benchmark file hash mismatch")
    if receipt.get("result_sha256") != result_hash:
        errors.append("result file hash mismatch")
    if result.get("benchmark_sha256") != benchmark_hash:
        errors.append("result benchmark binding mismatch")
    if result.get("catalog_sha256") != receipt.get("catalog_sha256"):
        errors.append("catalog binding mismatch")
    catalog = Path(str(receipt.get("catalog") or ""))
    if not catalog.is_file() or _sha256_file(catalog) != receipt.get("catalog_sha256"):
        errors.append("catalog file hash mismatch")
    source_chain = _load_source_chain(root, receipt, errors)
    _verify_source_chain(
        source_chain,
        benchmark=benchmark,
        receipt=receipt,
        errors=errors,
    )
    if result.get("algorithm_revision") != ALGORITHM_REVISION:
        errors.append("algorithm revision mismatch")
    if result.get("candidate_arm") != "late_output_fused":
        errors.append("candidate arm mismatch")
    if any(
        receipt.get(field) != "NOT_AUTHORIZED"
        for field in ("training_intake", "serving", "merge", "promotion")
    ):
        errors.append("run receipt weakens a no-promotion boundary")
    receipt_seeds = receipt.get("control_seeds")
    result_seeds = result.get("control_seeds")
    if receipt_seeds != expected_seeds:
        errors.append(
            "run receipt control seeds do not match the independently expected seeds"
        )
    if result_seeds != expected_seeds:
        errors.append(
            "result control seeds do not match the independently expected seeds"
        )
    if result_seeds != receipt_seeds:
        errors.append("result and run receipt control seed declarations differ")
    if result.get("result_limit") != receipt.get("result_limit"):
        errors.append("result limit differs from the run receipt")
    if result.get("query_provenance") != benchmark.get("query_provenance"):
        errors.append("result query provenance differs from the benchmark")

    module_root = Path(__file__).resolve().parent
    expected_implementation_hashes = {
        name: _sha256_file(module_root / name)
        for name in (
            "prime_token_catalog.py",
            "prime_token_benchmark.py",
            "prime_token_query_harvest.py",
            "prime_token_prospective.py",
        )
    }
    if receipt.get("implementation_hashes") != expected_implementation_hashes:
        errors.append("implementation source hash mismatch")

    queries = benchmark.get("queries")
    if not isinstance(queries, list):
        errors.append("benchmark query list missing")
        queries = []
    query_ids = [
        str(row.get("id") or "") for row in queries if isinstance(row, Mapping)
    ]
    if (
        len(query_ids) != len(queries)
        or not all(query_ids)
        or len(set(query_ids)) != len(query_ids)
    ):
        errors.append("benchmark query identities are incomplete or duplicated")
    if result.get("query_count") != len(queries):
        errors.append("result query count mismatch")
    arms = result.get("arms")
    if not isinstance(arms, Mapping) or set(arms) != EXPECTED_ARMS:
        errors.append("result arm set mismatch")
        arms = {}
    for arm_name, runs in arms.items():
        if not isinstance(runs, list) or not runs:
            errors.append(f"{arm_name}: run list missing")
            continue
        expected_run_seeds = (
            expected_seeds
            if arm_name in {"shuffled_binding", "random_rank_fusion"}
            else [0]
        )
        if len(runs) != len(expected_run_seeds):
            errors.append(
                f"{arm_name}: expected {len(expected_run_seeds)} runs, found {len(runs)}"
            )
        for run_index, run in enumerate(runs):
            if run_index >= len(expected_run_seeds):
                errors.append(f"{arm_name}[{run_index}]: unexpected extra run")
            elif (
                not isinstance(run, Mapping)
                or run.get("control_seed") != expected_run_seeds[run_index]
            ):
                errors.append(f"{arm_name}[{run_index}]: control seed mismatch")
            outcomes = run.get("outcomes") if isinstance(run, Mapping) else None
            if (
                not isinstance(outcomes, list)
                or [row.get("query_id") for row in outcomes] != query_ids
            ):
                errors.append(f"{arm_name}[{run_index}]: outcome query order mismatch")
                continue
            for outcome_index, outcome in enumerate(outcomes):
                benchmark_query = queries[outcome_index]
                review = benchmark_query.get("review", {})
                if outcome.get("query_source_uri") != benchmark_query.get(
                    "query_source_uri"
                ):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: query source mismatch"
                    )
                if not isinstance(review, Mapping) or outcome.get(
                    "review_stratum"
                ) != review.get("review_stratum"):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: review stratum mismatch"
                    )
                source_suffix = str(benchmark_query.get("relevant_source_suffix") or "")
                if not source_suffix or not str(
                    outcome.get("relevant_source_uri") or ""
                ).endswith(source_suffix):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: relevant source mismatch"
                    )
                rank = outcome.get("rank")
                expected_rr = 0.0 if rank is None else 1.0 / int(rank)
                if not _same_number(outcome.get("reciprocal_rank"), expected_rr):
                    errors.append(
                        f"{arm_name}[{run_index}].outcomes[{outcome_index}]: reciprocal rank mismatch"
                    )
            _check_mapping(
                errors,
                f"{arm_name}[{run_index}].metrics",
                run.get("metrics", {}),
                _metrics(outcomes),
            )
            actual_macro = run.get("macro_source_metrics", {})
            expected_macro = _macro(outcomes)
            if actual_macro.get("sources") != expected_macro[
                "sources"
            ] or not _same_number(
                actual_macro.get("macro_mrr"), expected_macro["macro_mrr"]
            ):
                errors.append(f"{arm_name}[{run_index}]: macro source summary mismatch")
            if actual_macro.get("by_source") != expected_macro["by_source"]:
                errors.append(f"{arm_name}[{run_index}]: per-source metrics mismatch")

    if not errors and arms:
        candidate_outcomes = arms["late_output_fused"][0]["outcomes"]
        candidate_rr = [float(row["reciprocal_rank"]) for row in candidate_outcomes]
        expected_gates: dict[str, Any] = {}
        for control_name in ("lexical_only", "no_intervention", "route_null"):
            expected_gates[control_name] = _paired_gate(
                candidate_rr,
                [
                    float(row["reciprocal_rank"])
                    for row in arms[control_name][0]["outcomes"]
                ],
            )
        for run in arms["shuffled_binding"]:
            seed = int(run["control_seed"])
            expected_gates[f"shuffled_binding_seed_{seed}"] = _paired_gate(
                candidate_rr,
                [float(row["reciprocal_rank"]) for row in run["outcomes"]],
            )
        for run in arms["random_rank_fusion"]:
            seed = int(run["control_seed"])
            expected_gates[f"random_rank_fusion_seed_{seed}"] = _paired_gate(
                candidate_rr,
                [float(row["reciprocal_rank"]) for row in run["outcomes"]],
            )
        actual_gates = result.get("gates", {})
        if set(actual_gates) != set(expected_gates):
            errors.append("paired gate set mismatch")
        else:
            for name, expected in expected_gates.items():
                _check_mapping(errors, f"gates.{name}", actual_gates[name], expected)

        candidate_macro = _macro(candidate_outcomes)
        lexical_outcomes = arms["lexical_only"][0]["outcomes"]
        lexical_macro = _macro(lexical_outcomes)
        macro_gate = {
            "candidate_macro_mrr": candidate_macro["macro_mrr"],
            "lexical_macro_mrr": lexical_macro["macro_mrr"],
            "passes": candidate_macro["macro_mrr"] > lexical_macro["macro_mrr"],
        }
        _check_mapping(
            errors, "macro_source_gate", result.get("macro_source_gate", {}), macro_gate
        )
        source_deltas = {
            source: candidate_macro["by_source"][source]["mrr"]
            - lexical_macro["by_source"][source]["mrr"]
            for source in candidate_macro["by_source"]
        }
        source_gate = {
            "improved_sources": sum(value > 0 for value in source_deltas.values()),
            "harmed_sources": sum(value < 0 for value in source_deltas.values()),
            "worst_source_delta": min(source_deltas.values(), default=0.0),
            "per_source_delta": source_deltas,
        }
        source_gate["passes"] = (
            source_gate["improved_sources"] >= 3
            and source_gate["worst_source_delta"] >= -0.05
        )
        actual_source_gate = result.get("source_change_gate", {})
        if set(actual_source_gate) != set(source_gate):
            errors.append("source change gate key mismatch")
        else:
            for key, value in source_gate.items():
                if key == "per_source_delta":
                    if actual_source_gate[key] != value:
                        errors.append("source change per-source delta mismatch")
                elif isinstance(value, (float, int)) and not isinstance(value, bool):
                    if not _same_number(actual_source_gate[key], value):
                        errors.append(f"source change gate {key} mismatch")
                elif actual_source_gate[key] != value:
                    errors.append(f"source change gate {key} mismatch")

        source_counts = Counter(
            str(row["relevant_source_uri"]) for row in candidate_outcomes
        )
        strata = sorted(
            {
                str(row.get("review_stratum") or "")
                for row in candidate_outcomes
                if row.get("review_stratum")
            }
        )
        max_source_share = max(source_counts.values(), default=0) / len(
            candidate_outcomes
        )
        diversity = {
            "topic_strata": strata,
            "topic_strata_count": len(strata),
            "relevant_source_count": len(source_counts),
            "max_relevant_source_share": max_source_share,
            "relevant_source_query_counts": dict(sorted(source_counts.items())),
        }
        if result.get("diversity") != diversity:
            errors.append("diversity summary mismatch")
        underpowered = []
        if len(queries) < MIN_CAPABILITY_QUERIES:
            underpowered.append(
                f"{len(queries)} queries is below the preregistered {MIN_CAPABILITY_QUERIES}-query capability floor"
            )
        if benchmark.get("query_provenance") != "independent_external":
            underpowered.append(
                "queries are not independently authored external requests"
            )
        if len(strata) < 3:
            underpowered.append("fewer than three reviewed topic strata")
        if len(source_counts) < 6:
            underpowered.append("fewer than six distinct relevant catalog sources")
        if max_source_share > 0.4:
            underpowered.append("one relevant source exceeds the 40-percent cap")
        if result.get("underpowered_reasons") != underpowered:
            errors.append("underpowered reason mismatch")
        all_gates = all(
            bool(value["passes_two_pooled_sd"]) for value in expected_gates.values()
        )
        expected_status = (
            "UNDERPOWERED"
            if underpowered
            else (
                "CANDIDATE_PASS"
                if all_gates and macro_gate["passes"] and source_gate["passes"]
                else "NO_GAIN"
            )
        )
        if (
            result.get("status") != expected_status
            or receipt.get("result_status") != expected_status
        ):
            errors.append("terminal status mismatch")

    verification_core = {
        "schema": "scbe.e92-prospective-verification.v1",
        "status": (
            "VERIFIED_E92_PROSPECTIVE_NO_AUTOMATIC_PROMOTION"
            if not errors
            else "INVALID_E92_PROSPECTIVE_BUNDLE"
        ),
        "bundle": str(root),
        "benchmark_sha256": _sha256_file(benchmark_path),
        "result_sha256": _sha256_file(result_path),
        "run_receipt_sha256": _sha256_file(receipt_path),
        "query_count": len(queries),
        "error_count": len(errors),
        "errors": errors,
        "training_intake": "NOT_AUTHORIZED",
        "serving": "NOT_AUTHORIZED",
        "merge": "NOT_AUTHORIZED",
        "promotion": "NOT_AUTHORIZED",
    }
    return {
        **verification_core,
        "verification_sha256": _canonical_sha256(verification_core),
    }
