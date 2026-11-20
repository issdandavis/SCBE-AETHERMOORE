"""Binding-controlled evaluation for verified public VQCC negative findings.

The task asks Clay to bind a public experiment description to the measured
limitation reported for that experiment.  Every answer is used once as truth
and once as a length/task-matched distractor, so answer style and length cannot
win without the question/answer relationship.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence


TASKS = frozenset(("invsqrt", "dqi", "chemistry", "all"))
LABELS = ("A", "B")
TRAINING_BINDING_MODES = ("authoritative_truth", "synthetic_derangement")
REQUIRED_ARMS = (
    "candidate",
    "no_intervention",
    "equal_parameter",
    "shuffled_binding",
    "zero_update",
)
_QUESTION = re.compile(
    r"^What limitation did the public (?P<task>invsqrt|dqi|chemistry|all) experiment report for "
    r"(?P<mechanism>.+)\? Evidence tier: (?P<evidence>[^.]+)\.$"
)


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _length_bucket(text: str, width: int) -> int:
    return len(text.encode("utf-8")) // width


@dataclass(frozen=True)
class FindingExample:
    record_id: str
    family_id: str
    task: str
    mechanism: str
    evidence_tier: str
    question: str
    answer: str
    answer_source_id: str


@dataclass(frozen=True)
class FindingComparison:
    comparison_id: str
    question_record_id: str
    family_ids: tuple[str, ...]
    task: str
    question: str
    a_answer: str
    b_answer: str
    a_source_id: str
    b_source_id: str
    target: str

    @property
    def prompt(self) -> str:
        return (
            "TASK=FINDING_BINDING_V1\n"
            f"QUESTION={self.question}\n"
            f"A={self.a_answer}\n"
            f"B={self.b_answer}\n"
            "ANSWER="
        )


@dataclass(frozen=True)
class FindingTrainingOccurrence:
    """One comparison occurrence with truth and synthetic binding kept separate.

    The answer source fields remain factual provenance.  The bound-record fields
    describe the association supervised by a training arm.  Synthetic rows are
    never valid evaluation truth and therefore use their own schema/type.
    """

    occurrence_id: str
    arm: str
    base_comparison_id: str
    question_record_id: str
    family_ids: tuple[str, ...]
    task: str
    question: str
    a_answer: str
    b_answer: str
    a_source_id: str
    b_source_id: str
    a_source_family_id: str
    b_source_family_id: str
    a_bound_record_id: str
    b_bound_record_id: str
    supervision_target: str
    binding_mode: str
    evaluation_eligible: bool

    @property
    def prompt(self) -> str:
        return (
            "TASK=FINDING_BINDING_V1\n"
            f"QUESTION={self.question}\n"
            f"A={self.a_answer}\n"
            f"B={self.b_answer}\n"
            "ANSWER="
        )


def parse_finding_row(row: Mapping[str, Any], *, family_id: str) -> FindingExample:
    if row.get("lane") != "public.experimental_findings":
        raise ValueError("row is not from public.experimental_findings")
    record_id = str(row.get("record_id") or "")
    question = str(row.get("question") or "").strip()
    answer = str(row.get("answer") or "").strip()
    if not record_id or not family_id or not question or not answer:
        raise ValueError("record_id, family_id, question, and answer are required")
    matched = _QUESTION.fullmatch(question)
    if matched is None:
        raise ValueError("finding question differs from the pinned corpus grammar")
    task = matched.group("task")
    if task not in TASKS:
        raise ValueError(f"unsupported VQCC task: {task}")
    return FindingExample(
        record_id=record_id,
        family_id=family_id,
        task=task,
        mechanism=matched.group("mechanism"),
        evidence_tier=matched.group("evidence"),
        question=question,
        answer=answer,
        answer_source_id=record_id,
    )


def derange_findings_bindings(
    examples: Sequence[FindingExample], *, seed: int, length_bucket_width: int = 32
) -> list[FindingExample]:
    """One-to-one within-stratum answer derangement for the training control."""

    if length_bucket_width <= 0:
        raise ValueError("length_bucket_width must be positive")
    grouped: dict[tuple[str, int], list[FindingExample]] = defaultdict(list)
    for example in examples:
        grouped[(example.task, _length_bucket(example.answer, length_bucket_width))].append(example)
    rng = random.Random(seed)
    result: list[FindingExample] = []
    used_sources: list[str] = []
    eligible_sources: list[str] = []
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda item: item.record_id)
        if len(group) < 2:
            continue
        rng.shuffle(group)
        shifted = group[1:] + group[:1]
        for destination, source in zip(group, shifted, strict=True):
            if destination.record_id == source.record_id:
                raise AssertionError("binding derangement retained an occurrence")
            result.append(
                replace(
                    destination,
                    answer=source.answer,
                    answer_source_id=source.record_id,
                )
            )
            eligible_sources.append(destination.record_id)
            used_sources.append(source.record_id)
    if Counter(eligible_sources) != Counter(used_sources):
        raise AssertionError("binding derangement changed answer-source marginals")
    return sorted(result, key=lambda item: item.record_id)


def aligned_findings_training_arms(
    examples: Sequence[FindingExample], *, seed: int, length_bucket_width: int = 32
) -> tuple[list[FindingExample], list[FindingExample]]:
    """Return intact and shuffled arms over exactly the same eligible records."""

    if len({example.record_id for example in examples}) != len(examples):
        raise ValueError("finding record IDs must be unique")
    shuffled = derange_findings_bindings(
        examples, seed=seed, length_bucket_width=length_bucket_width
    )
    by_id = {example.record_id: example for example in examples}
    candidate = [by_id[example.record_id] for example in shuffled]
    if [example.record_id for example in candidate] != [example.record_id for example in shuffled]:
        raise AssertionError("aligned finding arms differ in record order")
    return candidate, shuffled


def _comparison_id(left: FindingExample, right: FindingExample, question_side: str) -> str:
    return _digest(["finding-binding-v1", left.record_id, right.record_id, question_side])


def build_finding_comparisons(
    examples: Iterable[FindingExample], *, seed: int, length_bucket_width: int = 32
) -> list[FindingComparison]:
    """Build paired A/B comparisons with symmetric answer marginals.

    Each retained pair produces two questions.  The same candidate answers are
    shown in both orders: the left answer is correct for one question and the
    right answer is correct for the other.  Correct position is therefore
    exactly balanced and every answer is correct once and distractor once.
    """

    if length_bucket_width <= 0:
        raise ValueError("length_bucket_width must be positive")
    items = list(examples)
    if len({item.record_id for item in items}) != len(items):
        raise ValueError("finding record IDs must be unique")
    grouped: dict[tuple[str, int], list[FindingExample]] = defaultdict(list)
    for item in items:
        grouped[(item.task, _length_bucket(item.answer, length_bucket_width))].append(item)
    rng = random.Random(seed)
    rows: list[FindingComparison] = []
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda item: item.record_id)
        rng.shuffle(group)
        unmatched = list(group)
        while unmatched:
            left = unmatched.pop(0)
            partner_index = next(
                (
                    index
                    for index, candidate in enumerate(unmatched)
                    if candidate.family_id != left.family_id and candidate.answer != left.answer
                ),
                None,
            )
            if partner_index is None:
                continue
            right = unmatched.pop(partner_index)
            families = tuple(sorted((left.family_id, right.family_id)))
            rows.extend(
                (
                    FindingComparison(
                        comparison_id=_comparison_id(left, right, "left"),
                        question_record_id=left.record_id,
                        family_ids=families,
                        task=left.task,
                        question=left.question,
                        a_answer=left.answer,
                        b_answer=right.answer,
                        a_source_id=left.answer_source_id,
                        b_source_id=right.answer_source_id,
                        target="A",
                    ),
                    FindingComparison(
                        comparison_id=_comparison_id(left, right, "right"),
                        question_record_id=right.record_id,
                        family_ids=families,
                        task=right.task,
                        question=right.question,
                        a_answer=left.answer,
                        b_answer=right.answer,
                        a_source_id=left.answer_source_id,
                        b_source_id=right.answer_source_id,
                        target="B",
                    ),
                )
            )
    validate_finding_comparisons(rows)
    return sorted(rows, key=lambda item: item.comparison_id)


def validate_finding_comparisons(rows: Sequence[FindingComparison]) -> None:
    if not rows:
        raise ValueError("finding comparison set is empty")
    if len({row.comparison_id for row in rows}) != len(rows):
        raise ValueError("finding comparison IDs must be unique")
    answer_roles: Counter[tuple[str, str]] = Counter()
    questions = Counter(row.question_record_id for row in rows)
    for row in rows:
        if not row.family_ids or any(not family for family in row.family_ids):
            raise ValueError("comparison has an empty family")
        if row.task not in TASKS or not row.question or not row.a_answer or not row.b_answer:
            raise ValueError("comparison fields are incomplete")
        if row.a_answer == row.b_answer or row.a_source_id == row.b_source_id:
            raise ValueError("correct and distractor answers must differ")
        expected = "A" if row.question_record_id == row.a_source_id else "B"
        if row.question_record_id not in {row.a_source_id, row.b_source_id} or row.target != expected:
            raise ValueError("comparison target is inconsistent with answer provenance")
        answer_roles[(row.a_source_id, "correct" if row.target == "A" else "distractor")] += 1
        answer_roles[(row.b_source_id, "correct" if row.target == "B" else "distractor")] += 1
    labels = Counter(row.target for row in rows)
    if set(labels) != set(LABELS) or labels["A"] != labels["B"]:
        raise ValueError(f"finding targets must be exactly balanced: {dict(labels)}")
    if any(count != 1 for count in questions.values()):
        raise ValueError("each retained question must occur exactly once")
    sources = {source for source, _role in answer_roles}
    if any(answer_roles[(source, "correct")] != answer_roles[(source, "distractor")] for source in sources):
        raise ValueError("answer-source correct/distractor marginals differ")


def _ordered_derangement(
    examples: Sequence[FindingExample],
    *,
    seed: int,
    length_bucket_width: int,
) -> dict[str, FindingExample]:
    """Find a deterministic, stratum-preserving perfect answer derangement.

    Candidate edges exclude identity, same-family, and same-answer mappings.
    A deterministic augmenting-path matcher is used instead of a minibatch or
    random shuffle so the exact permutation is independently reconstructible.
    """

    grouped: dict[tuple[str, int], list[FindingExample]] = defaultdict(list)
    for example in examples:
        grouped[(example.task, _length_bucket(example.answer, length_bucket_width))].append(example)
    result: dict[str, FindingExample] = {}
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda item: item.record_id)
        if len(group) < 2:
            raise ValueError(f"finding derangement stratum is a singleton: {key!r}")
        destinations = sorted(
            group,
            key=lambda item: _digest(
                ["finding-derangement-destination-v1", seed, list(key), item.record_id]
            ),
        )
        candidates: dict[str, list[FindingExample]] = {}
        for destination in destinations:
            allowed = [
                source
                for source in group
                if source.record_id != destination.record_id
                and source.family_id != destination.family_id
                and source.answer != destination.answer
            ]
            allowed.sort(
                key=lambda source: _digest(
                    [
                        "finding-derangement-edge-v1",
                        seed,
                        list(key),
                        destination.record_id,
                        source.record_id,
                    ]
                )
            )
            if not allowed:
                raise ValueError(
                    f"finding derangement has no candidate for {destination.record_id} in {key!r}"
                )
            candidates[destination.record_id] = allowed

        source_to_destination: dict[str, str] = {}
        destination_to_source: dict[str, FindingExample] = {}

        def assign(destination_id: str, seen_sources: set[str]) -> bool:
            for source in candidates[destination_id]:
                if source.record_id in seen_sources:
                    continue
                seen_sources.add(source.record_id)
                previous = source_to_destination.get(source.record_id)
                if previous is None or assign(previous, seen_sources):
                    source_to_destination[source.record_id] = destination_id
                    destination_to_source[destination_id] = source
                    return True
            return False

        for destination in destinations:
            if not assign(destination.record_id, set()):
                raise ValueError(f"finding derangement has no perfect matching in {key!r}")
        if len(destination_to_source) != len(group):
            raise AssertionError("finding derangement did not cover every destination")
        result.update(destination_to_source)
    if len(result) != len(examples) or len({row.record_id for row in result.values()}) != len(examples):
        raise AssertionError("finding derangement is not one-to-one")
    return result


def _training_occurrence_id(values: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in values.items() if key != "occurrence_id"}
    return _digest(["finding-training-occurrence-v1", payload])


def build_finding_training_occurrences(
    examples: Sequence[FindingExample],
    comparisons: Sequence[FindingComparison],
    *,
    seed: int,
    length_bucket_width: int = 32,
) -> tuple[list[FindingTrainingOccurrence], list[FindingTrainingOccurrence]]:
    """Build aligned truth and dataset-wide synthetic training occurrences.

    The authoritative comparison rows are never modified.  The synthetic arm
    changes which answer occurrence is bound to each retained destination while
    preserving the same questions, pair plan, label counts, source multiset,
    task, and answer-length stratum.
    """

    if length_bucket_width <= 0:
        raise ValueError("length_bucket_width must be positive")
    validate_finding_comparisons(comparisons)
    by_id = {example.record_id: example for example in examples}
    if len(by_id) != len(examples):
        raise ValueError("finding record IDs must be unique")
    retained_ids = {
        record_id
        for row in comparisons
        for record_id in (row.question_record_id, row.a_source_id, row.b_source_id)
    }
    missing = sorted(retained_ids - set(by_id))
    if missing:
        raise ValueError(f"finding comparisons reference missing examples: {missing[:5]}")
    retained = [by_id[record_id] for record_id in sorted(retained_ids)]
    for row in comparisons:
        a_example, b_example = by_id[row.a_source_id], by_id[row.b_source_id]
        question_example = by_id[row.question_record_id]
        if (
            row.a_answer != a_example.answer
            or row.b_answer != b_example.answer
            or row.question != question_example.question
            or row.task != question_example.task
        ):
            raise ValueError(f"finding comparison content differs from source examples: {row.comparison_id}")
    shuffled_sources = _ordered_derangement(
        retained,
        seed=seed,
        length_bucket_width=length_bucket_width,
    )
    identity_sources = {example.record_id: example for example in retained}

    def render(
        *, arm: str, binding_mode: str, source_map: Mapping[str, FindingExample]
    ) -> list[FindingTrainingOccurrence]:
        rendered: list[FindingTrainingOccurrence] = []
        for base in sorted(comparisons, key=lambda item: item.comparison_id):
            a_bound, b_bound = base.a_source_id, base.b_source_id
            a_source, b_source = source_map[a_bound], source_map[b_bound]
            raw: dict[str, Any] = {
                "arm": arm,
                "base_comparison_id": base.comparison_id,
                "question_record_id": base.question_record_id,
                "family_ids": base.family_ids,
                "task": base.task,
                "question": base.question,
                "a_answer": a_source.answer,
                "b_answer": b_source.answer,
                "a_source_id": a_source.record_id,
                "b_source_id": b_source.record_id,
                "a_source_family_id": a_source.family_id,
                "b_source_family_id": b_source.family_id,
                "a_bound_record_id": a_bound,
                "b_bound_record_id": b_bound,
                "supervision_target": base.target,
                "binding_mode": binding_mode,
                "evaluation_eligible": binding_mode == "authoritative_truth",
            }
            occurrence_id = _training_occurrence_id(raw)
            rendered.append(FindingTrainingOccurrence(occurrence_id=occurrence_id, **raw))
        return sorted(rendered, key=lambda item: item.occurrence_id)

    candidate = render(
        arm="candidate",
        binding_mode="authoritative_truth",
        source_map=identity_sources,
    )
    shuffled = render(
        arm="shuffled_binding",
        binding_mode="synthetic_derangement",
        source_map=shuffled_sources,
    )
    validate_finding_training_occurrences(
        candidate,
        comparisons=comparisons,
        examples=retained,
        length_bucket_width=length_bucket_width,
    )
    validate_finding_training_occurrences(
        shuffled,
        comparisons=comparisons,
        examples=retained,
        length_bucket_width=length_bucket_width,
    )
    if [row.base_comparison_id for row in sorted(candidate, key=lambda row: row.base_comparison_id)] != [
        row.base_comparison_id for row in sorted(shuffled, key=lambda row: row.base_comparison_id)
    ]:
        raise AssertionError("finding training arms differ in base occurrence pool")
    if Counter(row.supervision_target for row in candidate) != Counter(
        row.supervision_target for row in shuffled
    ):
        raise AssertionError("finding training arms differ in target marginals")
    return candidate, shuffled


def validate_finding_training_occurrences(
    rows: Sequence[FindingTrainingOccurrence],
    *,
    comparisons: Sequence[FindingComparison],
    examples: Sequence[FindingExample],
    length_bucket_width: int = 32,
) -> dict[str, Any]:
    """Validate one training arm without accepting it as evaluation truth."""

    if not rows:
        raise ValueError("finding training occurrence set is empty")
    if length_bucket_width <= 0:
        raise ValueError("length_bucket_width must be positive")
    validate_finding_comparisons(comparisons)
    base_by_id = {row.comparison_id: row for row in comparisons}
    example_by_id = {row.record_id: row for row in examples}
    if len(base_by_id) != len(comparisons) or len(example_by_id) != len(examples):
        raise ValueError("finding training validation inputs contain duplicate IDs")
    if len({row.occurrence_id for row in rows}) != len(rows):
        raise ValueError("finding training occurrence IDs must be unique")
    if {row.base_comparison_id for row in rows} != set(base_by_id):
        raise ValueError("finding training occurrences differ from the base comparison pool")
    modes = {row.binding_mode for row in rows}
    arms = {row.arm for row in rows}
    if len(modes) != 1 or not modes.issubset(TRAINING_BINDING_MODES) or len(arms) != 1:
        raise ValueError("finding training rows must contain one valid arm and binding mode")
    mode = next(iter(modes))
    expected_arm = "candidate" if mode == "authoritative_truth" else "shuffled_binding"
    if arms != {expected_arm}:
        raise ValueError("finding training arm differs from its binding mode")
    destination_to_source: dict[str, str] = {}
    for row in rows:
        if row.occurrence_id != _training_occurrence_id(row.__dict__):
            raise ValueError(f"finding training occurrence identity differs: {row.occurrence_id}")
        base = base_by_id[row.base_comparison_id]
        if (
            row.question_record_id != base.question_record_id
            or row.family_ids != base.family_ids
            or row.task != base.task
            or row.question != base.question
            or row.a_bound_record_id != base.a_source_id
            or row.b_bound_record_id != base.b_source_id
            or row.supervision_target != base.target
        ):
            raise ValueError(f"finding training row differs from its base: {row.occurrence_id}")
        for side in ("a", "b"):
            source_id = getattr(row, f"{side}_source_id")
            source = example_by_id.get(source_id)
            bound_id = getattr(row, f"{side}_bound_record_id")
            bound = example_by_id.get(bound_id)
            if source is None or bound is None:
                raise ValueError("finding training row references an unknown source or destination")
            if (
                getattr(row, f"{side}_answer") != source.answer
                or getattr(row, f"{side}_source_family_id") != source.family_id
            ):
                raise ValueError("finding training answer differs from source provenance")
            previous = destination_to_source.setdefault(bound_id, source_id)
            if previous != source_id:
                raise ValueError("finding training mapping changes between paired occurrences")
            if mode == "authoritative_truth":
                if source_id != bound_id or row.evaluation_eligible is not True:
                    raise ValueError("authoritative finding binding is not identity truth")
            else:
                if row.evaluation_eligible is not False:
                    raise ValueError("synthetic finding binding cannot be evaluation eligible")
                if source_id == bound_id or source.family_id == bound.family_id or source.answer == bound.answer:
                    raise ValueError("synthetic finding binding violates derangement constraints")
                if source.task != bound.task or _length_bucket(
                    source.answer, length_bucket_width
                ) != _length_bucket(bound.answer, length_bucket_width):
                    raise ValueError("synthetic finding binding changed task or length stratum")
    if len(set(destination_to_source.values())) != len(destination_to_source):
        raise ValueError("finding training mapping is not one-to-one")
    if set(destination_to_source) != set(destination_to_source.values()):
        raise ValueError("finding training source and destination marginals differ")
    if Counter(row.supervision_target for row in rows) != Counter(row.target for row in comparisons):
        raise ValueError("finding training target marginals differ from truth")
    return {
        "rows": len(rows),
        "binding_mode": mode,
        "label_counts": dict(sorted(Counter(row.supervision_target for row in rows).items())),
        "task_counts": dict(sorted(Counter(row.task for row in rows).items())),
        "destinations": len(destination_to_source),
        "fixed_points": sum(
            destination == source for destination, source in destination_to_source.items()
        ),
        "mapping_sha256": _digest(sorted(destination_to_source.items())),
    }


def validate_family_disjoint(
    train: Sequence[FindingComparison], holdout: Sequence[FindingComparison]
) -> None:
    train_families = {family for row in train for family in row.family_ids}
    holdout_families = {family for row in holdout for family in row.family_ids}
    family_overlap = train_families & holdout_families
    train_records = {
        record
        for row in train
        for record in (row.question_record_id, row.a_source_id, row.b_source_id)
    }
    holdout_records = {
        record
        for row in holdout
        for record in (row.question_record_id, row.a_source_id, row.b_source_id)
    }
    record_overlap = train_records & holdout_records
    if family_overlap or record_overlap:
        raise ValueError(
            "finding train/holdout leakage: "
            f"families={sorted(family_overlap)}, records={sorted(record_overlap)}"
        )


def score_finding_predictions(
    rows: Sequence[FindingComparison], predictions: Mapping[str, Any]
) -> dict[str, Any]:
    """Score A/B predictions with task-macro accuracy and strict coverage."""

    validate_finding_comparisons(rows)
    observed_tasks = {row.task for row in rows}
    if observed_tasks != TASKS:
        raise ValueError(
            f"finding evaluation must include every task: expected={sorted(TASKS)}, "
            f"observed={sorted(observed_tasks)}"
        )
    by_task: dict[str, list[float]] = defaultdict(list)
    correct = 0
    parsed = 0
    for row in rows:
        token = str(predictions.get(row.comparison_id, "")).strip().upper()
        if token in LABELS:
            parsed += 1
        hit = token == row.target
        correct += int(hit)
        by_task[row.task].append(float(hit))
    task_accuracy = {task: statistics.fmean(values) for task, values in sorted(by_task.items())}
    return {
        "rows": len(rows),
        "coverage": parsed / len(rows),
        "exact_accuracy": correct / len(rows),
        "task_macro_accuracy": statistics.fmean(task_accuracy.values()),
        "accuracy_by_task": task_accuracy,
        "chance_accuracy": 0.5,
        "answer_sources": len({source for row in rows for source in (row.a_source_id, row.b_source_id)}),
        "families": len({family for row in rows for family in row.family_ids}),
    }


def score_finding_log_scores(
    rows: Sequence[FindingComparison], scores: Mapping[str, Mapping[str, float]]
) -> dict[str, Any]:
    """Score conditional answer log-scores without converting them to text."""

    predictions: dict[str, str] = {}
    margins: list[float] = []
    for row in rows:
        pair = scores.get(row.comparison_id)
        if not isinstance(pair, Mapping):
            continue
        a, b = float(pair.get("A", math.nan)), float(pair.get("B", math.nan))
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("finding answer scores must be finite")
        predictions[row.comparison_id] = "A" if a > b else "B" if b > a else ""
        signed = (a - b) if row.target == "A" else (b - a)
        margins.append(signed)
    result = score_finding_predictions(rows, predictions)
    result["mean_correct_log_score_margin"] = statistics.fmean(margins) if margins else math.nan
    return result


def _pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return math.inf
    return math.sqrt((statistics.stdev(left) ** 2 + statistics.stdev(right) ** 2) / 2.0)


def judge_finding_campaign(
    arm_scores: Mapping[str, Sequence[float]],
    *,
    seed_ids: Sequence[str],
    retention_exact: Sequence[bool],
    min_seeds: int = 3,
    absolute_margin: float = 0.02,
) -> dict[str, Any]:
    """Judge aligned finding task-macro accuracies without silent coercion."""

    if set(arm_scores) != set(REQUIRED_ARMS):
        raise ValueError("finding campaign scores do not contain the five required arms")
    seeds = [str(seed_id) for seed_id in seed_ids]
    if any(not seed_id for seed_id in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seed IDs must be explicit, non-empty, and unique")
    lengths = {len(values) for values in arm_scores.values()}
    if len(lengths) != 1 or next(iter(lengths)) < min_seeds:
        raise ValueError(f"every arm requires at least {min_seeds} aligned seeds")
    count = next(iter(lengths))
    if len(seeds) != count:
        raise ValueError("seed ID count differs from score count")
    if len(retention_exact) != count or any(type(value) is not bool for value in retention_exact):
        raise ValueError("retention results must be one boolean per seed")
    checked: dict[str, list[float]] = {}
    for name, values in arm_scores.items():
        checked[name] = [float(value) for value in values]
        if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in checked[name]):
            raise ValueError(f"{name} contains a non-finite or out-of-range score")

    candidate = checked["candidate"]
    comparisons: dict[str, Any] = {}
    verdict = "PROMOTE"
    for name in REQUIRED_ARMS[1:]:
        control = checked[name]
        effect = statistics.fmean(candidate) - statistics.fmean(control)
        pooled_sd = _pooled_sd(candidate, control)
        required = max(absolute_margin, 2.0 * pooled_sd)
        passed = effect > required
        comparisons[name] = {
            "candidate_minus_control": effect,
            "pooled_sd": pooled_sd,
            "required_strict_margin": required,
            "pass": passed,
        }
        if effect <= 0:
            verdict = "REJECT"
        elif not passed and verdict != "REJECT":
            verdict = "UNDERPOWERED"
    if statistics.fmean(candidate) <= (0.5 + absolute_margin) or not all(retention_exact):
        verdict = "REJECT"
    return {
        "verdict": verdict,
        "seeds": len(candidate),
        "seed_ids": seeds,
        "metric": "finding_binding.task_macro_accuracy",
        "candidate_mean": statistics.fmean(candidate),
        "chance_floor": 0.5,
        "retention_exact": all(retention_exact),
        "comparisons": comparisons,
    }
