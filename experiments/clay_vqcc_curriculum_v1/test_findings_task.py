from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest

from findings_task import (
    aligned_findings_training_arms,
    build_finding_comparisons,
    derange_findings_bindings,
    judge_finding_campaign,
    parse_finding_row,
    score_finding_log_scores,
    score_finding_predictions,
    validate_family_disjoint,
    validate_finding_comparisons,
)


def _example(index: int, *, task: str = "dqi", family: str | None = None, pad: str = ""):
    mechanism = f"mechanism-{index}"
    row = {
        "record_id": f"record-{index}",
        "lane": "public.experimental_findings",
        "question": (
            f"What limitation did the public {task} experiment report for {mechanism}? "
            "Evidence tier: full-verifier."
        ),
        "answer": f"measured limitation {index} {pad}".strip(),
    }
    return parse_finding_row(row, family_id=family or f"family-{index}")


def test_build_is_balanced_and_answer_marginals_are_symmetric() -> None:
    examples = [_example(i, pad="x" * (i % 3)) for i in range(12)]
    rows = build_finding_comparisons(examples, seed=7, length_bucket_width=64)
    assert Counter(row.target for row in rows) == {"A": len(rows) // 2, "B": len(rows) // 2}
    assert len({row.question_record_id for row in rows}) == len(rows)
    role_counts = Counter()
    for row in rows:
        role_counts[(row.a_source_id, "correct" if row.target == "A" else "distractor")] += 1
        role_counts[(row.b_source_id, "correct" if row.target == "B" else "distractor")] += 1
    for source in {source for source, _role in role_counts}:
        assert role_counts[(source, "correct")] == role_counts[(source, "distractor")] == 1


def test_derangement_is_one_to_one_and_changes_every_binding() -> None:
    examples = [_example(i) for i in range(8)]
    shuffled = derange_findings_bindings(examples, seed=11, length_bucket_width=64)
    assert {row.answer_source_id for row in shuffled} == {row.record_id for row in examples}
    assert all(row.record_id != row.answer_source_id for row in shuffled)
    assert Counter(row.task for row in shuffled) == Counter(row.task for row in examples)


def test_aligned_training_arms_drop_ineligible_strata_symmetrically() -> None:
    examples = [_example(i) for i in range(4)]
    singleton = _example(99, task="chemistry", pad="x" * 100)
    candidate, shuffled = aligned_findings_training_arms(
        [*examples, singleton], seed=17, length_bucket_width=32
    )
    assert [row.record_id for row in candidate] == [row.record_id for row in shuffled]
    assert singleton.record_id not in {row.record_id for row in candidate}
    assert all(left.answer_source_id == left.record_id for left in candidate)
    assert all(right.answer_source_id != right.record_id for right in shuffled)


def test_scoring_and_log_score_margin() -> None:
    examples = [
        _example(task_index * 10 + index, task=task)
        for task_index, task in enumerate(("invsqrt", "dqi", "chemistry", "all"))
        for index in range(4)
    ]
    rows = build_finding_comparisons(examples, seed=3, length_bucket_width=64)
    perfect = {row.comparison_id: row.target for row in rows}
    metrics = score_finding_predictions(rows, perfect)
    assert metrics["exact_accuracy"] == 1.0
    scores = {
        row.comparison_id: {
            "A": 2.0 if row.target == "A" else 0.0,
            "B": 2.0 if row.target == "B" else 0.0,
        }
        for row in rows
    }
    ranked = score_finding_log_scores(rows, scores)
    assert ranked["task_macro_accuracy"] == 1.0
    assert ranked["mean_correct_log_score_margin"] == 2.0


def test_tampered_provenance_and_family_leakage_fail() -> None:
    rows = build_finding_comparisons([_example(i) for i in range(8)], seed=5, length_bucket_width=64)
    with pytest.raises(ValueError, match="target is inconsistent"):
        validate_finding_comparisons([replace(rows[0], target="B" if rows[0].target == "A" else "A"), *rows[1:]])
    train = build_finding_comparisons(
        [_example(i, family=f"train-{i}") for i in range(8)], seed=1, length_bucket_width=64
    )
    holdout = build_finding_comparisons(
        [_example(i + 20, family=("train-0" if i == 0 else f"held-{i}")) for i in range(8)],
        seed=2,
        length_bucket_width=64,
    )
    with pytest.raises(ValueError, match="train/holdout leakage"):
        validate_family_disjoint(train, holdout)

    # A corrupted sidecar must not hide the same underlying record behind a
    # different family label in the opposite role.
    relabelled = [
        replace(
            row,
            family_ids=tuple(f"held-{index}-{family}" for family in row.family_ids),
        )
        for index, row in enumerate(train)
    ]
    with pytest.raises(ValueError, match="records=.*record-"):
        validate_family_disjoint(train, relabelled)


def test_question_grammar_and_score_finiteness_are_fail_closed() -> None:
    row = {
        "record_id": "x",
        "lane": "public.experimental_findings",
        "question": "generic prose",
        "answer": "failure",
    }
    with pytest.raises(ValueError, match="grammar"):
        parse_finding_row(row, family_id="family")
    rows = build_finding_comparisons([_example(i) for i in range(8)], seed=9, length_bucket_width=64)
    with pytest.raises(ValueError, match="finite"):
        score_finding_log_scores(rows, {rows[0].comparison_id: {"A": float("nan"), "B": 0.0}})

    with pytest.raises(ValueError, match="every task"):
        score_finding_predictions(rows, {item.comparison_id: item.target for item in rows})


def test_finding_campaign_judge_requires_all_controls_and_can_promote() -> None:
    scores = {
        "candidate": [0.91, 0.90, 0.92],
        "no_intervention": [0.50, 0.51, 0.49],
        "equal_parameter": [0.60, 0.59, 0.61],
        "shuffled_binding": [0.49, 0.50, 0.51],
        "zero_update": [0.52, 0.51, 0.53],
    }
    result = judge_finding_campaign(
        scores,
        seed_ids=("seed-a", "seed-b", "seed-c"),
        retention_exact=(True, True, True),
    )
    assert result["verdict"] == "PROMOTE"
    assert result["metric"] == "finding_binding.task_macro_accuracy"
    assert result["chance_floor"] == 0.5
    assert set(result["comparisons"]) == set(scores) - {"candidate"}
    assert all(item["pass"] for item in result["comparisons"].values())


def test_finding_campaign_judge_fails_closed() -> None:
    scores = {
        "candidate": [0.70, 0.71, 0.69],
        "no_intervention": [0.69, 0.68, 0.70],
        "equal_parameter": [0.68, 0.69, 0.67],
        "shuffled_binding": [0.50, 0.51, 0.49],
        "zero_update": [0.52, 0.51, 0.53],
    }
    result = judge_finding_campaign(
        scores,
        seed_ids=("seed-a", "seed-b", "seed-c"),
        retention_exact=(True, True, True),
    )
    assert result["verdict"] == "UNDERPOWERED"
    with pytest.raises(ValueError, match="unique"):
        judge_finding_campaign(
            scores,
            seed_ids=("seed-a", "seed-a", "seed-c"),
            retention_exact=(True, True, True),
        )
    poisoned = dict(scores)
    poisoned["candidate"] = [0.70, float("nan"), 0.69]
    with pytest.raises(ValueError, match="non-finite"):
        judge_finding_campaign(
            poisoned,
            seed_ids=("seed-a", "seed-b", "seed-c"),
            retention_exact=(True, True, True),
        )
