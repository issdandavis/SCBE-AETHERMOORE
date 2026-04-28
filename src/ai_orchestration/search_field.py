"""GeoSeal search-field controls for agent-bus exploration.

This module keeps search movement deterministic and inspectable. It turns a
candidate plus metric signals into a compact trace record:

projection -> grading -> residue -> phase rotation -> constraint decision

The goal is not to replace an optimizer. It provides the governance/control
surface that lets agent harnesses compare candidate movement with and without
phase rotation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Mapping


DEFAULT_PROJECTION_DIMS = ("transform_class", "symmetry", "intent")
DEFAULT_GRADING_AXES = ("structure", "semantic", "consistency")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ProjectionPolicy:
    """Select dimensions that define the unstable search slice."""

    dims: tuple[str, ...] = DEFAULT_PROJECTION_DIMS
    weights: tuple[float, ...] = (1.0, 0.8, 0.6)

    def __post_init__(self) -> None:
        if len(self.dims) != len(self.weights):
            raise ValueError("projection dims and weights must have equal length")
        if not self.dims:
            raise ValueError("projection must define at least one dimension")


@dataclass(frozen=True)
class GradingPolicy:
    """Discrete gemstone-style grading axes."""

    axes: tuple[str, ...] = DEFAULT_GRADING_AXES
    bins: int = 5
    weights: tuple[float, ...] = (1.2, 1.0, 1.1)

    def __post_init__(self) -> None:
        if len(self.axes) != len(self.weights):
            raise ValueError("grading axes and weights must have equal length")
        if self.bins < 2:
            raise ValueError("grading bins must be >= 2")


@dataclass(frozen=True)
class PhasePolicy:
    """Control phase rotation through collapsed residue classes."""

    mapping: str = "weighted_mod_sum"
    scale: float = 2.0
    damping: float = 0.85

    def __post_init__(self) -> None:
        if self.mapping != "weighted_mod_sum":
            raise ValueError("only weighted_mod_sum phase mapping is supported")
        if self.scale <= 0:
            raise ValueError("phase scale must be positive")
        if not 0 < self.damping <= 1:
            raise ValueError("phase damping must be in (0, 1]")


@dataclass(frozen=True)
class ConstraintPolicy:
    """GeoSeal constraint field for candidate acceptance."""

    max_entropy: float = 0.6
    min_agreement: float = 0.5
    harmonic_limit: float = 12.0


@dataclass(frozen=True)
class ConsensusPolicy:
    """Collapse condition for multi-agent agreement."""

    quorum: int = 3
    agreement_threshold: float = 0.7
    max_iterations: int = 12

    def __post_init__(self) -> None:
        if self.quorum < 1:
            raise ValueError("consensus quorum must be >= 1")
        if self.max_iterations < 1:
            raise ValueError("consensus max_iterations must be >= 1")


@dataclass(frozen=True)
class SearchFieldPolicy:
    """Parameterized field governing agent-bus candidate movement."""

    projection: ProjectionPolicy = field(default_factory=ProjectionPolicy)
    modulus: Mapping[str, int] = field(
        default_factory=lambda: {"transform_class": 8, "symmetry": 4, "intent": 6}
    )
    grading: GradingPolicy = field(default_factory=GradingPolicy)
    phase: PhasePolicy = field(default_factory=PhasePolicy)
    constraints: ConstraintPolicy = field(default_factory=ConstraintPolicy)
    consensus: ConsensusPolicy = field(default_factory=ConsensusPolicy)

    def __post_init__(self) -> None:
        missing = [dim for dim in self.projection.dims if dim not in self.modulus]
        if missing:
            raise ValueError(f"missing modulus values for projection dims: {missing}")
        for dim, modulus in self.modulus.items():
            if int(modulus) < 2:
                raise ValueError(f"modulus for {dim!r} must be >= 2")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["modulus"] = dict(self.modulus)
        return payload


@dataclass(frozen=True)
class SearchMetrics:
    """Runtime signals used by constraints and coupling rules."""

    entropy: float = 0.0
    agreement: float = 1.0
    stability: float = 0.0
    harmonic: float = 0.0
    iteration: int = 0

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "SearchMetrics":
        values = values or {}
        return cls(
            entropy=float(values.get("entropy", 0.0)),
            agreement=float(values.get("agreement", 1.0)),
            stability=float(values.get("stability", 0.0)),
            harmonic=float(values.get("harmonic", 0.0)),
            iteration=int(values.get("iteration", 0)),
        )


@dataclass(frozen=True)
class SearchTrace:
    """Single candidate movement record for the agent bus."""

    candidate_id: str
    projection: dict[str, int]
    grade: list[int]
    residue: int
    theta_degrees: float
    score: float
    decision: str
    reasons: list[str]
    policy: dict[str, Any]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_bucket(candidate: Mapping[str, Any], dim: str, modulus: int) -> int:
    raw = candidate.get(dim, "")
    digest = hashlib.sha256(
        json.dumps(raw, sort_keys=True, default=str).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def project_candidate(
    candidate: Mapping[str, Any], policy: SearchFieldPolicy
) -> dict[str, int]:
    """Project a candidate into configured residue dimensions."""

    return {
        dim: _stable_bucket(candidate, dim, int(policy.modulus[dim]))
        for dim in policy.projection.dims
    }


def grade_candidate(
    candidate: Mapping[str, Any], policy: SearchFieldPolicy
) -> list[int]:
    """Return a discrete grade vector in [0, bins - 1]."""

    grades = candidate.get("grades", {})
    output: list[int] = []
    for axis in policy.grading.axes:
        raw = grades.get(axis, candidate.get(axis, 0.0))
        if isinstance(raw, int) and 0 <= raw < policy.grading.bins:
            output.append(raw)
            continue
        normalized = _clamp(float(raw), 0.0, 1.0)
        output.append(round(normalized * (policy.grading.bins - 1)))
    return output


def compute_residue(
    projection: Mapping[str, int], grade: list[int], policy: SearchFieldPolicy
) -> int:
    """Collapse projection and grade into one deterministic residue class."""

    total = 0.0
    modulus_product = 1
    for dim, weight in zip(policy.projection.dims, policy.projection.weights):
        modulus = int(policy.modulus[dim])
        total += projection[dim] * weight
        modulus_product *= modulus
    for value, weight in zip(grade, policy.grading.weights):
        total += value * weight
    return int(round(total)) % modulus_product


def compute_theta_degrees(residue: int, policy: SearchFieldPolicy) -> float:
    """Map a residue class to damped phase rotation in degrees."""

    cycle = max(1, math.prod(int(policy.modulus[dim]) for dim in policy.projection.dims))
    theta = (360.0 * (residue % cycle) / cycle) * policy.phase.scale
    theta *= policy.phase.damping
    return round(theta % 360.0, 6)


def evaluate_constraints(
    metrics: SearchMetrics, policy: SearchFieldPolicy
) -> tuple[str, list[str]]:
    """Return ALLOW/QUARANTINE/DENY plus deterministic reasons."""

    reasons: list[str] = []
    if metrics.entropy > policy.constraints.max_entropy:
        reasons.append("entropy_above_max")
    if metrics.agreement < policy.constraints.min_agreement:
        reasons.append("agreement_below_min")
    if metrics.harmonic > policy.constraints.harmonic_limit:
        reasons.append("harmonic_above_limit")
    if metrics.iteration >= policy.consensus.max_iterations:
        reasons.append("max_iterations_reached")

    if "harmonic_above_limit" in reasons or "max_iterations_reached" in reasons:
        return "DENY", reasons
    if reasons:
        return "QUARANTINE", reasons
    if metrics.agreement >= policy.consensus.agreement_threshold:
        return "ALLOW", ["consensus_ready"]
    return "QUARANTINE", ["consensus_pending"]


def score_candidate(
    grade: list[int], metrics: SearchMetrics, policy: SearchFieldPolicy
) -> float:
    """Compute a compact, bounded comparison score."""

    max_grade = max(1, policy.grading.bins - 1)
    weighted = sum(value * weight for value, weight in zip(grade, policy.grading.weights))
    max_weighted = max_grade * sum(policy.grading.weights)
    grade_score = weighted / max_weighted
    penalty = 0.35 * metrics.entropy + 0.25 * max(0.0, 1.0 - metrics.agreement)
    penalty += 0.20 * max(0.0, metrics.harmonic / max(1.0, policy.constraints.harmonic_limit))
    return round(_clamp(grade_score - penalty, 0.0, 1.0), 6)


def trace_candidate(
    candidate: Mapping[str, Any],
    metrics: Mapping[str, Any] | SearchMetrics | None = None,
    policy: SearchFieldPolicy | None = None,
) -> SearchTrace:
    """Build a deterministic search trace for one candidate."""

    active_policy = policy or SearchFieldPolicy()
    active_metrics = (
        metrics if isinstance(metrics, SearchMetrics) else SearchMetrics.from_mapping(metrics)
    )
    projection = project_candidate(candidate, active_policy)
    grade = grade_candidate(candidate, active_policy)
    residue = compute_residue(projection, grade, active_policy)
    theta = compute_theta_degrees(residue, active_policy)
    decision, reasons = evaluate_constraints(active_metrics, active_policy)
    score = score_candidate(grade, active_metrics, active_policy)
    candidate_id = str(
        candidate.get(
            "id",
            hashlib.sha256(
                json.dumps(candidate, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16],
        )
    )
    return SearchTrace(
        candidate_id=candidate_id,
        projection=projection,
        grade=grade,
        residue=residue,
        theta_degrees=theta,
        score=score,
        decision=decision,
        reasons=reasons,
        policy=active_policy.to_dict(),
        metrics=asdict(active_metrics),
    )


def adapt_policy(
    policy: SearchFieldPolicy, metrics: Mapping[str, Any] | SearchMetrics
) -> SearchFieldPolicy:
    """Apply conservative coupling rules to reduce oscillation.

    Rules:
    - high entropy reduces damping so rotations settle faster
    - low agreement expands phase scale to explore more
    - high stability contracts phase scale to converge
    """

    active_metrics = (
        metrics if isinstance(metrics, SearchMetrics) else SearchMetrics.from_mapping(metrics)
    )
    scale = policy.phase.scale
    damping = policy.phase.damping

    if active_metrics.entropy > policy.constraints.max_entropy:
        damping *= 0.9
    if active_metrics.agreement < policy.constraints.min_agreement:
        scale *= 1.2
    if active_metrics.stability > 0.8:
        scale *= 0.8

    phase = replace(
        policy.phase,
        scale=round(_clamp(scale, 0.1, 8.0), 6),
        damping=round(_clamp(damping, 0.1, 1.0), 6),
    )
    return replace(policy, phase=phase)
