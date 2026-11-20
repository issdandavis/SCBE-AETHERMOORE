"""Exact VQCC resource-discrimination task and campaign gates.

This module deliberately does not train a model.  It turns the corpus's
``public.gate_count`` rows into a length-matched, class-balanced comparison
task whose answers are derived from Kickmix opcodes.  A model that succeeds
has passed a resource-count input-access sanity check on already-valid circuit
fragments.  That is not a proof of findings ranking, proposal quality, or a
semantics-preserving replacement.
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


TOFFOLI_OPCODES = frozenset((0x30, 0x31, 0x32, 0xB0, 0xB1, 0xB2))
LABELS = ("A", "B", "T")
REQUIRED_ARMS = (
    "candidate",
    "no_intervention",
    "equal_parameter",
    "shuffled_binding",
    "zero_update",
)
_HEX_LINE = re.compile(r"(?:[0-9a-fA-F]{2})(?: [0-9a-fA-F]{2}){3,31}")


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GateCountExample:
    """One verified opcode window from a corpus gate-count row."""

    record_id: str
    family_id: str
    opcodes: tuple[int, ...]
    count: int


@dataclass(frozen=True)
class CostComparison:
    """Two equal-length windows and the lower-cost choice.

    ``T`` means the two windows tie.  All targets are one character long so
    output length cannot reveal the class.
    """

    pair_id: str
    a_record_id: str
    b_record_id: str
    family_ids: tuple[str, ...]
    a_opcodes: tuple[int, ...]
    b_opcodes: tuple[int, ...]
    a_count: int
    b_count: int
    target: str
    target_source_id: str

    @property
    def prompt(self) -> str:
        a = " ".join(f"{opcode:02x}" for opcode in self.a_opcodes)
        b = " ".join(f"{opcode:02x}" for opcode in self.b_opcodes)
        return f"TASK=COST_COMPARE_V1\nA={a}\nB={b}\nANSWER="


@dataclass(frozen=True)
class ArmSpec:
    name: str
    trainable_parameters: int
    updates: int
    input_binding: str
    training_material: str


def parse_gate_count_row(row: Mapping[str, Any], *, family_id: str) -> GateCountExample:
    """Parse and independently verify one ``public.gate_count`` corpus row.

    The family identifier must come from the separately sealed split sidecar;
    the current corpus row does not carry a sufficiently granular family.
    """

    if row.get("lane") != "public.gate_count":
        raise ValueError("row is not from public.gate_count")
    record_id = str(row.get("record_id", ""))
    question = str(row.get("question", ""))
    answer = str(row.get("answer", ""))
    if not record_id or not family_id:
        raise ValueError("record_id and external family_id are required")
    matches = _HEX_LINE.findall(question)
    if len(matches) != 1:
        raise ValueError("gate-count question must contain one opcode window")
    opcodes = tuple(int(token, 16) for token in matches[0].split())
    try:
        reported = int(answer)
    except ValueError as exc:
        raise ValueError("gate-count answer is not an integer") from exc
    measured = sum(opcode in TOFFOLI_OPCODES for opcode in opcodes)
    if reported != measured:
        raise ValueError(f"gate-count answer differs: reported={reported}, measured={measured}")
    return GateCountExample(record_id=record_id, family_id=family_id, opcodes=opcodes, count=measured)


def _pair_identity(
    *,
    a_record_id: str,
    b_record_id: str,
    family_ids: Sequence[str],
    a_opcodes: Sequence[int],
    b_opcodes: Sequence[int],
    a_count: int,
    b_count: int,
) -> str:
    return _stable_digest(
        [
            "cost-compare-v2",
            a_record_id,
            b_record_id,
            sorted(family_ids),
            list(a_opcodes),
            list(b_opcodes),
            a_count,
            b_count,
        ]
    )


def _comparison(a: GateCountExample, b: GateCountExample) -> CostComparison:
    if len(a.opcodes) != 32 or len(b.opcodes) != 32:
        raise ValueError("cost-comparison windows must contain exactly 32 opcodes")
    if a.record_id == b.record_id:
        raise ValueError("a comparison cannot contain the same record twice")
    family_ids = tuple(sorted({a.family_id, b.family_id}))
    if not family_ids or any(not family for family in family_ids):
        raise ValueError("every comparison requires a non-empty family")
    target = "A" if a.count < b.count else "B" if b.count < a.count else "T"
    pair_id = _pair_identity(
        a_record_id=a.record_id,
        b_record_id=b.record_id,
        family_ids=family_ids,
        a_opcodes=a.opcodes,
        b_opcodes=b.opcodes,
        a_count=a.count,
        b_count=b.count,
    )
    return CostComparison(
        pair_id=pair_id,
        a_record_id=a.record_id,
        b_record_id=b.record_id,
        family_ids=family_ids,
        a_opcodes=a.opcodes,
        b_opcodes=b.opcodes,
        a_count=a.count,
        b_count=b.count,
        target=target,
        target_source_id=pair_id,
    )


def _eligible_examples(examples: Iterable[GateCountExample]) -> list[GateCountExample]:
    eligible = [example for example in examples if len(example.opcodes) == 32]
    if len({example.record_id for example in eligible}) != len(eligible):
        raise ValueError("record identifiers must be unique")
    for example in eligible:
        if not example.family_id:
            raise ValueError("every example requires a non-empty family")
        measured = sum(opcode in TOFFOLI_OPCODES for opcode in example.opcodes)
        if example.count != measured:
            raise ValueError(f"example count differs for {example.record_id}")
    return eligible


def _attempt_balanced_build(
    eligible: Sequence[GateCountExample], *, seed: int, gap_strata: tuple[int, ...], per_gap: int
) -> list[CostComparison] | None:
    by_count: dict[int, list[GateCountExample]] = defaultdict(list)
    rng = random.Random(seed)
    for example in eligible:
        by_count[example.count].append(example)
    for group in by_count.values():
        group.sort(key=lambda item: item.record_id)
        rng.shuffle(group)

    non_ties: list[CostComparison] = []
    for gap in gap_strata:
        lowers = [count for count in sorted(by_count) if count + gap in by_count]
        rng.shuffle(lowers)
        raw_pairs: list[tuple[GateCountExample, GateCountExample]] = []
        needed = 2 * per_gap
        while len(raw_pairs) < needed:
            progressed = False
            for lower in lowers:
                if by_count[lower] and by_count[lower + gap]:
                    raw_pairs.append((by_count[lower].pop(), by_count[lower + gap].pop()))
                    progressed = True
                    if len(raw_pairs) == needed:
                        break
            if not progressed:
                return None
        rng.shuffle(raw_pairs)
        non_ties.extend(_comparison(low, high) for low, high in raw_pairs[:per_gap])
        non_ties.extend(_comparison(high, low) for low, high in raw_pairs[per_gap:])

    per_label = per_gap * len(gap_strata)
    tie_pairs: list[tuple[GateCountExample, GateCountExample]] = []
    for count in sorted(by_count):
        group = by_count[count]
        tie_pairs.extend(zip(group[::2], group[1::2]))
    rng.shuffle(tie_pairs)
    if len(tie_pairs) < per_label:
        return None
    rows = [*_comparison_pairs(tie_pairs[:per_label]), *non_ties]
    rows.sort(key=lambda row: row.pair_id)
    return rows


def _comparison_pairs(pairs: Iterable[tuple[GateCountExample, GateCountExample]]) -> list[CostComparison]:
    return [_comparison(left, right) for left, right in pairs]


def build_balanced_comparisons(
    examples: Iterable[GateCountExample],
    *,
    seed: int,
    per_label: int | None = None,
    gap_strata: Sequence[int] = (1,),
) -> list[CostComparison]:
    """Build deterministic, hard, equally populated ``A``/``B``/``T`` rows.

    Non-tie pairs are drawn first from adjacent observed count bins.  Separate
    unordered pairs feed A and B so a reversed duplicate cannot leak the label.
    """

    eligible = _eligible_examples(examples)
    gaps = tuple(int(gap) for gap in gap_strata)
    if not gaps or any(gap <= 0 for gap in gaps) or len(set(gaps)) != len(gaps):
        raise ValueError("gap_strata must contain distinct positive integers")
    if per_label is not None:
        if per_label <= 0 or per_label % len(gaps):
            raise ValueError("per_label must be positive and divisible by the number of gap strata")
        candidates = [per_label // len(gaps)]
    else:
        candidates = range(len(eligible) // (6 * len(gaps)), 0, -1)
    rows = None
    for per_gap in candidates:
        rows = _attempt_balanced_build(eligible, seed=seed, gap_strata=gaps, per_gap=per_gap)
        if rows is not None:
            break
    if rows is None:
        raise ValueError("insufficient unique records for the requested balanced gap strata")
    validate_task_set(rows, require_balanced=True, max_record_reuse=1)
    report = task_set_report(rows)
    if report["gap_distribution_by_label"]["A"] != report["gap_distribution_by_label"]["B"]:
        raise AssertionError("A and B gap distributions differ")
    return rows


def build_natural_prevalence_comparisons(
    examples: Iterable[GateCountExample], *, seed: int, max_rows: int | None = None
) -> list[CostComparison]:
    """Pair a deterministic shuffle once, preserving its natural label prevalence."""

    eligible = _eligible_examples(examples)
    rng = random.Random(seed)
    eligible.sort(key=lambda item: item.record_id)
    rng.shuffle(eligible)
    available = len(eligible) // 2
    take = available if max_rows is None else max_rows
    if take <= 0 or take > available:
        raise ValueError(f"max_rows must be in [1, {available}], got {take}")
    rows = [_comparison(eligible[2 * index], eligible[2 * index + 1]) for index in range(take)]
    rows.sort(key=lambda row: row.pair_id)
    validate_task_set(rows, require_balanced=False, max_record_reuse=1)
    return rows


def validate_comparison(row: CostComparison, *, require_true_target: bool = True) -> None:
    if not row.a_record_id or not row.b_record_id or row.a_record_id == row.b_record_id:
        raise ValueError("comparison record IDs must be non-empty and distinct")
    if not row.family_ids or any(not family for family in row.family_ids):
        raise ValueError("comparison families must be non-empty")
    if tuple(sorted(set(row.family_ids))) != row.family_ids:
        raise ValueError("comparison families must be unique and sorted")
    if len(row.a_opcodes) != 32 or len(row.b_opcodes) != 32:
        raise ValueError("all windows must have length 32")
    if any(not 0 <= opcode <= 0xFF for opcode in (*row.a_opcodes, *row.b_opcodes)):
        raise ValueError("opcode lies outside one byte")
    a_measured = sum(opcode in TOFFOLI_OPCODES for opcode in row.a_opcodes)
    b_measured = sum(opcode in TOFFOLI_OPCODES for opcode in row.b_opcodes)
    if (row.a_count, row.b_count) != (a_measured, b_measured):
        raise ValueError(f"comparison counts differ on {row.pair_id}")
    expected_id = _pair_identity(
        a_record_id=row.a_record_id,
        b_record_id=row.b_record_id,
        family_ids=row.family_ids,
        a_opcodes=row.a_opcodes,
        b_opcodes=row.b_opcodes,
        a_count=row.a_count,
        b_count=row.b_count,
    )
    if row.pair_id != expected_id:
        raise ValueError(f"comparison identity differs on {row.pair_id}")
    exact = "A" if a_measured < b_measured else "B" if b_measured < a_measured else "T"
    if require_true_target and (row.target != exact or row.target_source_id != row.pair_id):
        raise ValueError(f"comparison target differs on {row.pair_id}")
    if row.target not in LABELS or not row.target_source_id:
        raise ValueError("comparison target or target source is invalid")


def task_set_report(rows: Sequence[CostComparison]) -> dict[str, Any]:
    record_use = Counter(
        record_id for row in rows for record_id in (row.a_record_id, row.b_record_id)
    )
    gap_by_label = {
        label: dict(sorted(Counter(abs(row.a_count - row.b_count) for row in rows if row.target == label).items()))
        for label in LABELS
    }
    return {
        "rows": len(rows),
        "label_counts": dict(Counter(row.target for row in rows)),
        "unique_records": len(record_use),
        "unique_families": len({family for row in rows for family in row.family_ids}),
        "maximum_record_reuse": max(record_use.values(), default=0),
        "gap_distribution_by_label": gap_by_label,
    }


def validate_task_set(
    rows: Sequence[CostComparison],
    *,
    require_balanced: bool = True,
    max_record_reuse: int = 1,
    require_true_target: bool = True,
) -> None:
    if not rows:
        raise ValueError("task set is empty")
    if max_record_reuse <= 0:
        raise ValueError("max_record_reuse must be positive")
    ids = [row.pair_id for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("pair identifiers must be unique")
    labels = Counter(row.target for row in rows)
    if not set(labels).issubset(LABELS):
        raise ValueError(f"task contains an invalid label: {dict(labels)}")
    if require_balanced and (set(labels) != set(LABELS) or len(set(labels.values())) != 1):
        raise ValueError(f"task labels must be exactly balanced: {dict(labels)}")
    prompt_lengths = {len(row.prompt) for row in rows}
    if len(prompt_lengths) != 1:
        raise ValueError("all prompts must have the same length")
    for row in rows:
        validate_comparison(row, require_true_target=require_true_target)
    report = task_set_report(rows)
    if report["maximum_record_reuse"] > max_record_reuse:
        raise ValueError(
            f"record reuse {report['maximum_record_reuse']} exceeds cap {max_record_reuse}"
        )


def validate_family_disjoint(train: Sequence[CostComparison], holdout: Sequence[CostComparison]) -> None:
    validate_task_set(train)
    validate_task_set(holdout)
    train_families = {family for row in train for family in row.family_ids}
    holdout_families = {family for row in holdout for family in row.family_ids}
    family_overlap = train_families & holdout_families
    train_records = {record for row in train for record in (row.a_record_id, row.b_record_id)}
    holdout_records = {record for row in holdout for record in (row.a_record_id, row.b_record_id)}
    record_overlap = train_records & holdout_records
    if family_overlap or record_overlap:
        raise ValueError(
            f"train/holdout leakage: families={sorted(family_overlap)}, records={sorted(record_overlap)}"
        )


def shuffled_binding(rows: Sequence[CostComparison], *, seed: int) -> list[CostComparison]:
    """Return a one-to-one occurrence shuffle with no label left in place.

    The task set is balanced, so cycling target-occurrence pools A→B→T→A
    preserves the exact target marginal while breaking every input binding.
    """

    validate_task_set(rows)
    by_label: dict[str, list[CostComparison]] = {label: [] for label in LABELS}
    for row in rows:
        by_label[row.target].append(row)
    rng = random.Random(seed)
    for group in by_label.values():
        group.sort(key=lambda row: row.pair_id)
        rng.shuffle(group)
    successor = {"A": "B", "B": "T", "T": "A"}
    cursors = Counter()
    shuffled: list[CostComparison] = []
    for row in sorted(rows, key=lambda item: item.pair_id):
        source_pool = by_label[successor[row.target]]
        source = source_pool[cursors[row.target]]
        cursors[row.target] += 1
        shuffled.append(replace(row, target=source.target, target_source_id=source.pair_id))
    if Counter(row.target for row in shuffled) != Counter(row.target for row in rows):
        raise AssertionError("shuffled binding changed target marginals")
    if any(before.target == after.target for before, after in zip(sorted(rows, key=lambda x: x.pair_id), shuffled)):
        raise AssertionError("shuffled binding retained a label")
    if len({row.target_source_id for row in shuffled}) != len(shuffled):
        raise AssertionError("target occurrence mapping is not one-to-one")
    validate_task_set(shuffled, require_balanced=True, max_record_reuse=1, require_true_target=False)
    return shuffled


def _normalise_label(value: Any) -> str | None:
    token = str(value).strip().upper()
    return token if token in LABELS else None


def score_predictions(
    rows: Sequence[CostComparison],
    predictions: Mapping[str, Any],
    *,
    require_balanced: bool = True,
) -> dict[str, Any]:
    """Score exact and resource-aware outcomes without rewarding response length."""

    validate_task_set(rows, require_balanced=require_balanced)
    totals = Counter(row.target for row in rows)
    correct = Counter()
    confusion: dict[str, Counter[str]] = {label: Counter() for label in LABELS}
    regrets: list[int] = []
    parsed = 0
    exact = 0
    for row in rows:
        predicted = _normalise_label(predictions.get(row.pair_id, ""))
        if predicted is not None:
            parsed += 1
        rendered = predicted or "INVALID"
        confusion[row.target][rendered] += 1
        if predicted == row.target:
            exact += 1
            correct[row.target] += 1
        if predicted == "A":
            selected = row.a_count
        elif predicted == "B":
            selected = row.b_count
        elif predicted == "T":
            selected = max(row.a_count, row.b_count)
        else:
            selected = max(row.a_count, row.b_count) + 1
        regrets.append(selected - min(row.a_count, row.b_count))
    recalls = {
        label: (correct[label] / totals[label] if totals[label] else None) for label in LABELS
    }
    observed_recalls = [value for value in recalls.values() if value is not None]
    return {
        "rows": len(rows),
        "coverage": parsed / len(rows),
        "exact_accuracy": exact / len(rows),
        "balanced_exact_accuracy": statistics.fmean(observed_recalls),
        "recall_by_label": recalls,
        "mean_selection_regret_toffoli": statistics.fmean(regrets),
        "majority_baseline_accuracy": max(totals.values()) / len(rows),
        "natural_label_prevalence": {label: totals[label] / len(rows) for label in LABELS},
        "prompt_length": len(rows[0].prompt),
        "task_set": task_set_report(rows),
        "confusion": {label: dict(confusion[label]) for label in LABELS},
    }


def score_natural_prevalence_predictions(
    rows: Sequence[CostComparison], predictions: Mapping[str, Any]
) -> dict[str, Any]:
    """Score the once-paired natural population separately from the balanced diagnostic."""

    result = score_predictions(rows, predictions, require_balanced=False)
    result["evaluation_population"] = "natural_prevalence_once_paired"
    result["natural_prevalence_accuracy"] = result["exact_accuracy"]
    return result


def standard_arm_specs(*, trainable_parameters: int, updates: int) -> dict[str, ArmSpec]:
    """Return preregistered metadata, not proof of runtime parameter equality.

    The eventual runner must independently count and hash every trainable tensor
    before the first update; matching these declarations alone is insufficient.
    """

    if trainable_parameters <= 0 or updates <= 0:
        raise ValueError("candidate trainable_parameters and updates must be positive")
    specs = {
        "candidate": ArmSpec("candidate", trainable_parameters, updates, "intact", "vqcc"),
        "no_intervention": ArmSpec("no_intervention", 0, 0, "none", "none"),
        "equal_parameter": ArmSpec(
            "equal_parameter", trainable_parameters, updates, "intact", "token_matched_ordinary"
        ),
        "shuffled_binding": ArmSpec(
            "shuffled_binding", trainable_parameters, updates, "one_to_one_deranged", "vqcc"
        ),
        "zero_update": ArmSpec("zero_update", trainable_parameters, 0, "intact", "vqcc"),
    }
    validate_arm_specs(specs)
    return specs


def validate_arm_specs(specs: Mapping[str, ArmSpec]) -> None:
    if set(specs) != set(REQUIRED_ARMS):
        raise ValueError(f"required arms differ: {sorted(specs)}")
    candidate = specs["candidate"]
    for name in ("equal_parameter", "shuffled_binding", "zero_update"):
        if specs[name].trainable_parameters != candidate.trainable_parameters:
            raise ValueError(f"{name} is not parameter matched")
    for name in ("equal_parameter", "shuffled_binding"):
        if specs[name].updates != candidate.updates:
            raise ValueError(f"{name} is not update matched")
    if specs["zero_update"].updates != 0 or specs["no_intervention"].updates != 0:
        raise ValueError("zero-update controls must have zero updates")


def _pooled_sd(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return math.inf
    return math.sqrt((statistics.stdev(left) ** 2 + statistics.stdev(right) ** 2) / 2.0)


def judge_campaign(
    arm_scores: Mapping[str, Sequence[float]],
    *,
    seed_ids: Sequence[str],
    retention_exact: Sequence[bool],
    min_seeds: int = 3,
    absolute_margin: float = 0.02,
) -> dict[str, Any]:
    """Apply the preregistered multi-seed promotion gate.

    The candidate must beat every control by more than both the absolute margin
    and two pooled standard deviations.  Otherwise the result is explicitly
    ``UNDERPOWERED`` instead of being called a win.
    """

    if set(arm_scores) != set(REQUIRED_ARMS):
        raise ValueError("campaign scores do not contain the five required arms")
    seeds = [str(seed_id) for seed_id in seed_ids]
    if any(not seed_id for seed_id in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seed IDs must be explicit, non-empty, and unique")
    lengths = {len(values) for values in arm_scores.values()}
    if len(lengths) != 1 or next(iter(lengths)) < min_seeds:
        raise ValueError(f"every arm requires at least {min_seeds} aligned seeds")
    if len(seeds) != next(iter(lengths)):
        raise ValueError("seed ID count differs from score count")
    if len(retention_exact) != next(iter(lengths)):
        raise ValueError("retention result count differs from seed count")
    if any(type(value) is not bool for value in retention_exact):
        raise ValueError("retention results must be booleans")
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
    if statistics.fmean(candidate) <= (1 / 3 + absolute_margin):
        verdict = "REJECT"
    if not all(retention_exact):
        verdict = "REJECT"
    return {
        "verdict": verdict,
        "seeds": len(candidate),
        "seed_ids": seeds,
        "metric": "balanced_exact_accuracy",
        "candidate_mean": statistics.fmean(candidate),
        "chance_floor": 1 / 3,
        "retention_exact": all(retention_exact),
        "comparisons": comparisons,
    }
