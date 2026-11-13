"""Factor-covered multi-view data selection for the Clay action learner.

This module changes the training support, not the model.  It selects three
row-disjoint multi-view banks from one training-only candidate pool while
holding view/action quotas fixed.  The proposed bank balances declared factor
products; the shuffled arm runs the same selector after breaking the binding
between those products and physical rows.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor

from python.scbe.clay_paired_orbit_training import (
    ACTION_COUNT,
    FEATURE_WIDTH,
    VIEW_COUNT,
    DataProvider,
    OrbitBank,
    PairedOrbitError,
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
from python.scbe.training_data_coverage import TensorBundle, derive_factors

SCHEMA = "clay.multiview-factor-coverage-campaign.v1"
SELECTION_SCHEMA = "clay.multiview-factor-selection.v1"
GATE_SCHEMA = "clay.multiview-factor-stratified-gate.v1"

ARMS = (
    "static_unique",
    "multiview_random",
    "multiview_factor",
    "multiview_factor_shuffled",
)
PRIMARY_ARM = "multiview_factor"
CONTROLS = (
    "static_unique",
    "multiview_random",
    "multiview_factor_shuffled",
)

FACTOR_PRODUCTS: tuple[tuple[str, ...], ...] = (
    ("phase", "drive", "target"),
    ("phase", "target"),
    ("drive", "target"),
    ("position_x_bin", "position_y_bin"),
    ("velocity_x_bin", "velocity_y_bin"),
    ("scope_sign_x", "scope_sign_y"),
    ("memory_slots", "stagnation_ticks"),
    ("memory_slots", "outburst_ticks"),
)


class FactorCoverageError(PairedOrbitError):
    """Raised when the factor-data intervention violates its controls."""


def _memory_bundle(bank: OrbitBank) -> TensorBundle:
    return TensorBundle(
        path=Path("<memory>"),
        features=bank.features,
        labels=bank.labels,
        sectors=bank.sectors,
        reward_values=torch.zeros((bank.features.shape[0], 1), dtype=torch.float32),
        file_sha256="",
    )


def factor_code_matrix(bank: OrbitBank) -> tuple[Tensor, list[list[list[int]]]]:
    """Encode each declared factor product as a deterministic integer cell."""

    factors = derive_factors(_memory_bundle(bank))
    columns: list[Tensor] = []
    tables: list[list[list[int]]] = []
    for names in FACTOR_PRODUCTS:
        matrix = torch.stack([factors[name] for name in names], dim=1)
        cells, inverse = torch.unique(matrix, sorted=True, return_inverse=True, dim=0)
        columns.append(inverse.to(torch.int64))
        tables.append(cells.to(torch.int64).tolist())
    return torch.stack(columns, dim=1), tables


def _stable_order(indices: Sequence[int], seed: int) -> list[int]:
    return sorted(
        (int(index) for index in indices),
        key=lambda index: hashlib.sha256(f"{seed}:{index}".encode("ascii")).digest(),
    )


def _balanced_select(
    indices: Sequence[int],
    signatures: Tensor,
    count: int,
    *,
    seed: int,
) -> list[int]:
    """Greedily flatten observed factor-cell counts without replacement."""

    source = [int(value) for value in indices]
    if count < 0 or count > len(source):
        raise FactorCoverageError("factor selection quota exceeds its candidate bucket")
    if count == 0:
        return []
    ordered = _stable_order(source, seed)
    rank = {index: position for position, index in enumerate(ordered)}
    cell_rows: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index in ordered:
        for factor, cell in enumerate(signatures[index].tolist()):
            cell_rows[(factor, int(cell))].append(index)
    pointers = {key: 0 for key in cell_rows}
    selected: set[int] = set()
    counts: Counter[tuple[int, int]] = Counter()

    while len(selected) < count:
        active: list[tuple[int, int]] = []
        for key, rows in cell_rows.items():
            pointer = pointers[key]
            while pointer < len(rows) and rows[pointer] in selected:
                pointer += 1
            pointers[key] = pointer
            if pointer < len(rows):
                active.append(key)
        if not active:
            break
        focus = min(active, key=lambda key: (counts[key], key[0], key[1]))
        rows = cell_rows[focus]
        candidates: list[int] = []
        cursor = pointers[focus]
        while cursor < len(rows) and len(candidates) < 32:
            index = rows[cursor]
            if index not in selected:
                candidates.append(index)
            cursor += 1
        if not candidates:
            pointers[focus] = cursor
            continue

        def score(index: int) -> tuple[float, int]:
            cells = signatures[index].tolist()
            coverage = sum(
                1.0 / (1.0 + counts[(factor, int(cell))])
                for factor, cell in enumerate(cells)
            )
            return coverage, -rank[index]

        chosen = max(candidates, key=score)
        selected.add(chosen)
        for factor, cell in enumerate(signatures[chosen].tolist()):
            counts[(factor, int(cell))] += 1

    if len(selected) < count:
        selected.update(index for index in ordered if index not in selected)
    result = sorted(selected, key=rank.__getitem__)[:count]
    if len(result) != count or len(set(result)) != count:
        raise FactorCoverageError("factor selector did not produce a unique quota")
    return result


def _subset_bank(name: str, source: OrbitBank, indices: Sequence[int]) -> OrbitBank:
    rows = []
    for group, index in enumerate(indices):
        rows.append(
            (
                source.features[index],
                int(source.labels[index]),
                int(source.sectors[index]),
                group,
                int(source.views[index]),
            )
        )
    return make_bank(name, rows, complete_groups=False)


def _quota_table(bank: OrbitBank) -> dict[str, int]:
    counts = Counter(
        (int(view), int(action))
        for view, action in zip(bank.views.tolist(), bank.labels.tolist(), strict=True)
    )
    return {
        f"view-{view}:action-{action}": counts[(view, action)]
        for view in range(VIEW_COUNT)
        for action in range(ACTION_COUNT)
    }


def _three_arm_quotas(counts: Sequence[int], total: int) -> list[int]:
    """Allocate natural-distribution quotas feasible for three disjoint arms."""

    available = [int(value) for value in counts]
    capacities = [value // 3 for value in available]
    if total < 1 or sum(capacities) < total or sum(available) < 1:
        raise FactorCoverageError("candidate action support cannot fill three arms")
    population = sum(available)
    desired = [total * value / population for value in available]
    quotas = [
        min(capacity, int(math.floor(target)))
        for capacity, target in zip(capacities, desired, strict=True)
    ]
    while sum(quotas) < total:
        choices = [
            index
            for index, capacity in enumerate(capacities)
            if quotas[index] < capacity
        ]
        if not choices:
            raise FactorCoverageError("candidate quota allocation exhausted capacity")
        chosen = max(
            choices,
            key=lambda index: (
                desired[index] - quotas[index],
                available[index],
                -index,
            ),
        )
        quotas[chosen] += 1
    return quotas


def _entropy_evenness(counts: Sequence[int]) -> float:
    total = sum(int(value) for value in counts)
    support = len(counts)
    if total <= 0 or support <= 1:
        return 1.0
    probabilities = [value / total for value in counts if value]
    entropy = -sum(value * math.log(value) for value in probabilities)
    return entropy / math.log(support)


def _coverage_report(
    indices: Sequence[int],
    candidate: OrbitBank,
    signatures: Tensor,
) -> dict[str, Any]:
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
            for factor_index, names in enumerate(FACTOR_PRODUCTS):
                candidate_cells = torch.unique(
                    signatures[candidate_indices, factor_index]
                )
                selected_counts = Counter(
                    int(value) for value in signatures[chosen, factor_index].tolist()
                )
                counts = [
                    selected_counts[int(cell)] for cell in candidate_cells.tolist()
                ]
                rows.append(
                    {
                        "view": view,
                        "action": action,
                        "factor_product": "x".join(names),
                        "candidate_cells": len(counts),
                        "selected_cells": sum(value > 0 for value in counts),
                        "coverage_ratio": (
                            sum(value > 0 for value in counts) / len(counts)
                            if counts
                            else 1.0
                        ),
                        "entropy_evenness": _entropy_evenness(counts),
                        "min_count": min(counts) if counts else 0,
                        "max_count": max(counts) if counts else 0,
                    }
                )
    nonempty = [row for row in rows if row["candidate_cells"] > 1]
    return {
        "conditional_tables": len(rows),
        "nontrivial_tables": len(nonempty),
        "mean_coverage_ratio": statistics.fmean(
            row["coverage_ratio"] for row in nonempty
        ),
        "mean_entropy_evenness": statistics.fmean(
            row["entropy_evenness"] for row in nonempty
        ),
        "minimum_coverage_ratio": min(row["coverage_ratio"] for row in nonempty),
        "tables": rows,
    }


def _feature_row_hashes(bank: OrbitBank) -> set[bytes]:
    matrix = bank.features.detach().cpu().contiguous().numpy()
    return {hashlib.sha256(row.tobytes()).digest() for row in matrix}


def _feature_row_digests(bank: OrbitBank) -> list[bytes]:
    matrix = bank.features.detach().cpu().contiguous().numpy()
    return [hashlib.sha256(row.tobytes()).digest() for row in matrix]


def _unique_feature_order(
    indices: Sequence[int], digests: Sequence[bytes], seed: int
) -> list[int]:
    result: list[int] = []
    seen: set[bytes] = set()
    for index in _stable_order(indices, seed):
        digest = digests[index]
        if digest in seen:
            continue
        seen.add(digest)
        result.append(index)
    return result


def _collect_candidate_bank(
    provider: DataProvider,
    *,
    held_sector: int,
    rows_per_view: int,
    seed: int,
) -> OrbitBank:
    rows = []
    for view, sandbox in enumerate(provider.training_sandboxes()):
        view_rows = _collect_rows(
            provider,
            sandbox,
            count=rows_per_view,
            held_sector=held_sector,
            include_held=False,
            seed=seed + 1009 * (view + 1),
            view=view,
        )
        rows.extend(
            (feature, label, sector, group + view * rows_per_view, view)
            for feature, label, sector, group, _ in view_rows
        )
    return make_bank("candidate_pool", rows, complete_groups=False)


def _collect_paired_probe(
    provider: DataProvider,
    *,
    held_sector: int,
    groups: int,
    seed: int,
) -> OrbitBank:
    """Build a diagnostic-only complete view orbit for gradient coherence."""

    sandboxes = provider.training_sandboxes()
    rng = random.Random(seed)
    rows = []
    attempts = 0
    while len(rows) < groups * VIEW_COUNT and attempts < groups * 192:
        attempts += 1
        state = provider.sample_state(sandboxes[0], rng)
        views = [provider.materialize(sandbox, state) for sandbox in sandboxes]
        if any(sector == held_sector for _, _, sector in views):
            continue
        group = len(rows) // VIEW_COUNT
        for view, (feature, label, sector) in enumerate(views):
            rows.append((feature, label, sector, group, view))
    if len(rows) != groups * VIEW_COUNT:
        raise FactorCoverageError("could not fill the paired diagnostic probe")
    return make_bank("paired_probe", rows, complete_groups=True)


def build_factor_data_arms(
    provider: DataProvider,
    *,
    held_sector: int,
    rows_per_view: int,
    candidate_rows_per_view: int,
    seed: int,
) -> tuple[dict[str, OrbitBank], OrbitBank, dict[str, Any]]:
    """Build matched random, true-factor, and shuffled-factor view banks."""

    if rows_per_view < 1 or candidate_rows_per_view < 3 * rows_per_view:
        raise FactorCoverageError(
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
    signatures, cell_tables = factor_code_matrix(candidate)
    candidate_digests = _feature_row_digests(candidate)

    quota_by_view_action: dict[tuple[int, int], int] = {}
    for view in range(VIEW_COUNT):
        counts = [
            len(
                {
                    candidate_digests[index]
                    for index in torch.nonzero(
                        (candidate.views == view) & (candidate.labels == action),
                        as_tuple=False,
                    )
                    .flatten()
                    .tolist()
                }
            )
            for action in range(ACTION_COUNT)
        ]
        for action, quota in enumerate(_three_arm_quotas(counts, rows_per_view)):
            quota_by_view_action[(view, action)] = quota

    random_indices: list[int] = []
    used_digests: set[bytes] = set()
    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            source = (
                torch.nonzero(
                    (candidate.views == view) & (candidate.labels == action),
                    as_tuple=False,
                )
                .flatten()
                .tolist()
            )
            available = [
                index
                for index in _unique_feature_order(
                    source,
                    candidate_digests,
                    seed + 10_000 + view * ACTION_COUNT + action,
                )
                if candidate_digests[index] not in used_digests
            ]
            chosen = available[: quota_by_view_action[(view, action)]]
            if len(chosen) != quota_by_view_action[(view, action)]:
                raise FactorCoverageError("random arm exhausted unique feature support")
            random_indices.extend(chosen)
            used_digests.update(candidate_digests[index] for index in chosen)
    random_bank = _subset_bank("multiview_random", candidate, random_indices)

    used = set(random_indices)
    factor_indices: list[int] = []
    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            quota = quota_by_view_action[(view, action)]
            bucket = (
                torch.nonzero(
                    (candidate.views == view) & (candidate.labels == action),
                    as_tuple=False,
                )
                .flatten()
                .tolist()
            )
            available = [
                index
                for index in _unique_feature_order(
                    bucket,
                    candidate_digests,
                    seed + 15_000 + view * ACTION_COUNT + action,
                )
                if index not in used and candidate_digests[index] not in used_digests
            ]
            chosen = _balanced_select(
                available,
                signatures,
                quota,
                seed=seed + 20_000 + view * ACTION_COUNT + action,
            )
            factor_indices.extend(chosen)
            used.update(chosen)
            used_digests.update(candidate_digests[index] for index in chosen)

    shuffled_signatures = signatures.clone()
    shuffled_available: dict[tuple[int, int], list[int]] = {}
    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            bucket = (
                torch.nonzero(
                    (candidate.views == view) & (candidate.labels == action),
                    as_tuple=False,
                )
                .flatten()
                .tolist()
            )
            available = [
                index
                for index in _unique_feature_order(
                    bucket,
                    candidate_digests,
                    seed + 25_000 + view * ACTION_COUNT + action,
                )
                if index not in used and candidate_digests[index] not in used_digests
            ]
            shuffled_available[(view, action)] = available
            generator = torch.Generator(device="cpu")
            generator.manual_seed(seed + 30_000 + view * ACTION_COUNT + action)
            bucket_tensor = torch.tensor(available, dtype=torch.int64)
            for factor in range(len(FACTOR_PRODUCTS)):
                permutation = torch.randperm(len(available), generator=generator)
                shuffled_signatures[bucket_tensor, factor] = signatures[
                    bucket_tensor[permutation], factor
                ]

    shuffled_indices: list[int] = []
    for view in range(VIEW_COUNT):
        for action in range(ACTION_COUNT):
            chosen = _balanced_select(
                shuffled_available[(view, action)],
                shuffled_signatures,
                quota_by_view_action[(view, action)],
                seed=seed + 40_000 + view * ACTION_COUNT + action,
            )
            shuffled_indices.extend(chosen)
            used.update(chosen)
            used_digests.update(candidate_digests[index] for index in chosen)

    selected_indices = {
        "multiview_random": random_indices,
        "multiview_factor": factor_indices,
        "multiview_factor_shuffled": shuffled_indices,
    }
    banks = {
        "static_unique": static,
        "multiview_random": random_bank,
        "multiview_factor": _subset_bank("multiview_factor", candidate, factor_indices),
        "multiview_factor_shuffled": _subset_bank(
            "multiview_factor_shuffled", candidate, shuffled_indices
        ),
    }
    if any(bank.features.shape != (total, FEATURE_WIDTH) for bank in banks.values()):
        raise FactorCoverageError("selected data arm changed the matched row shape")
    quota_tables = {
        name: _quota_table(bank)
        for name, bank in banks.items()
        if name != "static_unique"
    }
    if len({json.dumps(value, sort_keys=True) for value in quota_tables.values()}) != 1:
        raise FactorCoverageError("multi-view arms do not share view/action quotas")
    overlap = {
        f"{left}|{right}": len(
            set(selected_indices[left]) & set(selected_indices[right])
        )
        for left_index, left in enumerate(selected_indices)
        for right in tuple(selected_indices)[left_index + 1 :]
    }
    if any(overlap.values()):
        raise FactorCoverageError("multi-view selected banks overlap")
    feature_overlap = {
        f"{left}|{right}": len(
            _feature_row_hashes(banks[left]) & _feature_row_hashes(banks[right])
        )
        for left_index, left in enumerate(selected_indices)
        for right in tuple(selected_indices)[left_index + 1 :]
    }
    if any(feature_overlap.values()):
        raise FactorCoverageError("selected arms contain exact duplicate feature rows")

    coverage = {
        name: _coverage_report(indices, candidate, signatures)
        for name, indices in selected_indices.items()
    }
    factor_score = coverage["multiview_factor"]["mean_entropy_evenness"]
    intervention_verified = factor_score > max(
        coverage["multiview_random"]["mean_entropy_evenness"],
        coverage["multiview_factor_shuffled"]["mean_entropy_evenness"],
    )
    if not intervention_verified:
        raise FactorCoverageError(
            "factor selector did not improve true conditional coverage"
        )

    body: dict[str, Any] = {
        "schema": SELECTION_SCHEMA,
        "held_sector": held_sector,
        "seed": seed,
        "rows_per_view": rows_per_view,
        "candidate_rows_per_view": candidate_rows_per_view,
        "candidate_manifest_sha256": candidate.manifest_sha256,
        "factor_products": [list(names) for names in FACTOR_PRODUCTS],
        "factor_cell_tables": cell_tables,
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
        "coverage": coverage,
        "intervention_verified": intervention_verified,
        "holdout_used_for_selection": False,
        "reward_or_post_outcome_used_for_selection": False,
    }
    return banks, candidate, {**body, "selection_sha256": sha256_json(body)}


def _two_pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        raise FactorCoverageError("stratified gate needs at least two seeds")
    return 2.0 * math.sqrt(
        (statistics.variance(left) + statistics.variance(right)) / 2.0
    )


def evaluate_factor_gate(result: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the frozen sector-wise gate without granting authority."""

    configuration = result.get("configuration")
    horses = result.get("horses")
    if not isinstance(configuration, Mapping) or not isinstance(horses, list):
        raise FactorCoverageError("producer result is incomplete")
    primary_arm = str(configuration.get("primary_arm", ""))
    controls = tuple(str(value) for value in configuration.get("controls", ()))
    configured_arms = tuple(str(value) for value in configuration.get("arms", ()))
    if (
        primary_arm not in ARMS
        or not controls
        or any(control not in ARMS or control == primary_arm for control in controls)
        or set(configured_arms) != {primary_arm, *controls}
        or len(configured_arms) != 1 + len(controls)
    ):
        raise FactorCoverageError("producer comparison differs from preregistration")
    source_body = {
        key: value for key, value in result.items() if key != "result_sha256"
    }
    if sha256_json(source_body) != result.get("result_sha256"):
        raise FactorCoverageError("producer result receipt does not verify")
    held_sectors = tuple(int(value) for value in configuration["held_sectors"])
    if len(held_sectors) != 3 or len(set(held_sectors)) != 3:
        raise FactorCoverageError("factor gate requires three held sectors")
    floor = 2.0 / math.sqrt(int(configuration["evaluation_records"]))
    comparisons: dict[str, Any] = {}
    for control in controls:
        sectors: dict[str, Any] = {}
        for held in held_sectors:
            candidate_rows = [
                row
                for row in horses
                if int(row["held_sector"]) == held and row["arm"] == primary_arm
            ]
            control_rows = [
                row
                for row in horses
                if int(row["held_sector"]) == held and row["arm"] == control
            ]
            candidate = {int(row["seed"]): row for row in candidate_rows}
            baseline = {int(row["seed"]): row for row in control_rows}
            if set(candidate) != set(baseline) or len(candidate) != len(candidate_rows):
                raise FactorCoverageError("matched gate seeds differ")
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
        passes = all(
            row["positive_in_every_sector"] and row["clear_sector_count"] >= 2
            for row in metric_gate.values()
        ) and all(row["retention_within_two_points"] for row in sectors.values())
        comparisons[control] = {
            "sectors": sectors,
            "gate": metric_gate,
            "passes": passes,
        }
    passed = all(row["passes"] for row in comparisons.values())
    body: dict[str, Any] = {
        "schema": GATE_SCHEMA,
        "source_result_sha256": result["result_sha256"],
        "primary_arm": primary_arm,
        "controls": list(controls),
        "held_sectors": list(held_sectors),
        "finite_evaluation_floor": floor,
        "comparisons": comparisons,
        "verdict": (
            (
                "PASS_SHUFFLED_DATA_MECHANICS_NO_PROMOTION"
                if primary_arm == "multiview_factor_shuffled"
                else "PASS_FACTOR_DATA_MECHANICS_NO_PROMOTION"
            )
            if passed
            else "NO_SELECTION"
        ),
        "promotion_authorized": False,
        "partial_unfreeze_authorized": False,
    }
    return {**body, "gate_sha256": sha256_json(body)}


def render_factor_gate(report: Mapping[str, Any]) -> str:
    lines = [
        "# Clay multi-view factor-coverage gate",
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
        (
            "",
            "This mechanics gate never promotes weights or authorizes partial unfreeze.",
            "",
        )
    )
    return "\n".join(lines)


def run_factor_campaign(
    output: str | Path,
    provider: DataProvider,
    *,
    seeds: Sequence[int] = (263, 277, 293, 311, 331),
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
    data_seed_offset: int = 4_000_000,
    evaluation_min_class_support: int = 32,
    arms: Sequence[str] = ARMS,
    primary_arm: str = PRIMARY_ARM,
    controls: Sequence[str] = CONTROLS,
) -> dict[str, Any]:
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    selected_arms = tuple(str(value) for value in arms)
    selected_controls = tuple(str(value) for value in controls)
    if len(seeds) < 2 or len(held_sectors) != 3:
        raise FactorCoverageError("campaign requires multiple seeds and three folds")
    if (
        not selected_arms
        or any(arm not in ARMS for arm in selected_arms)
        or len(set(selected_arms)) != len(selected_arms)
        or primary_arm not in selected_arms
        or len(set(selected_controls)) != len(selected_controls)
        or any(
            control not in selected_arms or control == primary_arm
            for control in selected_controls
        )
        or set(selected_arms) != {primary_arm, *selected_controls}
    ):
        raise FactorCoverageError("campaign comparison arms are invalid")
    if batch_size < 1 or steps < 1 or evaluation_records < 1:
        raise FactorCoverageError("campaign dimensions must be positive")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise FactorCoverageError("CUDA was requested but is unavailable")
    device = torch.device(
        "cuda"
        if device_name == "cuda"
        or (device_name == "auto" and torch.cuda.is_available())
        else "cpu"
    )
    configuration = {
        "arms": list(selected_arms),
        "primary_arm": primary_arm,
        "controls": list(selected_controls),
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
    implementation_path = Path(__file__).resolve()
    campaign_body: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": utc_now(),
        "configuration": configuration,
        "source_hashes": dict(provider.source_hashes),
        "implementation_sha256": file_sha256(implementation_path),
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
            raise FactorCoverageError("existing factor campaign differs")
        campaign = existing
    else:
        _atomic_json(campaign_path, campaign)

    fold_data: dict[
        int, tuple[dict[str, OrbitBank], OrbitBank, OrbitBank, OrbitBank]
    ] = {}
    manifests: dict[str, Any] = {}
    selections: dict[str, Any] = {}
    for held in held_sectors:
        data_seed = 2026111300 + held + data_seed_offset
        banks, candidate, selection = build_factor_data_arms(
            provider,
            held_sector=held,
            rows_per_view=rows_per_view,
            candidate_rows_per_view=candidate_rows_per_view,
            seed=data_seed,
        )
        holdout, anchor = build_evaluation_banks(
            provider,
            held_sector=held,
            count=evaluation_records,
            seed=data_seed,
        )
        paired_probe = _collect_paired_probe(
            provider,
            held_sector=held,
            groups=64,
            seed=data_seed + 500_003,
        )
        held_rows = _feature_row_hashes(holdout)
        anchor_rows = _feature_row_hashes(anchor)
        if any(
            _feature_row_hashes(bank) & (held_rows | anchor_rows)
            for bank in banks.values()
        ):
            raise FactorCoverageError("selected training data overlaps evaluation")
        folder = root / "inputs" / f"held-{held}"
        for name, bank in {
            **banks,
            "candidate_pool": candidate,
            "paired_probe": paired_probe,
            "holdout": holdout,
            "anchor": anchor,
        }.items():
            path = folder / f"{name}.pt"
            if not path.is_file():
                _save_bank(path, bank)
        selection_path = folder / "SELECTION.json"
        if not selection_path.is_file():
            _atomic_json(selection_path, selection)
        manifests[str(held)] = {
            name: bank.manifest_sha256
            for name, bank in {
                **banks,
                "candidate_pool": candidate,
                "paired_probe": paired_probe,
                "holdout": holdout,
                "anchor": anchor,
            }.items()
        }
        selections[str(held)] = selection["selection_sha256"]
        fold_data[int(held)] = (banks, paired_probe, holdout, anchor)
    _atomic_json(root / "DATASET_MANIFESTS.json", manifests)
    _atomic_json(root / "SELECTION_MANIFESTS.json", selections)

    horses: list[dict[str, Any]] = []
    total = len(held_sectors) * len(selected_arms) * len(seeds)
    for held in held_sectors:
        banks, paired_probe, holdout, anchor = fold_data[int(held)]
        for arm in selected_arms:
            for seed in seeds:
                _atomic_json(
                    root / "ACTIVE_HORSE.json",
                    {
                        "schema": "clay.multiview-factor-active.v1",
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
                        "schema": "clay.multiview-factor-status.v1",
                        "updated_at_utc": utc_now(),
                        "state": "RUNNING",
                        "completed": len(horses),
                        "total": total,
                        "promotion_authorized": False,
                    },
                )

    aggregate_result = aggregate(
        horses,
        arms=selected_arms,
        primary_arm=primary_arm,
        controls=selected_controls,
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
    gate = evaluate_factor_gate(result)
    _atomic_json(root / "STRATIFIED_GATE.json", gate)
    _atomic_text(root / "STRATIFIED_GATE.md", render_factor_gate(gate))
    _atomic_json(
        root / "STATUS.json",
        {
            "schema": "clay.multiview-factor-status.v1",
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
    "FACTOR_PRODUCTS",
    "FactorCoverageError",
    "PRIMARY_ARM",
    "build_factor_data_arms",
    "evaluate_factor_gate",
    "factor_code_matrix",
    "render_factor_gate",
    "run_factor_campaign",
]
