"""Canonical bijection gate for source-to-target alignment maps.

This is the repo's single route/use contract for known solved problem spaces:

    truth map -> candidate map -> exact bijection audit -> route or do not route

The strict gate is deterministic. If the candidate swaps two known identities,
it fails through `wrong_matches`; no statistical null is needed to reject it.

The optional count-preserving null is kept as a diagnostic tier for approximate
research surfaces: it asks whether identity accuracy beats random relabeling
while preserving the same count. That diagnostic can explain a partial map, but
it never overrides the exact route contract.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping

BIJECTIVE_SOLVER = "BIJECTIVE_SOLVER"
COUNT_PERFECT_IDENTITY_SWAPPED = "COUNT_PERFECT_IDENTITY_SWAPPED"
PARTIAL_ALIGNMENT = "PARTIAL_ALIGNMENT"
INCOMPLETE_OR_HALLUCINATING = "INCOMPLETE_OR_HALLUCINATING"
NON_INJECTIVE = "NON_INJECTIVE"


@dataclass(frozen=True)
class WrongMatch:
    """A known source was present but mapped to the wrong target."""

    source_id: str
    expected_target: str
    predicted_target: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "expected_target": self.expected_target,
            "predicted_target": self.predicted_target,
        }


@dataclass(frozen=True)
class DuplicateTarget:
    """More than one source mapped to the same valid target."""

    target_id: str
    source_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "source_ids": list(self.source_ids),
        }


@dataclass(frozen=True)
class BijectionAudit:
    """Full audit record for a candidate alignment map."""

    schema_version: str
    verdict: str
    reason: str
    is_bijective: bool
    usable_as_router: bool
    expected_count: int
    predicted_count: int
    matched_count: int
    identity_errors: int
    identity_accuracy: float
    null95_identity_accuracy: float | None
    beats_identity_null: bool | None
    misses: tuple[str, ...]
    ghosts: tuple[str, ...]
    target_misses: tuple[str, ...]
    target_ghosts: tuple[str, ...]
    wrong_matches: tuple[WrongMatch, ...]
    duplicate_targets: tuple[DuplicateTarget, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "verdict": self.verdict,
            "reason": self.reason,
            "is_bijective": self.is_bijective,
            "usable_as_router": self.usable_as_router,
            "expected_count": self.expected_count,
            "predicted_count": self.predicted_count,
            "matched_count": self.matched_count,
            "identity_errors": self.identity_errors,
            "identity_accuracy": self.identity_accuracy,
            "null95_identity_accuracy": self.null95_identity_accuracy,
            "beats_identity_null": self.beats_identity_null,
            "misses": list(self.misses),
            "ghosts": list(self.ghosts),
            "target_misses": list(self.target_misses),
            "target_ghosts": list(self.target_ghosts),
            "wrong_matches": [row.to_dict() for row in self.wrong_matches],
            "duplicate_targets": [row.to_dict() for row in self.duplicate_targets],
        }


def audit_bijection(
    truth: Mapping[str, str],
    candidate: Mapping[str, str | None],
    *,
    null_trials: int = 0,
    seed: int = 0,
) -> BijectionAudit:
    """Audit whether `candidate` is a usable bijection against known truth.

    Args:
        truth: Known solved map, source id -> target id. Its target ids must be
            unique.
        candidate: Proposed map, source id -> target id. A value of None is an
            explicit miss.
        null_trials: Optional count-preserving random relabelings used only to
            report whether identity accuracy beats chance.
        seed: RNG seed for the optional null.

    Returns:
        BijectionAudit. `usable_as_router` is true only for an exact bijection:
        no misses, no ghosts, no target misses/ghosts, no duplicate targets, and
        no wrong source-to-target identities.
    """
    if not truth:
        raise ValueError("truth must be non-empty")
    if len(set(truth.values())) != len(truth):
        raise ValueError("truth must be a bijection (its values must be unique)")
    if null_trials < 0:
        raise ValueError("null_trials must be non-negative")

    truth_sources = set(truth)
    candidate_sources = set(candidate)
    truth_targets = set(truth.values())
    assigned_targets = {target for target in candidate.values() if target is not None}
    valid_assigned_targets = assigned_targets & truth_targets

    misses = _sorted_tuple(
        source for source in truth_sources if candidate.get(source) is None
    )
    ghosts = _sorted_tuple(candidate_sources - truth_sources)
    target_misses = _sorted_tuple(truth_targets - valid_assigned_targets)
    target_ghosts = _sorted_tuple(assigned_targets - truth_targets)

    wrong_matches = tuple(
        WrongMatch(
            source_id=source,
            expected_target=truth[source],
            predicted_target=str(candidate[source]),
        )
        for source in sorted(truth_sources & candidate_sources)
        if candidate[source] is not None and candidate[source] != truth[source]
    )
    duplicate_targets = _duplicate_valid_targets(candidate)
    matched_count = sum(
        1
        for source in truth_sources & candidate_sources
        if candidate[source] == truth[source]
    )
    identity_errors = len(wrong_matches)
    identity_accuracy = matched_count / len(truth)

    null95: float | None = None
    beats_null: bool | None = None
    if null_trials:
        null95 = _identity_null95(truth, null_trials=null_trials, seed=seed)
        beats_null = identity_accuracy > null95

    is_bijective = not (
        misses
        or ghosts
        or target_misses
        or target_ghosts
        or wrong_matches
        or duplicate_targets
    )
    verdict, reason = _verdict(
        is_bijective=is_bijective,
        count_perfect=not (
            misses or ghosts or target_misses or target_ghosts or duplicate_targets
        ),
        identity_errors=identity_errors,
        identity_accuracy=identity_accuracy,
        null95=null95,
        beats_null=beats_null,
        misses=len(misses),
        ghosts=len(ghosts) + len(target_ghosts),
        duplicates=len(duplicate_targets),
    )

    return BijectionAudit(
        schema_version="scbe_bijection_gate_v1",
        verdict=verdict,
        reason=reason,
        is_bijective=is_bijective,
        usable_as_router=is_bijective,
        expected_count=len(truth),
        predicted_count=len(candidate),
        matched_count=matched_count,
        identity_errors=identity_errors,
        identity_accuracy=identity_accuracy,
        null95_identity_accuracy=null95,
        beats_identity_null=beats_null,
        misses=misses,
        ghosts=ghosts,
        target_misses=target_misses,
        target_ghosts=target_ghosts,
        wrong_matches=wrong_matches,
        duplicate_targets=duplicate_targets,
    )


def evaluate_bijection(
    truth: Mapping[str, str],
    predicted: Mapping[str, str | None],
    *,
    null_trials: int = 500,
    seed: int = 0,
) -> BijectionAudit:
    """Compatibility wrapper for the statistical-diagnostic form."""
    return audit_bijection(truth, predicted, null_trials=null_trials, seed=seed)


def require_bijective(
    truth: Mapping[str, str], candidate: Mapping[str, str | None]
) -> BijectionAudit:
    """Return the audit or raise when the mapping is not usable as a router."""
    audit = audit_bijection(truth, candidate)
    if not audit.usable_as_router:
        raise ValueError(f"candidate mapping is not bijective: {audit.verdict}")
    return audit


def _sorted_tuple(values) -> tuple[str, ...]:
    return tuple(sorted(str(value) for value in values))


def _duplicate_valid_targets(
    candidate: Mapping[str, str | None],
) -> tuple[DuplicateTarget, ...]:
    by_target: dict[str, list[str]] = defaultdict(list)
    for source_id, target_id in candidate.items():
        if target_id is not None:
            by_target[target_id].append(source_id)

    rows = [
        DuplicateTarget(target_id=str(target_id), source_ids=tuple(sorted(source_ids)))
        for target_id, source_ids in by_target.items()
        if len(source_ids) > 1
    ]
    return tuple(sorted(rows, key=lambda row: row.target_id))


def _identity_null95(truth: Mapping[str, str], *, null_trials: int, seed: int) -> float:
    sources = list(truth)
    targets = list(truth.values())
    rng = random.Random(seed)
    accs: list[float] = []
    for _ in range(null_trials):
        shuffled = targets[:]
        rng.shuffle(shuffled)
        hits = sum(
            1 for idx, source in enumerate(sources) if shuffled[idx] == truth[source]
        )
        accs.append(hits / len(sources))
    return _percentile(accs, 0.95)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(q * len(ordered)))
    return ordered[idx]


def _verdict(
    *,
    is_bijective: bool,
    count_perfect: bool,
    identity_errors: int,
    identity_accuracy: float,
    null95: float | None,
    beats_null: bool | None,
    misses: int,
    ghosts: int,
    duplicates: int,
) -> tuple[str, str]:
    if is_bijective:
        return BIJECTIVE_SOLVER, "exact one-to-one and onto mapping; usable as router"
    if count_perfect and identity_errors:
        if beats_null is True:
            return (
                PARTIAL_ALIGNMENT,
                "count is preserved and identity beats the null, but exact identities are still wrong",
            )
        null_text = "not computed" if null95 is None else f"{null95:.3f}"
        return (
            COUNT_PERFECT_IDENTITY_SWAPPED,
            f"count is preserved but identities are wrong; null95={null_text}",
        )
    if misses or ghosts:
        return (
            INCOMPLETE_OR_HALLUCINATING,
            f"{misses} misses and {ghosts} ghosts; map is not total/sound",
        )
    return (
        NON_INJECTIVE,
        f"{duplicates} duplicate target collisions; map is not injective",
    )
