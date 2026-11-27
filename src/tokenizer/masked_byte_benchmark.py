"""Fairness and metric harness for the three-arm masked-byte experiment.

The harness does not contain a model and does not manufacture a quality claim.
It creates deterministic held-out cases, validates routing/work receipts, and
separates representation gain (six fixed views minus bytes) from routing gain
(six adaptive views minus six fixed views).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import random
from statistics import fmean, stdev
from typing import Iterable, Mapping, Sequence

SCHEMA = "scbe.masked-byte-routing-benchmark.v1"


class BenchmarkContractError(ValueError):
    """A run cannot be compared without violating the benchmark contract."""


class BenchmarkArm(str, Enum):
    BYTE_BASELINE = "byte_baseline"
    SIX_VIEW_FIXED = "six_view_fixed"
    SIX_VIEW_ADAPTIVE = "six_view_adaptive"


class MaskKind(str, Enum):
    SINGLE = "single"
    SPAN = "span"
    STRUCTURE = "structure"


@dataclass(frozen=True, slots=True)
class MaskedByteCase:
    case_id: str
    split: str
    target: bytes
    masked_positions: tuple[int, ...]
    mask_kind: MaskKind

    def __post_init__(self) -> None:
        if not self.case_id or not self.split or not self.target:
            raise BenchmarkContractError("case identity, split, and target are required")
        if not self.masked_positions:
            raise BenchmarkContractError("at least one byte must be masked")
        if tuple(sorted(set(self.masked_positions))) != self.masked_positions:
            raise BenchmarkContractError("masked positions must be sorted and unique")
        if self.masked_positions[0] < 0 or self.masked_positions[-1] >= len(self.target):
            raise BenchmarkContractError("masked position is outside the target")


@dataclass(frozen=True, slots=True)
class RoutingStep:
    step: int
    position: int
    score: float
    candidate_evaluations: int
    predicted_byte: int
    reason: str

    def __post_init__(self) -> None:
        if self.step < 0 or self.position < 0:
            raise BenchmarkContractError("step and position must be non-negative")
        if not math.isfinite(self.score):
            raise BenchmarkContractError("routing score must be finite")
        if self.candidate_evaluations < 1:
            raise BenchmarkContractError("candidate evaluations must be positive")
        if not 0 <= self.predicted_byte <= 255:
            raise BenchmarkContractError("predicted byte must be in 0..255")
        if not self.reason:
            raise BenchmarkContractError("routing reason is required")


@dataclass(frozen=True, slots=True)
class CaseObservation:
    case_id: str
    reconstruction: bytes
    candidate_distributions: tuple[tuple[float, ...], ...]
    trace: tuple[RoutingStep, ...]
    forward_passes: int

    def __post_init__(self) -> None:
        if not self.case_id:
            raise BenchmarkContractError("observation case_id is required")
        if self.forward_passes < 0:
            raise BenchmarkContractError("forward_passes must be non-negative")
        for distribution in self.candidate_distributions:
            if len(distribution) != 256:
                raise BenchmarkContractError("each candidate distribution must contain 256 byte probabilities")
            if any(not math.isfinite(value) or value < 0.0 for value in distribution):
                raise BenchmarkContractError("candidate probabilities must be finite and non-negative")
            if not math.isclose(math.fsum(distribution), 1.0, rel_tol=1e-9, abs_tol=1e-9):
                raise BenchmarkContractError("candidate distributions must sum to one")


@dataclass(frozen=True, slots=True)
class ArmRun:
    arm: BenchmarkArm
    seed: int
    model_parameters: int
    training_updates: int
    max_candidate_evaluations: int
    observations: tuple[CaseObservation, ...]

    def __post_init__(self) -> None:
        if self.model_parameters < 1 or self.training_updates < 1:
            raise BenchmarkContractError("model parameters and training updates must be positive")
        if self.max_candidate_evaluations < 1:
            raise BenchmarkContractError("candidate budget must be positive")


def _case_id(split: str, seed: int, index: int, target: bytes, positions: Sequence[int]) -> str:
    digest = hashlib.sha256()
    digest.update(SCHEMA.encode("ascii"))
    digest.update(split.encode("utf-8"))
    digest.update(seed.to_bytes(8, "big", signed=True))
    digest.update(index.to_bytes(8, "big"))
    digest.update(target)
    for position in positions:
        digest.update(position.to_bytes(8, "big"))
    return digest.hexdigest()[:24]


def generate_structured_cases(*, split: str, seed: int, count: int) -> tuple[MaskedByteCase, ...]:
    """Generate deterministic structured records without reading model outputs."""

    if split not in {"train", "validation", "test"}:
        raise BenchmarkContractError("split must be train, validation, or test")
    if count < 1:
        raise BenchmarkContractError("count must be positive")
    domain_seed = int.from_bytes(hashlib.sha256(f"{SCHEMA}:{split}:{seed}".encode()).digest()[:8], "big")
    rng = random.Random(domain_seed)
    cases: list[MaskedByteCase] = []
    for index in range(count):
        payload = "".join(chr(rng.randrange(97, 123)) for _ in range(rng.randrange(4, 13)))
        body = {"id": index, "kind": split[0], "payload": payload}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        checksum = hashlib.sha256(canonical).hexdigest()[:8]
        target = canonical[:-1] + f',"sum":"{checksum}"}}'.encode("ascii")
        kind = tuple(MaskKind)[index % len(MaskKind)]
        if kind is MaskKind.SINGLE:
            positions = (rng.randrange(len(target)),)
        elif kind is MaskKind.SPAN:
            width = min(4, len(target))
            start = rng.randrange(0, len(target) - width + 1)
            positions = tuple(range(start, start + width))
        else:
            structure = [offset for offset, value in enumerate(target) if value in b'{}[],:"']
            take = min(4, len(structure))
            positions = tuple(sorted(rng.sample(structure, take)))
        cases.append(
            MaskedByteCase(
                case_id=_case_id(split, seed, index, target, positions),
                split=split,
                target=target,
                masked_positions=positions,
                mask_kind=kind,
            )
        )
    return tuple(cases)


def evaluate_run(cases: Sequence[MaskedByteCase], run: ArmRun) -> dict[str, object]:
    """Validate one run and compute metrics from its auditable observations."""

    case_by_id = {case.case_id: case for case in cases}
    if len(case_by_id) != len(cases):
        raise BenchmarkContractError("case IDs must be unique")
    observation_by_id = {observation.case_id: observation for observation in run.observations}
    if len(observation_by_id) != len(run.observations):
        raise BenchmarkContractError("observation case IDs must be unique")
    if set(observation_by_id) != set(case_by_id):
        raise BenchmarkContractError("every run must cover exactly the same cases")

    exact: list[float] = []
    losses: list[float] = []
    work: list[int] = []
    exact_work: list[int] = []
    passes: list[int] = []
    buckets: dict[str, list[float]] = {kind.value: [] for kind in MaskKind}
    for case_id, case in case_by_id.items():
        observation = observation_by_id[case_id]
        if len(observation.reconstruction) != len(case.target):
            raise BenchmarkContractError("reconstruction length must match its target")
        if len(observation.candidate_distributions) != len(case.masked_positions):
            raise BenchmarkContractError("one candidate distribution is required per masked byte")
        if observation.forward_passes < len(observation.trace):
            raise BenchmarkContractError("forward-pass count cannot be smaller than the routing trace")
        _validate_trace(case, observation)
        candidate_work = sum(step.candidate_evaluations for step in observation.trace)
        if candidate_work > run.max_candidate_evaluations:
            raise BenchmarkContractError("routing trace exceeds the declared candidate budget")
        is_exact = float(
            all(observation.reconstruction[position] == case.target[position] for position in case.masked_positions)
        )
        exact.append(is_exact)
        if is_exact:
            exact_work.append(candidate_work)
        buckets[case.mask_kind.value].append(is_exact)
        for position, distribution in zip(case.masked_positions, observation.candidate_distributions, strict=True):
            target_probability = distribution[case.target[position]]
            if target_probability <= 0.0:
                raise BenchmarkContractError("target byte probability must be positive for finite NLL")
            losses.append(-math.log(target_probability))
        work.append(candidate_work)
        passes.append(observation.forward_passes)

    return {
        "schema": SCHEMA,
        "arm": run.arm.value,
        "seed": run.seed,
        "case_ids": sorted(case_by_id),
        "model_parameters": run.model_parameters,
        "training_updates": run.training_updates,
        "candidate_budget": run.max_candidate_evaluations,
        "exact_recovery": fmean(exact),
        "mean_target_nll": fmean(losses),
        "mean_candidate_evaluations": fmean(work),
        "mean_work_to_exact_recovery": fmean(exact_work) if exact_work else None,
        "mean_forward_passes": fmean(passes),
        "exact_by_mask_kind": {name: fmean(values) for name, values in buckets.items() if values},
    }


def _validate_trace(case: MaskedByteCase, observation: CaseObservation) -> None:
    positions = [step.position for step in observation.trace]
    if [step.step for step in observation.trace] != list(range(len(observation.trace))):
        raise BenchmarkContractError("routing steps must be contiguous from zero")
    if len(set(positions)) != len(positions):
        raise BenchmarkContractError("a masked position may be committed at most once")
    if not set(positions) <= set(case.masked_positions):
        raise BenchmarkContractError("routing trace may select only masked positions")
    distribution_by_position = dict(zip(case.masked_positions, observation.candidate_distributions, strict=True))
    for step in observation.trace:
        if observation.reconstruction[step.position] != step.predicted_byte:
            raise BenchmarkContractError("trace prediction must match the submitted reconstruction")
        distribution = distribution_by_position[step.position]
        predicted = max(range(256), key=distribution.__getitem__)
        if predicted != step.predicted_byte:
            raise BenchmarkContractError("trace prediction must be the candidate-distribution argmax")


def compare_three_arms(
    cases: Sequence[MaskedByteCase], runs: Iterable[ArmRun], *, parameter_tolerance: float = 0.01
) -> dict[str, object]:
    """Compare matched multi-seed runs without blending representation and routing gains."""

    if not 0.0 <= parameter_tolerance <= 1.0:
        raise BenchmarkContractError("parameter_tolerance must be in [0, 1]")
    by_seed: dict[int, dict[BenchmarkArm, ArmRun]] = {}
    for run in runs:
        seed_runs = by_seed.setdefault(run.seed, {})
        if run.arm in seed_runs:
            raise BenchmarkContractError("each seed may contain only one run per arm")
        seed_runs[run.arm] = run
    if len(by_seed) < 3:
        raise BenchmarkContractError("at least three matched seeds are required")

    per_run: list[dict[str, object]] = []
    scores: dict[BenchmarkArm, list[float]] = {arm: [] for arm in BenchmarkArm}
    for seed, seed_runs in sorted(by_seed.items()):
        if set(seed_runs) != set(BenchmarkArm):
            raise BenchmarkContractError(f"seed {seed} does not contain all three arms")
        parameters = [run.model_parameters for run in seed_runs.values()]
        if (max(parameters) - min(parameters)) / max(parameters) > parameter_tolerance:
            raise BenchmarkContractError("model parameter counts are not matched")
        if len({run.training_updates for run in seed_runs.values()}) != 1:
            raise BenchmarkContractError("training update counts are not matched")
        fixed = seed_runs[BenchmarkArm.SIX_VIEW_FIXED]
        adaptive = seed_runs[BenchmarkArm.SIX_VIEW_ADAPTIVE]
        if fixed.max_candidate_evaluations != adaptive.max_candidate_evaluations:
            raise BenchmarkContractError("fixed and adaptive candidate budgets are not matched")
        for arm in BenchmarkArm:
            metrics = evaluate_run(cases, seed_runs[arm])
            per_run.append(metrics)
            scores[arm].append(float(metrics["exact_recovery"]))

    representation = _gain(scores[BenchmarkArm.SIX_VIEW_FIXED], scores[BenchmarkArm.BYTE_BASELINE])
    routing = _gain(scores[BenchmarkArm.SIX_VIEW_ADAPTIVE], scores[BenchmarkArm.SIX_VIEW_FIXED])
    return {
        "schema": SCHEMA,
        "seed_count": len(by_seed),
        "runs": per_run,
        "representation_gain": representation,
        "routing_gain": routing,
    }


def _gain(candidate: Sequence[float], control: Sequence[float]) -> dict[str, float | bool]:
    delta = fmean(candidate) - fmean(control)
    pooled_sd = math.sqrt((stdev(candidate) ** 2 + stdev(control) ** 2) / 2.0)
    threshold = 2.0 * pooled_sd
    return {
        "exact_recovery_delta": delta,
        "pooled_sd": pooled_sd,
        "required_delta": threshold,
        "powered_positive_result": delta > threshold,
    }


def report_json(report: Mapping[str, object]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
