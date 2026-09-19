"""Deterministic fleet-composition routing with honest coordination accounting.

This module turns three existing SCBE ideas into one executable control slice:

* CloneTrooper role vectors define what a roster can and cannot observe.
* Agentic Sphere Grid tongue weights define the base cost of activating roles.
* Mars/DTN scenarios define delayed, duplicated, disrupted, and custody-backed links.

Geometry is advisory: it measures coverage and transition continuity. Governance
clearance is a separate hard gate and is checked before any composition is scored.
The receipt digest is an audit checksum, not an authentication mechanism.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
from typing import Iterable, Sequence

import numpy as np

from src.kernel.scattered_sphere import TONGUE_KEYS, TONGUE_WEIGHTS

TONGUES = tuple(TONGUE_KEYS)
GOVERNANCE_TIERS = ("KO", "AV", "RU", "CA", "UM", "DR")
_RANK_TOL = 1e-9


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _validate_vector(vector: Sequence[float], *, name: str) -> tuple[float, ...]:
    values = tuple(float(value) for value in vector)
    if len(values) != len(TONGUES):
        raise ValueError(f"{name} must have {len(TONGUES)} values, got {len(values)}")
    if not all(math.isfinite(value) and value >= 0.0 for value in values):
        raise ValueError(f"{name} values must be finite and non-negative")
    if not any(value > 0.0 for value in values):
        raise ValueError(f"{name} cannot be the zero vector")
    return values


class CoordinationPolicy(str, Enum):
    """Comparable dispatch policies used by the coordinator and benchmark."""

    STICKY = "sticky"
    ROUND_ROBIN = "round_robin"
    DISTANCE = "distance"
    COMPOSITION_AWARE = "composition_aware"
    STABILITY_GUARDED = "stability_guarded"


@dataclass(frozen=True)
class FleetMember:
    """One role-bearing fleet member.

    ``base_cost`` is the unweighted activation cost. ``effective_cost`` applies
    the canonical Agentic Sphere Grid phi weight for the member's tongue.
    """

    member_id: str
    tongue: str
    capability_vector: tuple[float, ...]
    base_cost: float = 1.0
    reliability: float = 0.95
    latency_ticks: int = 1

    def __post_init__(self) -> None:
        if not self.member_id:
            raise ValueError("member_id is required")
        if self.tongue not in TONGUES:
            raise ValueError(f"tongue must be one of {TONGUES}")
        object.__setattr__(
            self,
            "capability_vector",
            _validate_vector(self.capability_vector, name="capability_vector"),
        )
        if not math.isfinite(self.base_cost) or self.base_cost <= 0.0:
            raise ValueError("base_cost must be finite and positive")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be in [0, 1]")
        if self.latency_ticks < 0:
            raise ValueError("latency_ticks cannot be negative")

    @property
    def effective_cost(self) -> float:
        return self.base_cost * TONGUE_WEIGHTS[self.tongue]


@dataclass(frozen=True)
class FleetComposition:
    """A named roster that can be activated as one coordination unit."""

    composition_id: str
    members: tuple[FleetMember, ...]
    max_governance_tier: str
    fixed_overhead: float = 0.0

    def __post_init__(self) -> None:
        if not self.composition_id:
            raise ValueError("composition_id is required")
        if not self.members:
            raise ValueError("a composition needs at least one member")
        if len({member.member_id for member in self.members}) != len(self.members):
            raise ValueError("member IDs must be unique inside a composition")
        if self.max_governance_tier not in GOVERNANCE_TIERS:
            raise ValueError(f"unknown governance tier: {self.max_governance_tier}")
        if not math.isfinite(self.fixed_overhead) or self.fixed_overhead < 0.0:
            raise ValueError("fixed_overhead must be finite and non-negative")

    @property
    def base_cost(self) -> float:
        return self.fixed_overhead + sum(member.effective_cost for member in self.members)

    @property
    def mean_reliability(self) -> float:
        return sum(member.reliability for member in self.members) / len(self.members)

    @property
    def max_latency_ticks(self) -> int:
        return max(member.latency_ticks for member in self.members)


@dataclass(frozen=True)
class FleetTask:
    """A task expressed as a six-tongue requirement vector."""

    task_id: str
    requirement_vector: tuple[float, ...]
    required_governance_tier: str = "KO"
    work_units: float = 1.0
    risk: float = 0.2
    inertia: float = 0.2
    deadline_ticks: int = 20
    minimum_coverage: float = 0.80

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id is required")
        object.__setattr__(
            self,
            "requirement_vector",
            _validate_vector(self.requirement_vector, name="requirement_vector"),
        )
        if self.required_governance_tier not in GOVERNANCE_TIERS:
            raise ValueError(f"unknown governance tier: {self.required_governance_tier}")
        if not math.isfinite(self.work_units) or self.work_units <= 0.0:
            raise ValueError("work_units must be finite and positive")
        if not 0.0 <= self.risk <= 1.0 or not 0.0 <= self.inertia <= 1.0:
            raise ValueError("risk and inertia must be in [0, 1]")
        if self.deadline_ticks <= 0:
            raise ValueError("deadline_ticks must be positive")
        if not 0.0 <= self.minimum_coverage <= 1.0:
            raise ValueError("minimum_coverage must be in [0, 1]")


@dataclass(frozen=True)
class NetworkCondition:
    """Normalized link conditions for deterministic stress simulation."""

    name: str
    base_delay_ticks: int = 0
    duplicate_probability: float = 0.0
    drop_probability: float = 0.0
    reorder_probability: float = 0.0
    custody_retransmit: bool = False
    blackout_ticks: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("network condition name is required")
        if self.base_delay_ticks < 0 or self.blackout_ticks < 0:
            raise ValueError("network delays cannot be negative")
        for name in ("duplicate_probability", "drop_probability", "reorder_probability"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class CompositionGeometry:
    dimension: int
    rank: int
    blind_dimensions: int
    dilution: float
    projector: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class TaskFit:
    coverage: float
    blind_residual: float
    dilution: float


@dataclass(frozen=True)
class TransitionMeasure:
    stability: float
    cost: float
    retained_members: float
    warmed_members: float
    subspace_alignment: float


@dataclass(frozen=True)
class CandidateAssessment:
    composition_id: str
    task_fit: TaskFit
    transition: TransitionMeasure
    execution_cost: float
    estimated_duration_ticks: int
    deadline_overrun_ticks: int
    distance_objective: float
    adaptive_objective: float


@dataclass(frozen=True)
class CoordinationDecision:
    task_id: str
    policy: str
    selected_composition_id: str | None
    outcome: str
    reason: str
    governance_checks: int
    candidate_evaluations: int
    control_cost: float
    assessments: tuple[CandidateAssessment, ...]
    receipt_digest: str


@dataclass(frozen=True)
class MissionMetrics:
    policy: str
    network: str
    seed: int
    tasks: int
    completed: int
    completion_rate: float
    governance_denials: int
    capability_misses: int
    deadline_misses: int
    execution_failures: int
    permanent_losses: int
    state_converged: bool
    transitions: int
    transition_churn: float
    mean_transition_stability: float
    transition_instability: float
    governance_checks: int
    candidate_evaluations: int
    transmissions: int
    duplicates: int
    retransmissions: int
    execution_cost: float
    transition_cost: float
    control_cost: float
    network_cost: float
    total_cost: float
    cost_per_completed: float | None
    utilization: dict[str, int]
    utilization_fairness: float


@lru_cache(maxsize=512)
def composition_geometry(composition: FleetComposition) -> CompositionGeometry:
    """Return rank, blind dimensions, dilution, and row-space projector."""

    basis = np.asarray([member.capability_vector for member in composition.members], dtype=float)
    _u, singular, vt = np.linalg.svd(basis, full_matrices=True)
    rank = int(np.sum(singular > _RANK_TOL))
    if rank:
        span = vt[:rank].T
        projector = span @ span.T
    else:  # Defensive only; zero vectors are rejected at input validation.
        projector = np.zeros((len(TONGUES), len(TONGUES)), dtype=float)
    nonzero = singular[singular > _RANK_TOL]
    if nonzero.size <= 1:
        dilution = 1.0 if nonzero.size else math.inf
    else:
        dilution = float(nonzero[0] / nonzero[-1])
    return CompositionGeometry(
        dimension=len(TONGUES),
        rank=rank,
        blind_dimensions=len(TONGUES) - rank,
        dilution=dilution,
        projector=tuple(tuple(float(value) for value in row) for row in projector),
    )


def task_fit(composition: FleetComposition, task: FleetTask) -> TaskFit:
    """Measure how much of a task lies inside a roster's observable span."""

    requirement = np.asarray(task.requirement_vector, dtype=float)
    projector = np.asarray(composition_geometry(composition).projector, dtype=float)
    projection = projector @ requirement
    norm = float(np.linalg.norm(requirement))
    coverage = _clamp01(float(np.linalg.norm(projection)) / norm)
    blind = _clamp01(float(np.linalg.norm(requirement - projection)) / norm)
    return TaskFit(
        coverage=coverage,
        blind_residual=blind,
        dilution=composition_geometry(composition).dilution,
    )


def transition_measure(
    source: FleetComposition | None,
    destination: FleetComposition,
    *,
    inertia: float,
) -> TransitionMeasure:
    """Measure directional state continuity and reconfiguration cost.

    The transition is directional. Retaining three of three source members is
    different from warming three of six destination members. The geometry term
    compares the two roster subspaces; it cannot grant authority.
    """

    if source is None or source.composition_id == destination.composition_id:
        return TransitionMeasure(1.0, 0.0, 1.0, 1.0, 1.0)

    source_ids = {member.member_id for member in source.members}
    destination_ids = {member.member_id for member in destination.members}
    overlap = len(source_ids & destination_ids)
    retained = overlap / len(source_ids)
    warmed = overlap / len(destination_ids)

    source_geometry = composition_geometry(source)
    destination_geometry = composition_geometry(destination)
    source_projector = np.asarray(source_geometry.projector, dtype=float)
    destination_projector = np.asarray(destination_geometry.projector, dtype=float)
    denominator = max(source_geometry.rank, destination_geometry.rank, 1)
    alignment = _clamp01(float(np.trace(source_projector @ destination_projector)) / denominator)

    stability = _clamp01(0.50 * retained + 0.20 * warmed + 0.30 * alignment)
    cost = destination.base_cost * (1.0 - stability) * (0.5 + _clamp01(inertia))
    return TransitionMeasure(stability, cost, retained, warmed, alignment)


def _tier_allows(composition: FleetComposition, task: FleetTask) -> bool:
    return GOVERNANCE_TIERS.index(composition.max_governance_tier) >= GOVERNANCE_TIERS.index(
        task.required_governance_tier
    )


def _deadline_duration(
    composition: FleetComposition,
    task: FleetTask,
    transition: TransitionMeasure,
    network: NetworkCondition,
) -> int:
    transition_ticks = math.ceil((1.0 - transition.stability) * 5.0 * (1.0 + task.inertia))
    work_ticks = math.ceil(task.work_units)
    reorder_ticks = 1 if network.reorder_probability > 0.0 else 0
    return (
        composition.max_latency_ticks
        + work_ticks
        + transition_ticks
        + network.base_delay_ticks
        + network.blackout_ticks
        + reorder_ticks
    )


def assess_candidate(
    composition: FleetComposition,
    task: FleetTask,
    previous: FleetComposition | None,
    network: NetworkCondition,
) -> CandidateAssessment:
    fit = task_fit(composition, task)
    transition = transition_measure(previous, composition, inertia=task.inertia)
    execution_cost = composition.base_cost * task.work_units
    duration = _deadline_duration(composition, task, transition, network)
    overrun = max(0, duration - task.deadline_ticks)
    finite_dilution = fit.dilution if math.isfinite(fit.dilution) else 1e6
    dilution_penalty = math.log1p(max(0.0, finite_dilution - 1.0))

    # Distance is the size-matched, zero-tuned control. Each direct quantity is
    # mapped to [0, 1), then combined with equal unit weight.
    distance_objective = (
        execution_cost / (1.0 + execution_cost)
        + transition.cost / (1.0 + transition.cost)
        + fit.blind_residual
        + dilution_penalty / (1.0 + dilution_penalty)
        + overrun / (task.deadline_ticks + overrun)
    )

    # The adaptive arm lets task pressure alter the relative penalties. All
    # terms remain observable and are emitted in the decision receipt.
    adaptive_objective = (
        execution_cost
        + transition.cost * (1.0 + 2.0 * task.inertia)
        + 20.0 * fit.blind_residual * (1.0 + 2.0 * task.risk)
        + 2.0 * dilution_penalty
        + 4.0 * overrun
        + composition.max_latency_ticks * (0.25 + task.risk)
    )
    return CandidateAssessment(
        composition_id=composition.composition_id,
        task_fit=fit,
        transition=transition,
        execution_cost=execution_cost,
        estimated_duration_ticks=duration,
        deadline_overrun_ticks=overrun,
        distance_objective=distance_objective,
        adaptive_objective=adaptive_objective,
    )


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class FleetCompositionCoordinator:
    """Select governed fleet compositions and emit deterministic receipts."""

    GOVERNANCE_CHECK_COST = 0.005
    MINIMUM_DWELL_TASKS = 4
    EVALUATION_COST = {
        CoordinationPolicy.STICKY: 0.01,
        CoordinationPolicy.ROUND_ROBIN: 0.01,
        CoordinationPolicy.DISTANCE: 0.04,
        CoordinationPolicy.COMPOSITION_AWARE: 0.08,
        CoordinationPolicy.STABILITY_GUARDED: 0.09,
    }

    def __init__(self, compositions: Iterable[FleetComposition]):
        ordered = sorted(compositions, key=lambda composition: composition.composition_id)
        if not ordered:
            raise ValueError("at least one composition is required")
        if len({composition.composition_id for composition in ordered}) != len(ordered):
            raise ValueError("composition IDs must be unique")
        self.compositions = tuple(ordered)
        self._by_id = {composition.composition_id: composition for composition in ordered}
        self._round_robin_cursor = 0

    def get(self, composition_id: str | None) -> FleetComposition | None:
        return self._by_id.get(composition_id) if composition_id else None

    def select(
        self,
        task: FleetTask,
        *,
        policy: CoordinationPolicy,
        previous_composition_id: str | None,
        previous_dwell_tasks: int = 0,
        network: NetworkCondition,
    ) -> CoordinationDecision:
        previous = self.get(previous_composition_id)
        governance_checks = len(self.compositions)
        eligible = [composition for composition in self.compositions if _tier_allows(composition, task)]
        if not eligible:
            payload = {
                "task_id": task.task_id,
                "policy": policy.value,
                "outcome": "DENY",
                "reason": "no_governance_eligible_composition",
                "governance_checks": governance_checks,
            }
            return CoordinationDecision(
                task_id=task.task_id,
                policy=policy.value,
                selected_composition_id=None,
                outcome="DENY",
                reason="no governance-eligible composition",
                governance_checks=governance_checks,
                candidate_evaluations=0,
                control_cost=governance_checks * self.GOVERNANCE_CHECK_COST,
                assessments=(),
                receipt_digest=_canonical_digest(payload),
            )

        if policy is CoordinationPolicy.STICKY:
            selected = (
                previous
                if previous in eligible
                else min(eligible, key=lambda item: (item.base_cost, item.composition_id))
            )
            assessments = (assess_candidate(selected, task, previous, network),)
        elif policy is CoordinationPolicy.ROUND_ROBIN:
            eligible_ids = {composition.composition_id for composition in eligible}
            selected = eligible[0]
            for offset in range(len(self.compositions)):
                idx = (self._round_robin_cursor + offset) % len(self.compositions)
                candidate = self.compositions[idx]
                if candidate.composition_id in eligible_ids:
                    selected = candidate
                    self._round_robin_cursor = (idx + 1) % len(self.compositions)
                    break
            assessments = (assess_candidate(selected, task, previous, network),)
        else:
            assessments = tuple(assess_candidate(candidate, task, previous, network) for candidate in eligible)
            if policy is CoordinationPolicy.DISTANCE:
                selected_id = min(
                    assessments,
                    key=lambda row: (row.distance_objective, row.composition_id),
                ).composition_id
            else:
                coverage_valid = tuple(
                    row for row in assessments if row.task_fit.coverage + 1e-12 >= task.minimum_coverage
                )
                if not coverage_valid:
                    candidate_evaluations = len(assessments)
                    control_cost = (
                        governance_checks * self.GOVERNANCE_CHECK_COST
                        + candidate_evaluations * self.EVALUATION_COST[policy]
                    )
                    payload = {
                        "task_id": task.task_id,
                        "policy": policy.value,
                        "outcome": "HOLD",
                        "reason": "no_composition_meets_coverage_contract",
                        "previous": previous_composition_id,
                        "network": network.name,
                        "governance_checks": governance_checks,
                        "candidate_evaluations": candidate_evaluations,
                        "control_cost": round(control_cost, 12),
                        "assessments": [asdict(row) for row in assessments],
                    }
                    return CoordinationDecision(
                        task_id=task.task_id,
                        policy=policy.value,
                        selected_composition_id=None,
                        outcome="HOLD",
                        reason="no governance-eligible composition meets minimum coverage",
                        governance_checks=governance_checks,
                        candidate_evaluations=candidate_evaluations,
                        control_cost=control_cost,
                        assessments=assessments,
                        receipt_digest=_canonical_digest(payload),
                    )
                deadline_valid = tuple(row for row in coverage_valid if row.deadline_overrun_ticks == 0)
                adaptive_pool = deadline_valid or coverage_valid
                best = min(
                    adaptive_pool,
                    key=lambda row: (row.adaptive_objective, row.composition_id),
                )
                selected_id = best.composition_id
                if policy is CoordinationPolicy.STABILITY_GUARDED and previous is not None:
                    previous_assessment = next(
                        (row for row in adaptive_pool if row.composition_id == previous.composition_id),
                        None,
                    )
                    if previous_assessment is not None and previous_dwell_tasks < self.MINIMUM_DWELL_TASKS:
                        selected_id = previous.composition_id
            selected = self._by_id[selected_id]

        candidate_evaluations = len(assessments)
        control_cost = (
            governance_checks * self.GOVERNANCE_CHECK_COST + candidate_evaluations * self.EVALUATION_COST[policy]
        )
        payload = {
            "task_id": task.task_id,
            "policy": policy.value,
            "selected": selected.composition_id,
            "previous": previous_composition_id,
            "previous_dwell_tasks": previous_dwell_tasks,
            "network": network.name,
            "governance_checks": governance_checks,
            "candidate_evaluations": candidate_evaluations,
            "control_cost": round(control_cost, 12),
            "assessments": [asdict(row) for row in assessments],
        }
        return CoordinationDecision(
            task_id=task.task_id,
            policy=policy.value,
            selected_composition_id=selected.composition_id,
            outcome="ALLOW",
            reason="governance eligible; selected by policy",
            governance_checks=governance_checks,
            candidate_evaluations=candidate_evaluations,
            control_cost=control_cost,
            assessments=assessments,
            receipt_digest=_canonical_digest(payload),
        )


def _stable_unit(seed: int, *parts: object) -> float:
    material = "|".join([str(seed), *(str(part) for part in parts)]).encode("utf-8")
    value = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return value / float(2**64)


def _jain_fairness(values: Sequence[int]) -> float:
    if not values or sum(values) == 0:
        return 1.0
    numerator = float(sum(values) ** 2)
    denominator = len(values) * float(sum(value * value for value in values))
    return numerator / denominator if denominator else 1.0


def simulate_mission(
    compositions: Sequence[FleetComposition],
    tasks: Sequence[FleetTask],
    *,
    policy: CoordinationPolicy,
    network: NetworkCondition,
    seed: int,
) -> MissionMetrics:
    """Run a deterministic mission and charge every evaluated candidate.

    Duplicate packets are de-duplicated by task ID. Custody retransmission
    guarantees eventual delivery in this bounded model; permanent loss without
    custody is recorded as state divergence.
    """

    coordinator = FleetCompositionCoordinator(compositions)
    previous_id: str | None = None
    dwell_tasks = 0
    completed = governance_denials = capability_misses = deadline_misses = 0
    execution_failures = permanent_losses = 0
    transitions = governance_checks = candidate_evaluations = 0
    transmissions = duplicates = retransmissions = 0
    execution_cost = transition_cost = control_cost = network_cost = 0.0
    transition_stabilities: list[float] = []
    utilization = {composition.composition_id: 0 for composition in compositions}

    for task in tasks:
        decision = coordinator.select(
            task,
            policy=policy,
            previous_composition_id=previous_id,
            previous_dwell_tasks=dwell_tasks,
            network=network,
        )
        governance_checks += decision.governance_checks
        candidate_evaluations += decision.candidate_evaluations
        control_cost += decision.control_cost
        if decision.selected_composition_id is None:
            if decision.outcome == "DENY":
                governance_denials += 1
            else:
                capability_misses += 1
            continue

        selected = coordinator.get(decision.selected_composition_id)
        assert selected is not None
        selected_assessment = next(row for row in decision.assessments if row.composition_id == selected.composition_id)
        utilization[selected.composition_id] += 1
        if previous_id is not None and previous_id != selected.composition_id:
            transitions += 1
            transition_stabilities.append(selected_assessment.transition.stability)
        transition_cost += selected_assessment.transition.cost
        if previous_id == selected.composition_id:
            dwell_tasks += 1
        else:
            dwell_tasks = 1
        previous_id = selected.composition_id

        transmissions += 1
        network_cost += 0.05 * task.work_units
        dropped = _stable_unit(seed, network.name, task.task_id, "drop") < network.drop_probability
        if dropped:
            if network.custody_retransmit:
                retransmissions += 1
                transmissions += 1
                network_cost += 0.05 * task.work_units
            else:
                permanent_losses += 1
                continue

        if _stable_unit(seed, network.name, task.task_id, "duplicate") < network.duplicate_probability:
            duplicates += 1
            transmissions += 1
            network_cost += 0.05 * task.work_units

        fit = selected_assessment.task_fit
        if fit.coverage + 1e-12 < task.minimum_coverage:
            capability_misses += 1
            execution_cost += selected_assessment.execution_cost
            continue

        duration = selected_assessment.estimated_duration_ticks
        if dropped and network.custody_retransmit:
            duration += network.base_delay_ticks + 1
        if duration > task.deadline_ticks:
            deadline_misses += 1
            execution_cost += selected_assessment.execution_cost
            continue

        execution_cost += selected_assessment.execution_cost
        success_probability = _clamp01(
            selected.mean_reliability
            * (0.45 + 0.55 * fit.coverage)
            * (0.75 + 0.25 * selected_assessment.transition.stability)
            * (1.0 - 0.20 * task.risk * fit.blind_residual)
        )
        if _stable_unit(seed, task.task_id, selected.composition_id, "execute") <= success_probability:
            completed += 1
        else:
            execution_failures += 1

    mean_stability = sum(transition_stabilities) / len(transition_stabilities) if transition_stabilities else 1.0
    instability = sum(1.0 - value for value in transition_stabilities)
    total_cost = execution_cost + transition_cost + control_cost + network_cost
    return MissionMetrics(
        policy=policy.value,
        network=network.name,
        seed=seed,
        tasks=len(tasks),
        completed=completed,
        completion_rate=completed / len(tasks) if tasks else 1.0,
        governance_denials=governance_denials,
        capability_misses=capability_misses,
        deadline_misses=deadline_misses,
        execution_failures=execution_failures,
        permanent_losses=permanent_losses,
        state_converged=permanent_losses == 0,
        transitions=transitions,
        transition_churn=transitions / max(len(tasks) - 1, 1),
        mean_transition_stability=mean_stability,
        transition_instability=instability,
        governance_checks=governance_checks,
        candidate_evaluations=candidate_evaluations,
        transmissions=transmissions,
        duplicates=duplicates,
        retransmissions=retransmissions,
        execution_cost=execution_cost,
        transition_cost=transition_cost,
        control_cost=control_cost,
        network_cost=network_cost,
        total_cost=total_cost,
        cost_per_completed=(total_cost / completed if completed else None),
        utilization=utilization,
        utilization_fairness=_jain_fairness(tuple(utilization.values())),
    )


__all__ = [
    "CandidateAssessment",
    "CompositionGeometry",
    "CoordinationDecision",
    "CoordinationPolicy",
    "FleetComposition",
    "FleetCompositionCoordinator",
    "FleetMember",
    "FleetTask",
    "MissionMetrics",
    "NetworkCondition",
    "TaskFit",
    "TransitionMeasure",
    "assess_candidate",
    "composition_geometry",
    "simulate_mission",
    "task_fit",
    "transition_measure",
]
