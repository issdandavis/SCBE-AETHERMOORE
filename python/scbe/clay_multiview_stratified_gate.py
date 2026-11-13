"""Pre-registered, held-sector-stratified gate for Clay multi-view campaigns."""

from __future__ import annotations

import math
import statistics
from typing import Any, Mapping, Sequence

from python.scbe.clay_paired_orbit_training import sha256_json

SCHEMA = "clay.multiview-stratified-gate.v1"
METRICS = ("accuracy", "stable_macro_f1")
EXPECTED_PRIMARY = "curriculum_independent"
EXPECTED_CONTROLS = ("static_unique", "static_repeated")


class StratifiedGateError(ValueError):
    """Raised when a producer result cannot support the registered comparison."""


def _two_pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        raise StratifiedGateError("each held-sector arm needs at least two seeds")
    return 2.0 * math.sqrt(
        (statistics.variance(left) + statistics.variance(right)) / 2.0
    )


def _rows_by_seed(rows: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    result: dict[int, Mapping[str, Any]] = {}
    for row in rows:
        seed = int(row["seed"])
        if seed in result:
            raise StratifiedGateError(f"duplicate seed in held-sector arm: {seed}")
        result[seed] = row
    return result


def evaluate_stratified_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the locked sector-wise gate without granting model authority."""

    configuration = result.get("configuration")
    horses = result.get("horses")
    if not isinstance(configuration, Mapping) or not isinstance(horses, list):
        raise StratifiedGateError("producer result is missing configuration or horses")

    primary = str(configuration.get("primary_arm"))
    controls = tuple(str(value) for value in configuration.get("controls", ()))
    held_sectors = tuple(int(value) for value in configuration.get("held_sectors", ()))
    evaluation_records = int(configuration.get("evaluation_records", 0))
    if primary != EXPECTED_PRIMARY or controls != EXPECTED_CONTROLS:
        raise StratifiedGateError(
            "producer arms differ from the preregistered comparison"
        )
    if len(held_sectors) != 3 or len(set(held_sectors)) != 3:
        raise StratifiedGateError(
            "the preregistered gate requires three distinct held sectors"
        )
    if evaluation_records < 1:
        raise StratifiedGateError("evaluation record count must be positive")

    source_body = {
        key: value for key, value in result.items() if key != "result_sha256"
    }
    source_receipt_valid = sha256_json(source_body) == result.get("result_sha256")
    if not source_receipt_valid:
        raise StratifiedGateError("producer result receipt does not verify")

    # Conservative bounded-metric floor used when per-example paired ledgers are
    # unavailable.  It prevents zero seed variance from reducing the gate to zero.
    finite_evaluation_floor = 2.0 / math.sqrt(evaluation_records)
    required_clear_sectors = 2
    comparisons: dict[str, Any] = {}

    for control in controls:
        sectors: dict[str, Any] = {}
        for held in held_sectors:
            candidate_rows = [
                row
                for row in horses
                if int(row["held_sector"]) == held and row["arm"] == primary
            ]
            control_rows = [
                row
                for row in horses
                if int(row["held_sector"]) == held and row["arm"] == control
            ]
            candidate_by_seed = _rows_by_seed(candidate_rows)
            control_by_seed = _rows_by_seed(control_rows)
            if set(candidate_by_seed) != set(control_by_seed):
                raise StratifiedGateError(
                    f"matched seeds differ for held={held}, control={control}"
                )

            metric_rows: dict[str, Any] = {}
            for metric in METRICS:
                candidate = [
                    float(candidate_by_seed[seed]["holdout"][metric])
                    for seed in sorted(candidate_by_seed)
                ]
                baseline = [
                    float(control_by_seed[seed]["holdout"][metric])
                    for seed in sorted(control_by_seed)
                ]
                delta = statistics.fmean(candidate) - statistics.fmean(baseline)
                pooled_threshold = _two_pooled_sd(candidate, baseline)
                required_delta = max(pooled_threshold, finite_evaluation_floor)
                paired_deltas = [
                    left - right
                    for left, right in zip(candidate, baseline, strict=True)
                ]
                metric_rows[metric] = {
                    "candidate_mean": statistics.fmean(candidate),
                    "control_mean": statistics.fmean(baseline),
                    "delta": delta,
                    "two_pooled_sd": pooled_threshold,
                    "finite_evaluation_floor": finite_evaluation_floor,
                    "required_delta": required_delta,
                    "positive": delta > 0.0,
                    "clears_gate": delta > required_delta,
                    "matched_wins": sum(value > 0.0 for value in paired_deltas),
                    "matched_ties": sum(value == 0.0 for value in paired_deltas),
                    "matched_losses": sum(value < 0.0 for value in paired_deltas),
                }

            candidate_anchor = statistics.fmean(
                float(row["anchor"]["accuracy"]) for row in candidate_rows
            )
            control_anchor = statistics.fmean(
                float(row["anchor"]["accuracy"]) for row in control_rows
            )
            sectors[str(held)] = {
                "metrics": metric_rows,
                "anchor_candidate_mean": candidate_anchor,
                "anchor_control_mean": control_anchor,
                "anchor_delta": candidate_anchor - control_anchor,
                "retention_within_two_points": candidate_anchor
                >= control_anchor - 0.02,
            }

        comparison_gate = {
            metric: {
                "positive_in_every_sector": all(
                    sector["metrics"][metric]["positive"] for sector in sectors.values()
                ),
                "clear_sector_count": sum(
                    sector["metrics"][metric]["clears_gate"]
                    for sector in sectors.values()
                ),
                "required_clear_sector_count": required_clear_sectors,
            }
            for metric in METRICS
        }
        comparison_passes = all(
            row["positive_in_every_sector"]
            and row["clear_sector_count"] >= row["required_clear_sector_count"]
            for row in comparison_gate.values()
        ) and all(sector["retention_within_two_points"] for sector in sectors.values())
        comparisons[control] = {
            "sectors": sectors,
            "gate": comparison_gate,
            "anchor_retained_in_every_sector": all(
                sector["retention_within_two_points"] for sector in sectors.values()
            ),
            "passes": comparison_passes,
        }

    passes = all(row["passes"] for row in comparisons.values())
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "source_result_sha256": result["result_sha256"],
        "source_receipt_valid": source_receipt_valid,
        "primary_arm": primary,
        "controls": list(controls),
        "held_sectors": list(held_sectors),
        "evaluation_records_per_sector": evaluation_records,
        "finite_evaluation_floor": finite_evaluation_floor,
        "required_clear_sectors": required_clear_sectors,
        "comparisons": comparisons,
        "verdict": (
            "PASS_STRATIFIED_MECHANICS_NO_PROMOTION" if passes else "NO_SELECTION"
        ),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "gate_sha256": sha256_json(body)}


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Clay multi-view stratified gate",
        "",
        f"Verdict: `{report['verdict']}`",
        "",
        "| Control | Sector | Accuracy delta / required | Stable F1 delta / required | Anchor retained |",
        "| --- | ---: | ---: | ---: | :---: |",
    ]
    for control, comparison in report["comparisons"].items():
        for held, sector in comparison["sectors"].items():
            accuracy = sector["metrics"]["accuracy"]
            stable = sector["metrics"]["stable_macro_f1"]
            lines.append(
                f"| {control} | {held} | {accuracy['delta']:.4f} / {accuracy['required_delta']:.4f} "
                f"| {stable['delta']:.4f} / {stable['required_delta']:.4f} "
                f"| {'yes' if sector['retention_within_two_points'] else 'no'} |"
            )
    lines.extend(
        [
            "",
            "The threshold is the larger of two pooled seed standard deviations and",
            "the preregistered finite-evaluation floor. This evaluator never grants",
            "promotion or partial-unfreeze authority.",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "SCHEMA",
    "StratifiedGateError",
    "evaluate_stratified_gate",
    "render_markdown",
]
