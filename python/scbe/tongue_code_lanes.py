"""
Tongue-to-code-lane contracts for SCBE.

This layer turns language/paradigm alignment into an explicit runtime contract
instead of passive metadata. It supports two distinct views:

- computational_isomorphism:
    The paradigm mapping documented in TONGUE_ISOMORPHISM_PROOF.md
- opcode_runtime:
    Concrete execution-lane mappings used by tongue-specific opcode tables
"""

from __future__ import annotations

from typing import Iterable, Sequence

from .atomic_tokenization import AtomicTokenState, TONGUES


CODE_LANE_REGISTRY = {
    "computational_isomorphism": {
        "KO": "lisp",
        "AV": "python",
        "RU": "forth",
        "CA": "sql",
        "UM": "assembly",
        "DR": "make",
    },
    "opcode_runtime": {
        "CA": "c",
    },
}

KNOWN_CODE_LANES = {
    "assembly",
    "c",
    "forth",
    "lisp",
    "make",
    "python",
    "rust",
    "sql",
    "typescript",
}


def infer_contract_tongues(
    states: Sequence[AtomicTokenState],
    *,
    context_class: str | None = None,
) -> list[str]:
    context = (context_class or "").strip().lower()
    if context.endswith("_opcode"):
        prefix = context.split("_", 1)[0].upper()
        if prefix in TONGUES:
            return [prefix]

    scores = {tongue: 0 for tongue in TONGUES}
    for state in states:
        tau = state.tau.as_dict()
        for tongue, value in tau.items():
            if value == 1:
                scores[tongue] += 1

    max_score = max(scores.values()) if scores else 0
    if max_score <= 0:
        return []
    return [tongue for tongue, score in scores.items() if score == max_score]


def infer_code_lanes(states: Sequence[AtomicTokenState]) -> list[str]:
    lanes: list[str] = []
    for state in states:
        candidate = (state.code_lane or "").strip().lower()
        if candidate in KNOWN_CODE_LANES and candidate not in lanes:
            lanes.append(candidate)
    return lanes


def default_code_lane_profile(*, context_class: str | None = None) -> str:
    context = (context_class or "").strip().lower()
    if context.endswith("_opcode"):
        return "opcode_runtime"
    return "computational_isomorphism"


def expected_code_lanes(
    tongues: Iterable[str],
    *,
    profile: str,
) -> list[str]:
    mapping = CODE_LANE_REGISTRY.get(profile, {})
    lanes: list[str] = []
    for tongue in tongues:
        lane = mapping.get(tongue)
        if lane and lane not in lanes:
            lanes.append(lane)
    return lanes


def classify_code_lane_alignment(
    states: Sequence[AtomicTokenState],
    *,
    context_class: str | None = None,
    profile: str | None = None,
) -> dict:
    contract_tongues = infer_contract_tongues(states, context_class=context_class)
    active_profile = profile or default_code_lane_profile(context_class=context_class)
    reference_profile = "computational_isomorphism"

    expected = expected_code_lanes(contract_tongues, profile=active_profile)
    reference = expected_code_lanes(contract_tongues, profile=reference_profile)
    actual = infer_code_lanes(states)

    mismatch = [lane for lane in actual if lane not in expected]
    overlap = [lane for lane in actual if lane in expected]
    mismatch_count = len(mismatch)
    actual_count = len(actual)
    degradation_score = float(mismatch_count / max(1, actual_count))

    if actual_count == 0:
        failure_mode = "no_code_lane_bound"
        operational_failure_risk = "LOW"
    elif mismatch_count == 0:
        failure_mode = "none"
        operational_failure_risk = "LOW"
    elif not overlap:
        failure_mode = "cross_language_degradation"
        operational_failure_risk = "HIGH"
    else:
        failure_mode = "partial_lane_mismatch"
        operational_failure_risk = "MEDIUM"

    return {
        "contract_tongues": contract_tongues,
        "active_profile": active_profile,
        "reference_profile": reference_profile,
        "expected_lanes": expected,
        "reference_lanes": reference,
        "actual_lanes": actual,
        "mismatch_lanes": mismatch,
        "mismatch_count": mismatch_count,
        "degradation_score": degradation_score,
        "cross_profile_divergence": sorted(expected) != sorted(reference),
        "failure_mode": failure_mode,
        "operational_failure_risk": operational_failure_risk,
    }


__all__ = [
    "CODE_LANE_REGISTRY",
    "KNOWN_CODE_LANES",
    "infer_contract_tongues",
    "infer_code_lanes",
    "default_code_lane_profile",
    "expected_code_lanes",
    "classify_code_lane_alignment",
]
