"""Fail-closed aggregation for the prime-token frozen input-access horse race."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Mapping, Sequence

from .prime_token_training import canonical_sha256, sha256_file

SCHEMA = "scbe.prime-token-input-access-evidence.v1"
MANIFEST_SCHEMA = "scbe.prime-token-input-access-evidence-manifest.v1"
SOURCE_RECONSTRUCTION_SCHEMA = "scbe.prime-token-independent-source-reconstruction.v1"
CANDIDATE_ARM = "canonical_six_view_reader"
NO_INTERVENTION_ARM = "no_intervention"
MATCHED_CONTROL_ARMS = (
    "lexical_only_reader",
    "random_fixed_reader",
    "shuffled_binding_reader",
    "single_frame_reader",
)
REQUIRED_ARMS = (NO_INTERVENTION_ARM, CANDIDATE_ARM, *MATCHED_CONTROL_ARMS)
PRIMARY_METRICS = ("accuracy", "relationship", "function")
SYSTEM_METRICS = (
    "ordinary_false_activation",
    "frozen_parent_retention",
    "throughput",
    "peak_memory",
    "checkpoint_bytes",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON artifact must be an object: {path}")
    return value


def _bound_artifact(
    row: Mapping[str, Any], key: str, root: Path
) -> tuple[Path, dict[str, Any]]:
    raw_path = row.get(f"{key}_path")
    expected_hash = row.get(f"{key}_sha256")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"evidence entry omitted {key}_path")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError(f"evidence entry omitted {key}_sha256")
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve(strict=True)
    if sha256_file(path) != expected_hash.casefold():
        raise RuntimeError(f"{key} hash mismatch")
    return path, _load_json(path)


def _number(value: object, label: str, *, unit_interval: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if unit_interval and not 0.0 <= result <= 1.0:
        raise ValueError(f"{label} must lie in [0,1]")
    return result


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase hexadecimal SHA-256")
    return value


def _outcome_map(run: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    evaluation = run.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("run result omitted evaluation")
    metrics = evaluation.get("metrics")
    outcomes = evaluation.get("per_example")
    if not isinstance(metrics, dict) or not isinstance(outcomes, list) or not outcomes:
        raise ValueError("run result omitted metrics or per-example outcomes")
    for metric in (*PRIMARY_METRICS, *SYSTEM_METRICS):
        _number(metrics.get(metric), f"metrics.{metric}")
    mapped: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(outcomes):
        if not isinstance(row, dict):
            raise TypeError("per-example outcome must be an object")
        identity = row.get("id")
        if not isinstance(identity, str) or not identity.strip() or identity in mapped:
            raise ValueError("per-example outcome identity is empty or duplicated")
        for field in ("record_id", "source_family", "query_source_family"):
            if not isinstance(row.get(field), str) or not str(row[field]).strip():
                raise ValueError(f"per-example outcome {index} omitted {field}")
        if row.get("split") not in {"validation", "final_test"}:
            raise ValueError("per-example outcome uses an invalid held split")
        normalized = dict(row)
        for metric in PRIMARY_METRICS:
            normalized[metric] = _number(
                row.get(metric), f"outcome.{identity}.{metric}", unit_interval=True
            )
        if normalized["accuracy"] not in {0.0, 1.0}:
            raise ValueError("per-example accuracy must be binary for exact replay")
        mapped[identity] = normalized
    for metric in PRIMARY_METRICS:
        observed = mean(float(row[metric]) for row in mapped.values())
        if not math.isclose(
            observed, _number(metrics[metric], f"metrics.{metric}"), abs_tol=1e-12
        ):
            raise RuntimeError(f"producer aggregate differs from per-example {metric}")
    return mapped


def _flatten_replay(
    replay: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], bool]:
    if replay.get("schema") != "scbe.prime-token-independent-replay-run.v1":
        raise ValueError("unexpected independent replay schema")
    if replay.get("status") != "VERIFIED_REPLAY_NO_PROMOTION":
        raise ValueError("independent replay is not verified")
    if (
        replay.get("promotion_authorized") is not False
        or replay.get("partial_unfreeze_authorized") is not False
        or replay.get("tool_dispatch") is not False
    ):
        raise ValueError("independent replay changed authority")
    if replay.get("producer_runtime_cases_ignored") is not True:
        raise ValueError("independent replay did not reject producer runtime cases")
    source_reconstruction = replay.get("source_reconstruction")
    if (
        not isinstance(source_reconstruction, dict)
        or source_reconstruction.get("schema") != SOURCE_RECONSTRUCTION_SCHEMA
    ):
        raise ValueError("independent replay omitted its source reconstruction receipt")
    for field in (
        "producer_runtime_cases_consumed",
        "producer_targets_consumed",
    ):
        if source_reconstruction.get(field) is not False:
            raise ValueError(f"independent source reconstruction changed {field}")
    for field in (
        "producer_targets_verified",
        "query_inputs_rebuilt_from_benchmark",
        "targets_rebuilt_from_source_and_evaluator",
    ):
        if source_reconstruction.get(field) is not True:
            raise ValueError(f"independent source reconstruction omitted {field}")
    cases = replay.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("independent replay omitted cases")
    rows: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("outcomes"), list):
            raise ValueError("independent replay case omitted outcomes")
        for row in case["outcomes"]:
            identity = row.get("id") if isinstance(row, dict) else None
            if not isinstance(identity, str) or not identity or identity in rows:
                raise ValueError("independent replay outcome identity is invalid")
            normalized = dict(row)
            normalized["target_logit"] = _number(
                row.get("target_logit"), f"replay.{identity}.target_logit"
            )
            normalized["target_nll"] = _number(
                row.get("target_nll"), f"replay.{identity}.target_nll"
            )
            if normalized["target_nll"] < 0.0:
                raise ValueError("independent replay target NLL is negative")
            rows[identity] = normalized
    if int(replay.get("example_count", -1)) != len(rows):
        raise RuntimeError("independent replay count differs from outcomes")
    raw_packet_usage = [case.get("prime_packet_used") for case in cases]
    if not all(isinstance(value, bool) for value in raw_packet_usage):
        raise RuntimeError("independent replay omitted its packet-use policy")
    packet_usage = set(raw_packet_usage)
    if len(packet_usage) != 1:
        raise RuntimeError("independent replay mixed packet-use policies")
    replay_accuracy = _number(
        replay.get("accuracy"), "replay.accuracy", unit_interval=True
    )
    observed_accuracy = mean(float(bool(row.get("correct"))) for row in rows.values())
    if not math.isclose(replay_accuracy, observed_accuracy, abs_tol=1e-12):
        raise RuntimeError("independent replay aggregate differs from outcomes")
    observed_nll = mean(float(row["target_nll"]) for row in rows.values())
    if not math.isclose(
        _number(replay.get("mean_target_nll"), "replay.mean_target_nll"),
        observed_nll,
        abs_tol=1e-12,
    ):
        raise RuntimeError(
            "independent replay target NLL aggregate differs from outcomes"
        )
    return rows, next(iter(packet_usage))


def _verify_run_and_replay(
    *, arm: str, seed: int, run: Mapping[str, Any], replay: Mapping[str, Any]
) -> tuple[dict[str, float], dict[str, dict[str, Any]], tuple[str, str, str]]:
    if (
        run.get("schema") != "scbe.prime-token-reader-run.v1"
        or run.get("status") != "COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("run result is not a completed no-promotion lineage")
    if (
        run.get("promotion_authorized") is not False
        or run.get("partial_unfreeze_authorized") is not False
        or run.get("tool_dispatch") is not False
    ):
        raise ValueError("run result changed authority")
    identity = run.get("identity")
    if (
        not isinstance(identity, dict)
        or identity.get("arm") != arm
        or int(identity.get("seed", -1)) != seed
    ):
        raise ValueError("run identity differs from evidence manifest")
    boundary = tuple(
        _sha256(identity.get(key), f"identity.{key}")
        for key in ("parent_sha256", "source_manifest_sha256", "split_manifest_sha256")
    )
    source_reconstruction = replay.get("source_reconstruction")
    if not isinstance(source_reconstruction, dict):
        raise ValueError("independent replay omitted source reconstruction")
    for field in (
        "source_manifest_sha256",
        "split_manifest_sha256",
        "cases_manifest_sha256",
        "evaluator_receipt_sha256",
    ):
        if _sha256(
            source_reconstruction.get(field), f"source_reconstruction.{field}"
        ) != _sha256(identity.get(field), f"identity.{field}"):
            raise RuntimeError(
                f"independent source reconstruction differs from run identity at {field}"
            )
    outcomes = _outcome_map(run)
    replay_rows, prime_packet_used = _flatten_replay(replay)
    evaluator_receipt = _sha256(
        run["evaluation"].get("evaluator_receipt_sha256"),
        "evaluation.evaluator_receipt_sha256",
    )
    replay_receipts = {
        _sha256(
            case.get("exact_evaluator_receipt_sha256"),
            "replay.exact_evaluator_receipt_sha256",
        )
        for case in replay["cases"]
    }
    if replay_receipts != {evaluator_receipt}:
        raise RuntimeError("producer and replay evaluator receipts differ")
    if set(outcomes) != set(replay_rows):
        raise RuntimeError("producer and replay outcome identities differ")
    for identity_key, producer in outcomes.items():
        independent = replay_rows[identity_key]
        for field in (
            "record_id",
            "split",
            "source_family",
            "query_source_family",
        ):
            if producer[field] != independent.get(field):
                raise RuntimeError(
                    f"producer and replay provenance differ for {identity_key}"
                )
        if bool(independent.get("correct")) != bool(producer["accuracy"]):
            raise RuntimeError(
                f"producer and replay accuracy differ for {identity_key}"
            )
    if not math.isclose(
        _number(replay.get("accuracy"), "replay.accuracy"),
        mean(row["accuracy"] for row in outcomes.values()),
        abs_tol=1e-12,
    ):
        raise RuntimeError("producer and replay accuracy aggregates differ")
    checkpoint = replay.get("checkpoint")
    if not isinstance(checkpoint, dict) or checkpoint.get(
        "identity_sha256"
    ) != canonical_sha256(identity):
        raise RuntimeError("replay checkpoint identity differs from run")
    final_step = int(run.get("final_step", -1))
    if arm == NO_INTERVENTION_ARM:
        if (
            checkpoint.get("checkpoint_free_baseline") is not True
            or checkpoint.get("checkpoint") is not None
            or final_step != 0
            or prime_packet_used
        ):
            raise RuntimeError("no-intervention replay is not checkpoint-free")
    elif (
        checkpoint.get("checkpoint") is None
        or int(checkpoint.get("step", -1)) != final_step
        or not prime_packet_used
    ):
        raise RuntimeError("learned replay checkpoint differs from final run step")
    metrics = run["evaluation"]["metrics"]
    return (
        {name: float(metrics[name]) for name in (*PRIMARY_METRICS, *SYSTEM_METRICS)},
        outcomes,
        boundary,
    )


def _exact_sign_p(wins: int, losses: int) -> float:
    pairs = wins + losses
    if not pairs or wins <= losses:
        return 1.0
    return sum(math.comb(pairs, k) for k in range(wins, pairs + 1)) / (2**pairs)


def _comparison_gate(
    candidate_seed_values: Sequence[float],
    control_seed_values: Sequence[float],
    candidate_rows: Mapping[str, Sequence[float]],
    control_rows: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    if (
        len(candidate_seed_values) != len(control_seed_values)
        or len(candidate_seed_values) < 3
    ):
        raise ValueError("comparison requires the same three or more seeds")
    if set(candidate_rows) != set(control_rows) or not candidate_rows:
        raise ValueError("comparison requires aligned held examples")
    pooled_sd = math.sqrt(
        (stdev(candidate_seed_values) ** 2 + stdev(control_seed_values) ** 2) / 2.0
    )
    gain = mean(candidate_seed_values) - mean(control_seed_values)
    differences = [
        mean(candidate_rows[key]) - mean(control_rows[key])
        for key in sorted(candidate_rows)
    ]
    wins = sum(value > 1e-15 for value in differences)
    losses = sum(value < -1e-15 for value in differences)
    ties = len(differences) - wins - losses
    p_value = _exact_sign_p(wins, losses)
    return {
        "candidate_mean": mean(candidate_seed_values),
        "control_mean": mean(control_seed_values),
        "mean_difference": gain,
        "pooled_seed_sd": pooled_sd,
        "two_pooled_seed_sd": 2.0 * pooled_sd,
        "passes_two_pooled_seed_sd": gain > 2.0 * pooled_sd,
        "finite_sample_test": "exact_one_sided_paired_sign_on_across_seed_example_means",
        "finite_sample_alpha": 0.05,
        "pair_count": len(differences),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "exact_one_sided_p_value": p_value,
        "passes_finite_sample_uncertainty": p_value <= 0.05,
        "passes_gate": gain > 2.0 * pooled_sd and p_value <= 0.05,
    }


def aggregate_evidence(manifest_path: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve(strict=True)
    manifest = _load_json(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("unexpected evidence manifest schema")
    seeds = tuple(int(seed) for seed in manifest.get("seeds", ()))
    if len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise ValueError("evidence manifest requires at least three unique seeds")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("evidence manifest omitted entries")
    expected = {(arm, seed) for arm in REQUIRED_ARMS for seed in seeds}
    indexed: dict[tuple[str, int], Mapping[str, Any]] = {}
    for row in entries:
        if not isinstance(row, dict):
            raise TypeError("evidence entry must be an object")
        key = (str(row.get("arm") or ""), int(row.get("seed", -1)))
        if key in indexed:
            raise ValueError("evidence manifest repeats an arm/seed lineage")
        indexed[key] = row
    if set(indexed) != expected:
        raise ValueError("evidence manifest does not contain the exact arm/seed grid")

    seed_metrics: dict[str, dict[int, dict[str, float]]] = {
        arm: {} for arm in REQUIRED_ARMS
    }
    example_metrics: dict[str, dict[str, dict[int, float]]] = {
        metric: {arm: {} for arm in REQUIRED_ARMS} for metric in PRIMARY_METRICS
    }
    reference_boundary: tuple[str, str, str] | None = None
    reference_provenance: dict[str, tuple[str, str, str, str]] | None = None
    artifacts = []
    for arm in REQUIRED_ARMS:
        for seed in seeds:
            row = indexed[(arm, seed)]
            run_path, run = _bound_artifact(row, "run_result", manifest_path.parent)
            replay_path, replay = _bound_artifact(
                row, "replay_result", manifest_path.parent
            )
            metrics, outcomes, boundary = _verify_run_and_replay(
                arm=arm, seed=seed, run=run, replay=replay
            )
            if reference_boundary is None:
                reference_boundary = boundary
            elif boundary != reference_boundary:
                raise RuntimeError(
                    "arm/seed lineages do not share one parent/source/split boundary"
                )
            provenance = {
                key: (
                    str(value["record_id"]),
                    str(value["split"]),
                    str(value["source_family"]),
                    str(value["query_source_family"]),
                )
                for key, value in outcomes.items()
            }
            if reference_provenance is None:
                reference_provenance = provenance
            elif provenance != reference_provenance:
                raise RuntimeError("arm/seed held provenance is not exactly aligned")
            seed_metrics[arm][seed] = metrics
            for metric in PRIMARY_METRICS:
                for key, outcome in outcomes.items():
                    example_metrics[metric][arm].setdefault(key, {})[seed] = float(
                        outcome[metric]
                    )
            artifacts.append(
                {
                    "arm": arm,
                    "seed": seed,
                    "run_result": str(run_path),
                    "run_result_sha256": sha256_file(run_path),
                    "replay_result": str(replay_path),
                    "replay_result_sha256": sha256_file(replay_path),
                }
            )

    comparisons: dict[str, Any] = {}
    for metric in PRIMARY_METRICS:
        arm_means = {
            arm: mean(seed_metrics[arm][seed][metric] for seed in seeds)
            for arm in MATCHED_CONTROL_ARMS
        }
        strongest = max(MATCHED_CONTROL_ARMS, key=lambda arm: (arm_means[arm], arm))
        metric_result: dict[str, Any] = {
            "strongest_matched_control": strongest,
            "comparisons": {},
        }
        for control in (NO_INTERVENTION_ARM, strongest):
            candidate_rows = {
                key: [values[seed] for seed in seeds]
                for key, values in example_metrics[metric][CANDIDATE_ARM].items()
            }
            control_rows = {
                key: [values[seed] for seed in seeds]
                for key, values in example_metrics[metric][control].items()
            }
            metric_result["comparisons"][control] = _comparison_gate(
                [seed_metrics[CANDIDATE_ARM][seed][metric] for seed in seeds],
                [seed_metrics[control][seed][metric] for seed in seeds],
                candidate_rows,
                control_rows,
            )
        metric_result["passes_gate"] = all(
            value["passes_gate"] for value in metric_result["comparisons"].values()
        )
        comparisons[metric] = metric_result

    all_primary_pass = all(value["passes_gate"] for value in comparisons.values())
    return {
        "schema": SCHEMA,
        "status": (
            "SUPPORTED_NO_PROMOTION"
            if all_primary_pass
            else "UNDERPOWERED_NO_PROMOTION"
        ),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "candidate_arm": CANDIDATE_ARM,
        "matched_control_arms": list(MATCHED_CONTROL_ARMS),
        "seeds": list(seeds),
        "source_boundary": {
            "parent_sha256": reference_boundary[0],
            "source_manifest_sha256": reference_boundary[1],
            "split_manifest_sha256": reference_boundary[2],
        },
        "held_example_count": len(reference_provenance or {}),
        "comparisons": comparisons,
        "system_metrics_by_arm_seed": seed_metrics,
        "artifacts": artifacts,
        "all_primary_metrics_pass": all_primary_pass,
        "independent_bounded_output_replay_complete": True,
        "tool_dispatch": False,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }


__all__ = ["aggregate_evidence"]
