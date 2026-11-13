"""Factor-specificity control for Clay multi-view data selection.

The primary arm reuses the shuffled-factor selector that led the preceding
discovery and confirmation markets.  The mechanism control replaces those
factor cells with deterministic SHA-256 cells of equal cardinality.  Every
arm keeps the same view/action quotas, standard learner, and compute budget.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

from python.scbe.clay_multiview_factor_coverage import (
    FACTOR_PRODUCTS,
    FactorCoverageError,
    _balanced_select,
    _collect_candidate_bank,
    _collect_paired_probe,
    _feature_row_digests,
    _feature_row_hashes,
    _quota_table,
    _subset_bank,
    _three_arm_quotas,
    _unique_feature_order,
    factor_code_matrix,
)
from python.scbe.clay_paired_orbit_training import (
    ACTION_COUNT,
    FEATURE_WIDTH,
    VIEW_COUNT,
    DataProvider,
    OrbitBank,
    _atomic_json,
    _atomic_text,
    _collect_rows,
    _save_bank,
    aggregate,
    build_evaluation_banks,
    file_sha256,
    make_bank,
    render_market,
    sha256_json,
    tensor_sha256,
    train_horse,
    utc_now,
)

SCHEMA = "clay.multiview-hash-spread-campaign.v1"
SELECTION_SCHEMA = "clay.multiview-hash-spread-selection.v1"
GATE_SCHEMA = "clay.multiview-hash-spread-gate.v1"

ARMS = (
    "static_unique",
    "multiview_random",
    "multiview_factor_shuffled",
    "multiview_hash_spread",
)
PRIMARY_ARM = "multiview_factor_shuffled"
CONTROLS = (
    "multiview_hash_spread",
    "multiview_random",
    "static_unique",
)


class HashSpreadError(FactorCoverageError):
    """Raised when the factor-specificity experiment violates a control."""


def hash_code_matrix(
    bank: OrbitBank,
    *,
    seed: int,
    widths: Sequence[int],
) -> Tensor:
    """Map exact feature rows into deterministic equal-width hash cells.

    The mapping is independent of labels, rewards, losses, gradients, and
    evaluation data.  Labels enter later only through the locked action quota.
    """

    cardinalities = tuple(int(value) for value in widths)
    if not cardinalities or any(value < 1 for value in cardinalities):
        raise HashSpreadError("hash signature widths must be positive")
    digests = _feature_row_digests(bank)
    columns: list[list[int]] = [[] for _ in cardinalities]
    seed_bytes = int(seed).to_bytes(16, "big", signed=True)
    for digest in digests:
        for column, width in enumerate(cardinalities):
            payload = (
                b"clay-hash-spread-v1\x00"
                + seed_bytes
                + column.to_bytes(4, "big", signed=False)
                + digest
            )
            value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
            columns[column].append(value % width)
    return torch.tensor(columns, dtype=torch.int64).transpose(0, 1).contiguous()


def _entropy_evenness(counts: Sequence[int]) -> float:
    total = sum(int(value) for value in counts)
    support = len(counts)
    if total <= 0 or support <= 1:
        return 1.0
    probabilities = [value / total for value in counts if value]
    entropy = -sum(value * math.log(value) for value in probabilities)
    return entropy / math.log(support)


def _signature_coverage_report(
    indices: Sequence[int],
    candidate: OrbitBank,
    signatures: Tensor,
    *,
    column_names: Sequence[str],
) -> dict[str, Any]:
    if signatures.ndim != 2 or signatures.shape[0] != candidate.features.shape[0]:
        raise HashSpreadError("signature matrix does not match candidate rows")
    if signatures.shape[1] != len(column_names):
        raise HashSpreadError("signature column names do not match matrix")
    selected = torch.tensor(list(indices), dtype=torch.int64)
    rows: list[dict[str, Any]] = []
    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            candidate_mask = (candidate.views == view) & (candidate.labels == action)
            candidate_indices = torch.nonzero(candidate_mask, as_tuple=False).flatten()
            chosen_mask = (candidate.views[selected] == view) & (
                candidate.labels[selected] == action
            )
            chosen = selected[chosen_mask]
            for column, name in enumerate(column_names):
                candidate_cells = torch.unique(signatures[candidate_indices, column])
                selected_counts = Counter(
                    int(value) for value in signatures[chosen, column].tolist()
                )
                counts = [
                    selected_counts[int(cell)] for cell in candidate_cells.tolist()
                ]
                covered = sum(value > 0 for value in counts)
                rows.append(
                    {
                        "view": view,
                        "action": action,
                        "signature_column": str(name),
                        "candidate_cells": len(counts),
                        "selected_cells": covered,
                        "coverage_ratio": covered / len(counts) if counts else 1.0,
                        "entropy_evenness": _entropy_evenness(counts),
                        "min_count": min(counts) if counts else 0,
                        "max_count": max(counts) if counts else 0,
                    }
                )
    nontrivial = [row for row in rows if row["candidate_cells"] > 1]
    if not nontrivial:
        raise HashSpreadError("signature coverage has no nontrivial tables")
    return {
        "conditional_tables": len(rows),
        "nontrivial_tables": len(nontrivial),
        "mean_coverage_ratio": statistics.fmean(
            row["coverage_ratio"] for row in nontrivial
        ),
        "mean_entropy_evenness": statistics.fmean(
            row["entropy_evenness"] for row in nontrivial
        ),
        "minimum_coverage_ratio": min(row["coverage_ratio"] for row in nontrivial),
        "tables": rows,
    }


def _bucket_indices(candidate: OrbitBank, view: int, action: int) -> list[int]:
    return (
        torch.nonzero(
            (candidate.views == view) & (candidate.labels == action),
            as_tuple=False,
        )
        .flatten()
        .tolist()
    )


def build_hash_spread_data_arms(
    provider: DataProvider,
    *,
    held_sector: int,
    rows_per_view: int,
    candidate_rows_per_view: int,
    seed: int,
) -> tuple[dict[str, OrbitBank], OrbitBank, dict[str, Any]]:
    """Build three disjoint multi-view arms and one canonical baseline."""

    if rows_per_view < 1 or candidate_rows_per_view < 3 * rows_per_view:
        raise HashSpreadError(
            "candidate pool needs at least three selected banks per view"
        )
    total = rows_per_view * VIEW_COUNT
    canonical_rows = _collect_rows(
        provider,
        provider.training_sandboxes()[0],
        count=total,
        held_sector=held_sector,
        include_held=False,
        seed=seed + 17,
        view=0,
    )
    static = make_bank("static_unique", canonical_rows, complete_groups=False)
    candidate = _collect_candidate_bank(
        provider,
        held_sector=held_sector,
        rows_per_view=candidate_rows_per_view,
        seed=seed + 100_000,
    )
    factor_signatures, factor_tables = factor_code_matrix(candidate)
    widths = [len(table) for table in factor_tables]
    hash_signatures = hash_code_matrix(candidate, seed=seed + 700_000, widths=widths)
    candidate_digests = _feature_row_digests(candidate)

    quota_by_view_action: dict[tuple[int, int], int] = {}
    for view in range(VIEW_COUNT):
        counts = [
            len(
                {
                    candidate_digests[index]
                    for index in _bucket_indices(candidate, view, action)
                }
            )
            for action in range(ACTION_COUNT)
        ]
        for action, quota in enumerate(_three_arm_quotas(counts, rows_per_view)):
            quota_by_view_action[(view, action)] = quota

    selected_indices: dict[str, list[int]] = {
        "multiview_random": [],
        "multiview_factor_shuffled": [],
        "multiview_hash_spread": [],
    }
    used_indices: set[int] = set()
    used_digests: set[bytes] = set()

    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            source = _bucket_indices(candidate, view, action)
            available = [
                index
                for index in _unique_feature_order(
                    source,
                    candidate_digests,
                    seed + 10_000 + view * ACTION_COUNT + action,
                )
                if candidate_digests[index] not in used_digests
            ]
            quota = quota_by_view_action[(view, action)]
            chosen = available[:quota]
            if len(chosen) != quota:
                raise HashSpreadError("random arm exhausted unique feature support")
            selected_indices["multiview_random"].extend(chosen)
            used_indices.update(chosen)
            used_digests.update(candidate_digests[index] for index in chosen)

    shuffled_signatures = factor_signatures.clone()
    shuffled_available: dict[tuple[int, int], list[int]] = {}
    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            available = [
                index
                for index in _unique_feature_order(
                    _bucket_indices(candidate, view, action),
                    candidate_digests,
                    seed + 25_000 + view * ACTION_COUNT + action,
                )
                if index not in used_indices
                and candidate_digests[index] not in used_digests
            ]
            shuffled_available[(view, action)] = available
            generator = torch.Generator(device="cpu")
            generator.manual_seed(seed + 30_000 + view * ACTION_COUNT + action)
            bucket = torch.tensor(available, dtype=torch.int64)
            for column in range(factor_signatures.shape[1]):
                permutation = torch.randperm(len(available), generator=generator)
                shuffled_signatures[bucket, column] = factor_signatures[
                    bucket[permutation], column
                ]

    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            chosen = _balanced_select(
                shuffled_available[(view, action)],
                shuffled_signatures,
                quota_by_view_action[(view, action)],
                seed=seed + 40_000 + view * ACTION_COUNT + action,
            )
            selected_indices["multiview_factor_shuffled"].extend(chosen)
            used_indices.update(chosen)
            used_digests.update(candidate_digests[index] for index in chosen)

    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            available = [
                index
                for index in _unique_feature_order(
                    _bucket_indices(candidate, view, action),
                    candidate_digests,
                    seed + 50_000 + view * ACTION_COUNT + action,
                )
                if index not in used_indices
                and candidate_digests[index] not in used_digests
            ]
            chosen = _balanced_select(
                available,
                hash_signatures,
                quota_by_view_action[(view, action)],
                seed=seed + 60_000 + view * ACTION_COUNT + action,
            )
            selected_indices["multiview_hash_spread"].extend(chosen)
            used_indices.update(chosen)
            used_digests.update(candidate_digests[index] for index in chosen)

    banks = {
        "static_unique": static,
        **{
            name: _subset_bank(name, candidate, indices)
            for name, indices in selected_indices.items()
        },
    }
    if any(bank.features.shape != (total, FEATURE_WIDTH) for bank in banks.values()):
        raise HashSpreadError("selected data arm changed the matched row shape")
    if any(not torch.isfinite(bank.features).all() for bank in banks.values()):
        raise HashSpreadError("selected data contains non-finite features")

    quota_tables = {
        name: _quota_table(bank)
        for name, bank in banks.items()
        if name != "static_unique"
    }
    if len({json.dumps(value, sort_keys=True) for value in quota_tables.values()}) != 1:
        raise HashSpreadError("multi-view arms do not share view/action quotas")
    overlap = {
        f"{left}|{right}": len(
            set(selected_indices[left]) & set(selected_indices[right])
        )
        for left_index, left in enumerate(selected_indices)
        for right in tuple(selected_indices)[left_index + 1 :]
    }
    if any(overlap.values()):
        raise HashSpreadError("multi-view selected banks overlap")
    feature_overlap = {
        f"{left}|{right}": len(
            _feature_row_hashes(banks[left]) & _feature_row_hashes(banks[right])
        )
        for left_index, left in enumerate(selected_indices)
        for right in tuple(selected_indices)[left_index + 1 :]
    }
    if any(feature_overlap.values()):
        raise HashSpreadError("selected arms contain exact duplicate feature rows")

    factor_names = ["x".join(names) for names in FACTOR_PRODUCTS]
    hash_names = [f"hash-{column}" for column in range(len(widths))]
    true_factor_coverage = {
        name: _signature_coverage_report(
            indices,
            candidate,
            factor_signatures,
            column_names=factor_names,
        )
        for name, indices in selected_indices.items()
    }
    hash_coverage = {
        name: _signature_coverage_report(
            indices,
            candidate,
            hash_signatures,
            column_names=hash_names,
        )
        for name, indices in selected_indices.items()
    }
    hash_score = hash_coverage["multiview_hash_spread"]["mean_entropy_evenness"]
    intervention_verified = hash_score > max(
        hash_coverage["multiview_random"]["mean_entropy_evenness"],
        hash_coverage["multiview_factor_shuffled"]["mean_entropy_evenness"],
    )
    if not intervention_verified:
        raise HashSpreadError(
            "hash selector did not improve conditional hash-space coverage"
        )

    body: dict[str, Any] = {
        "schema": SELECTION_SCHEMA,
        "held_sector": held_sector,
        "seed": seed,
        "rows_per_view": rows_per_view,
        "candidate_rows_per_view": candidate_rows_per_view,
        "candidate_manifest_sha256": candidate.manifest_sha256,
        "factor_products": [list(names) for names in FACTOR_PRODUCTS],
        "factor_cell_widths": widths,
        "hash_contract": {
            "algorithm": "SHA-256",
            "payload": "domain || signed-data-seed || column || feature-row-digest",
            "label_used_in_hash": False,
            "holdout_used_in_hash": False,
        },
        "selected_index_sha256": {
            name: tensor_sha256(torch.tensor(indices, dtype=torch.int64))
            for name, indices in selected_indices.items()
        },
        "bank_manifest_sha256": {
            name: bank.manifest_sha256 for name, bank in banks.items()
        },
        "view_action_quotas": quota_tables,
        "selected_index_overlap": overlap,
        "exact_feature_overlap": feature_overlap,
        "true_factor_coverage": true_factor_coverage,
        "hash_space_coverage": hash_coverage,
        "intervention_verified": intervention_verified,
        "holdout_used_for_selection": False,
        "reward_or_post_outcome_used_for_selection": False,
    }
    return banks, candidate, {**body, "selection_sha256": sha256_json(body)}


def _two_pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        raise HashSpreadError("stratified gate needs at least two seeds")
    return 2.0 * math.sqrt(
        (statistics.variance(left) + statistics.variance(right)) / 2.0
    )


def evaluate_hash_spread_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the locked factor-specificity gate without granting authority."""

    configuration = result.get("configuration")
    horses = result.get("horses")
    if not isinstance(configuration, Mapping) or not isinstance(horses, list):
        raise HashSpreadError("producer result is incomplete")
    primary = str(configuration.get("primary_arm", ""))
    controls = tuple(str(value) for value in configuration.get("controls", ()))
    arms = tuple(str(value) for value in configuration.get("arms", ()))
    if primary != PRIMARY_ARM or controls != CONTROLS or arms != ARMS:
        raise HashSpreadError("producer comparison differs from preregistration")
    source_body = {
        key: value for key, value in result.items() if key != "result_sha256"
    }
    if sha256_json(source_body) != result.get("result_sha256"):
        raise HashSpreadError("producer result receipt does not verify")
    held_sectors = tuple(int(value) for value in configuration["held_sectors"])
    if len(held_sectors) != 3 or len(set(held_sectors)) != 3:
        raise HashSpreadError("hash-spread gate requires three held sectors")
    floor = 2.0 / math.sqrt(int(configuration["evaluation_records"]))
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
            candidate = {int(row["seed"]): row for row in candidate_rows}
            baseline = {int(row["seed"]): row for row in control_rows}
            if (
                set(candidate) != set(baseline)
                or len(candidate) != len(candidate_rows)
                or not candidate
            ):
                raise HashSpreadError("matched gate seeds differ")
            metrics: dict[str, Any] = {}
            for metric in ("accuracy", "stable_macro_f1"):
                left = [
                    float(candidate[seed]["holdout"][metric])
                    for seed in sorted(candidate)
                ]
                right = [
                    float(baseline[seed]["holdout"][metric])
                    for seed in sorted(baseline)
                ]
                delta = statistics.fmean(left) - statistics.fmean(right)
                required = max(_two_pooled_sd(left, right), floor)
                paired = [a - b for a, b in zip(left, right, strict=True)]
                metrics[metric] = {
                    "candidate_mean": statistics.fmean(left),
                    "control_mean": statistics.fmean(right),
                    "delta": delta,
                    "required_delta": required,
                    "positive": delta > 0.0,
                    "clears_gate": delta > required,
                    "matched_wins": sum(value > 0.0 for value in paired),
                    "matched_ties": sum(value == 0.0 for value in paired),
                    "matched_losses": sum(value < 0.0 for value in paired),
                }
            candidate_anchor = statistics.fmean(
                float(row["anchor"]["accuracy"]) for row in candidate_rows
            )
            control_anchor = statistics.fmean(
                float(row["anchor"]["accuracy"]) for row in control_rows
            )
            sectors[str(held)] = {
                "metrics": metrics,
                "anchor_delta": candidate_anchor - control_anchor,
                "retention_within_two_points": candidate_anchor
                >= control_anchor - 0.02,
            }
        metric_gate = {
            metric: {
                "positive_in_every_sector": all(
                    row["metrics"][metric]["positive"] for row in sectors.values()
                ),
                "clear_sector_count": sum(
                    row["metrics"][metric]["clears_gate"] for row in sectors.values()
                ),
            }
            for metric in ("accuracy", "stable_macro_f1")
        }
        passed = all(
            row["positive_in_every_sector"] and row["clear_sector_count"] >= 2
            for row in metric_gate.values()
        ) and all(row["retention_within_two_points"] for row in sectors.values())
        comparisons[control] = {
            "sectors": sectors,
            "gate": metric_gate,
            "passes": passed,
        }
    passed = all(row["passes"] for row in comparisons.values())
    body: dict[str, Any] = {
        "schema": GATE_SCHEMA,
        "source_result_sha256": result["result_sha256"],
        "primary_arm": primary,
        "controls": list(controls),
        "held_sectors": list(held_sectors),
        "finite_evaluation_floor": floor,
        "comparisons": comparisons,
        "verdict": (
            "PASS_SHUFFLED_OVER_HASH_MECHANICS_NO_PROMOTION"
            if passed
            else "NO_SELECTION"
        ),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "gate_sha256": sha256_json(body)}


def render_hash_spread_gate(report: Mapping[str, Any]) -> str:
    lines = [
        "# Clay shuffled-factor versus hash-spread gate",
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
                f"| {control} | {held} | {accuracy['delta']:.4f} / "
                f"{accuracy['required_delta']:.4f} | {stable['delta']:.4f} / "
                f"{stable['required_delta']:.4f} | "
                f"{'yes' if sector['retention_within_two_points'] else 'no'} |"
            )
    lines.extend(
        (
            "",
            "This factor-specificity gate never promotes weights or authorizes partial unfreeze.",
            "",
        )
    )
    return "\n".join(lines)


def run_hash_spread_campaign(
    output: str | Path,
    provider: DataProvider,
    *,
    seeds: Sequence[int] = (419, 431, 443, 457, 461),
    held_sectors: Sequence[int] = (1, 4, 7),
    rows_per_view: int = 10_000,
    candidate_rows_per_view: int = 60_000,
    evaluation_records: int = 10_000,
    steps: int = 4_800,
    batch_size: int = 192,
    learning_rate: float = 0.001,
    weight_decay: float = 0.0001,
    log_every: int = 200,
    hidden_width: int = 64,
    device_name: str = "auto",
    data_seed_offset: int = 6_000_000,
    evaluation_min_class_support: int = 32,
) -> dict[str, Any]:
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if len(seeds) < 2 or len(held_sectors) != 3:
        raise HashSpreadError("campaign requires multiple seeds and three folds")
    if batch_size < 1 or steps < 1 or evaluation_records < 1:
        raise HashSpreadError("campaign dimensions must be positive")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise HashSpreadError("CUDA was requested but is unavailable")
    device = torch.device(
        "cuda"
        if device_name == "cuda"
        or (device_name == "auto" and torch.cuda.is_available())
        else "cpu"
    )
    configuration = {
        "arms": list(ARMS),
        "primary_arm": PRIMARY_ARM,
        "controls": list(CONTROLS),
        "seeds": list(seeds),
        "held_sectors": list(held_sectors),
        "rows_per_view": rows_per_view,
        "records_per_arm": rows_per_view * VIEW_COUNT,
        "candidate_rows_per_view": candidate_rows_per_view,
        "evaluation_records": evaluation_records,
        "steps": steps,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "log_every": log_every,
        "hidden_width": hidden_width,
        "device": str(device),
        "data_seed_offset": data_seed_offset,
        "evaluation_min_class_support": evaluation_min_class_support,
    }
    campaign_body: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": utc_now(),
        "configuration": configuration,
        "source_hashes": dict(provider.source_hashes),
        "implementation_sha256": file_sha256(Path(__file__).resolve()),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    campaign = {**campaign_body, "campaign_sha256": sha256_json(campaign_body)}
    campaign_path = root / "CAMPAIGN.json"
    if campaign_path.is_file():
        existing = json.loads(campaign_path.read_text(encoding="utf-8"))
        comparable = dict(existing)
        comparable.pop("created_at_utc", None)
        comparable.pop("campaign_sha256", None)
        expected = dict(campaign)
        expected.pop("created_at_utc", None)
        expected.pop("campaign_sha256", None)
        if comparable != expected:
            raise HashSpreadError("existing hash-spread campaign differs")
        campaign = existing
    else:
        _atomic_json(campaign_path, campaign)

    fold_data: dict[
        int, tuple[dict[str, OrbitBank], OrbitBank, OrbitBank, OrbitBank]
    ] = {}
    manifests: dict[str, Any] = {}
    selections: dict[str, Any] = {}
    for held in held_sectors:
        data_seed = 2026111300 + int(held) + data_seed_offset
        banks, candidate, selection = build_hash_spread_data_arms(
            provider,
            held_sector=int(held),
            rows_per_view=rows_per_view,
            candidate_rows_per_view=candidate_rows_per_view,
            seed=data_seed,
        )
        holdout, anchor = build_evaluation_banks(
            provider,
            held_sector=int(held),
            count=evaluation_records,
            seed=data_seed,
        )
        paired_probe = _collect_paired_probe(
            provider,
            held_sector=int(held),
            groups=64,
            seed=data_seed + 500_003,
        )
        evaluation_rows = _feature_row_hashes(holdout) | _feature_row_hashes(anchor)
        if any(_feature_row_hashes(bank) & evaluation_rows for bank in banks.values()):
            raise HashSpreadError("selected training data overlaps evaluation")
        folder = root / "inputs" / f"held-{held}"
        all_banks = {
            **banks,
            "candidate_pool": candidate,
            "paired_probe": paired_probe,
            "holdout": holdout,
            "anchor": anchor,
        }
        for name, bank in all_banks.items():
            path = folder / f"{name}.pt"
            if not path.is_file():
                _save_bank(path, bank)
        selection_path = folder / "SELECTION.json"
        if not selection_path.is_file():
            _atomic_json(selection_path, selection)
        manifests[str(held)] = {
            name: bank.manifest_sha256 for name, bank in all_banks.items()
        }
        selections[str(held)] = selection["selection_sha256"]
        fold_data[int(held)] = (banks, paired_probe, holdout, anchor)
    _atomic_json(root / "DATASET_MANIFESTS.json", manifests)
    _atomic_json(root / "SELECTION_MANIFESTS.json", selections)

    horses: list[dict[str, Any]] = []
    total = len(held_sectors) * len(ARMS) * len(seeds)
    for held in held_sectors:
        banks, paired_probe, holdout, anchor = fold_data[int(held)]
        for arm in ARMS:
            for seed in seeds:
                _atomic_json(
                    root / "ACTIVE_HORSE.json",
                    {
                        "schema": "clay.multiview-hash-spread-active.v1",
                        "updated_at_utc": utc_now(),
                        "completed": len(horses),
                        "total": total,
                        "held_sector": held,
                        "arm": arm,
                        "seed": seed,
                    },
                )
                horses.append(
                    train_horse(
                        root,
                        held_sector=int(held),
                        arm=arm,
                        seed=int(seed),
                        bank=banks[arm],
                        paired_probe=paired_probe,
                        holdout=holdout,
                        anchor=anchor,
                        steps=steps,
                        batch_size=batch_size,
                        learning_rate=learning_rate,
                        weight_decay=weight_decay,
                        log_every=log_every,
                        hidden_width=hidden_width,
                        device=device,
                        evaluation_min_class_support=evaluation_min_class_support,
                    )
                )
                _atomic_json(
                    root / "STATUS.json",
                    {
                        "schema": "clay.multiview-hash-spread-status.v1",
                        "updated_at_utc": utc_now(),
                        "state": "RUNNING",
                        "completed": len(horses),
                        "total": total,
                        "promotion_authorized": False,
                    },
                )

    aggregate_result = aggregate(
        horses,
        arms=ARMS,
        primary_arm=PRIMARY_ARM,
        controls=CONTROLS,
    )
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "campaign_sha256": campaign["campaign_sha256"],
        "state": "COMPLETE_MECHANICS_NO_PROMOTION",
        "configuration": configuration,
        "dataset_manifests": manifests,
        "selection_manifests": selections,
        "horses": horses,
        "aggregate": aggregate_result,
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    result = {**body, "result_sha256": sha256_json(body)}
    _atomic_json(root / "RESULT.json", result)
    _atomic_text(root / "MARKET_REPORT.md", render_market(result))
    gate = evaluate_hash_spread_gate(result)
    _atomic_json(root / "STRATIFIED_GATE.json", gate)
    _atomic_text(root / "STRATIFIED_GATE.md", render_hash_spread_gate(gate))
    _atomic_json(
        root / "STATUS.json",
        {
            "schema": "clay.multiview-hash-spread-status.v1",
            "updated_at_utc": utc_now(),
            "state": result["state"],
            "completed": total,
            "total": total,
            "producer_verdict": aggregate_result["verdict"],
            "stratified_verdict": gate["verdict"],
            "result_sha256": result["result_sha256"],
            "gate_sha256": gate["gate_sha256"],
            "promotion_authorized": False,
            "partial_unfreeze_authorized": False,
        },
    )
    return result


__all__ = [
    "ARMS",
    "CONTROLS",
    "HashSpreadError",
    "PRIMARY_ARM",
    "build_hash_spread_data_arms",
    "evaluate_hash_spread_gate",
    "hash_code_matrix",
    "render_hash_spread_gate",
    "run_hash_spread_campaign",
]
