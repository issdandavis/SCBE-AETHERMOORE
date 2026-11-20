from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

import vqcc_task as task


def _example(index: int, count: int, family: str, record_prefix: str = "record") -> task.GateCountExample:
    opcodes = [0x01] * 32
    for position in range(count):
        opcodes[position] = (0x30, 0x31, 0x32, 0xB0, 0xB1, 0xB2)[position % 6]
    return task.GateCountExample(f"{record_prefix}-{index:03d}", family, tuple(opcodes), count)


def _pool(family_prefix: str = "family", record_prefix: str | None = None) -> list[task.GateCountExample]:
    rows = []
    index = 0
    record_prefix = record_prefix or family_prefix
    for count in range(4):
        for member in range(8):
            rows.append(_example(index, count, f"{family_prefix}-{member % 4}", record_prefix))
            index += 1
    return rows


def test_parse_gate_count_row_independently_recounts_opcodes() -> None:
    opcodes = [0x30, 0x01, 0xB2, 0x02] + [0x03] * 28
    row = {
        "record_id": "abc",
        "lane": "public.gate_count",
        "question": "How many?\n" + " ".join(f"{value:02x}" for value in opcodes),
        "answer": "2",
    }
    parsed = task.parse_gate_count_row(row, family_id="circuit-family-1")
    assert parsed.count == 2
    assert len(parsed.opcodes) == 32
    with pytest.raises(ValueError, match="answer differs"):
        task.parse_gate_count_row({**row, "answer": "3"}, family_id="circuit-family-1")


def test_balanced_comparisons_are_deterministic_constant_length_and_exact() -> None:
    first = task.build_balanced_comparisons(_pool(), seed=19, per_label=4)
    second = task.build_balanced_comparisons(_pool(), seed=19, per_label=4)
    assert first == second
    assert Counter(row.target for row in first) == {"A": 4, "B": 4, "T": 4}
    assert len({len(row.prompt) for row in first}) == 1
    assert all(len(row.target) == 1 for row in first)
    assert all(row.a_record_id != row.b_record_id for row in first)
    report = task.task_set_report(first)
    assert report["unique_records"] == 24
    assert report["maximum_record_reuse"] == 1
    assert report["gap_distribution_by_label"]["A"] == report["gap_distribution_by_label"]["B"]


def test_prespecified_gap_strata_match_between_a_and_b() -> None:
    rows = task.build_balanced_comparisons(
        _pool(), seed=5, per_label=4, gap_strata=(1, 2)
    )
    gaps = task.task_set_report(rows)["gap_distribution_by_label"]
    assert gaps["A"] == {1: 2, 2: 2}
    assert gaps["B"] == gaps["A"]


def test_family_disjoint_gate_rejects_family_or_record_leakage() -> None:
    train = task.build_balanced_comparisons(_pool("train"), seed=1, per_label=2)
    holdout = task.build_balanced_comparisons(_pool("holdout"), seed=2, per_label=2)
    task.validate_family_disjoint(train, holdout)
    leaked = task.build_balanced_comparisons(
        _pool("train", record_prefix="leaked-holdout"), seed=2, per_label=2
    )
    with pytest.raises(ValueError, match="leakage"):
        task.validate_family_disjoint(train, leaked)


def test_comparison_validation_recounts_and_rehashes_every_field() -> None:
    row = task.build_balanced_comparisons(_pool(), seed=3, per_label=2)[0]
    with pytest.raises(ValueError, match="counts differ"):
        task.validate_comparison(replace(row, a_count=row.a_count + 1))
    changed = list(row.a_opcodes)
    position = next(index for index, opcode in enumerate(changed) if opcode not in task.TOFFOLI_OPCODES)
    changed[position] = 0x02 if changed[position] != 0x02 else 0x03
    with pytest.raises(ValueError, match="identity differs"):
        task.validate_comparison(replace(row, a_opcodes=tuple(changed)))
    with pytest.raises(ValueError, match="families"):
        task.validate_comparison(replace(row, family_ids=("",)))
    with pytest.raises(ValueError, match="distinct"):
        task.validate_comparison(replace(row, a_record_id=row.b_record_id))
    wrong = next(label for label in task.LABELS if label != row.target)
    with pytest.raises(ValueError, match="target differs"):
        task.validate_comparison(replace(row, target=wrong))


def test_shuffled_binding_is_one_to_one_deranged_and_marginal_preserving() -> None:
    rows = task.build_balanced_comparisons(_pool(), seed=7, per_label=5)
    shuffled = task.shuffled_binding(rows, seed=31)
    original = sorted(rows, key=lambda row: row.pair_id)
    assert Counter(row.target for row in shuffled) == Counter(row.target for row in original)
    assert all(before.target != after.target for before, after in zip(original, shuffled))
    assert len({row.target_source_id for row in shuffled}) == len(rows)


def test_metrics_do_not_reward_majority_or_output_length() -> None:
    rows = task.build_balanced_comparisons(_pool(), seed=4, per_label=5)
    majority = task.score_predictions(rows, {row.pair_id: "A" for row in rows})
    oracle = task.score_predictions(rows, {row.pair_id: row.target for row in rows})
    assert majority["exact_accuracy"] == pytest.approx(1 / 3)
    assert majority["balanced_exact_accuracy"] == pytest.approx(1 / 3)
    assert majority["majority_baseline_accuracy"] == pytest.approx(1 / 3)
    assert oracle["exact_accuracy"] == 1.0
    assert oracle["mean_selection_regret_toffoli"] == 0.0


def test_natural_prevalence_population_is_separate_and_record_unique() -> None:
    rows = task.build_natural_prevalence_comparisons(_pool(), seed=91, max_rows=12)
    report = task.task_set_report(rows)
    assert report["unique_records"] == 24
    assert report["maximum_record_reuse"] == 1
    scored = task.score_natural_prevalence_predictions(
        rows, {row.pair_id: row.target for row in rows}
    )
    assert scored["evaluation_population"] == "natural_prevalence_once_paired"
    assert scored["natural_prevalence_accuracy"] == 1.0
    assert sum(scored["natural_label_prevalence"].values()) == pytest.approx(1.0)


def test_standard_arms_and_campaign_promotion_gate() -> None:
    specs = task.standard_arm_specs(trainable_parameters=142_164, updates=18_000)
    assert specs["equal_parameter"].trainable_parameters == specs["candidate"].trainable_parameters
    assert specs["shuffled_binding"].updates == specs["candidate"].updates
    result = task.judge_campaign(
        {
            "candidate": [0.81, 0.82, 0.80],
            "no_intervention": [0.34, 0.35, 0.33],
            "equal_parameter": [0.46, 0.45, 0.47],
            "shuffled_binding": [0.33, 0.34, 0.32],
            "zero_update": [0.35, 0.34, 0.36],
        },
        seed_ids=["seed-11", "seed-29", "seed-47"],
        retention_exact=[True, True, True],
    )
    assert result["verdict"] == "PROMOTE"
    underpowered = task.judge_campaign(
        {
            "candidate": [0.51, 0.61, 0.41],
            "no_intervention": [0.45, 0.46, 0.44],
            "equal_parameter": [0.45, 0.46, 0.44],
            "shuffled_binding": [0.34, 0.35, 0.33],
            "zero_update": [0.35, 0.36, 0.34],
        },
        seed_ids=["seed-11", "seed-29", "seed-47"],
        retention_exact=[True, True, True],
    )
    assert underpowered["verdict"] == "UNDERPOWERED"


def test_campaign_gate_rejects_repeated_seeds_and_invalid_scores() -> None:
    scores = {
        "candidate": [0.8, 0.8, 0.8],
        "no_intervention": [0.3, 0.3, 0.3],
        "equal_parameter": [0.4, 0.4, 0.4],
        "shuffled_binding": [0.3, 0.3, 0.3],
        "zero_update": [0.3, 0.3, 0.3],
    }
    with pytest.raises(ValueError, match="unique"):
        task.judge_campaign(
            scores,
            seed_ids=["same", "same", "other"],
            retention_exact=[True, True, True],
        )
    invalid = {**scores, "candidate": [0.8, float("nan"), 0.8]}
    with pytest.raises(ValueError, match="non-finite"):
        task.judge_campaign(
            invalid,
            seed_ids=["one", "two", "three"],
            retention_exact=[True, True, True],
        )
