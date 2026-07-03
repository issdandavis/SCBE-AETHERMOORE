from dataclasses import replace

from python.scbe.atomic_tokenization import TritVector, map_token_to_atomic_state
from python.scbe.tongue_code_lanes import (
    KNOWN_CODE_LANES,
    classify_code_lane_alignment,
    expected_code_lanes,
)


def dr_state_with_lane(code_lane: str):
    base = map_token_to_atomic_state("architecture", language="haskell", context_class="architecture")
    return replace(base, code_lane=code_lane, tau=TritVector(KO=0, AV=0, RU=0, CA=0, UM=0, DR=1))


def test_go_is_known_draumric_language_family_lane():
    assert "go" in KNOWN_CODE_LANES
    assert expected_code_lanes(["DR"], profile="language_family") == [
        "haskell",
        "go",
        "typescript",
        "terraform",
        "kotlin",
    ]


def test_go_lane_aligns_when_draumric_language_family_profile_is_explicit():
    alignment = classify_code_lane_alignment([dr_state_with_lane("go")], profile="language_family")

    assert alignment["active_profile"] == "language_family"
    assert alignment["reference_lanes"] == ["make"]
    assert alignment["actual_lanes"] == ["go"]
    assert "go" in alignment["expected_lanes"]
    assert alignment["mismatch_lanes"] == []
    assert alignment["failure_mode"] == "none"
    assert alignment["cross_profile_divergence"] is True


def test_go_lane_does_not_replace_default_draumric_contract():
    alignment = classify_code_lane_alignment([dr_state_with_lane("go")])

    assert alignment["active_profile"] == "computational_isomorphism"
    assert alignment["expected_lanes"] == ["make"]
    assert alignment["actual_lanes"] == ["go"]
    assert alignment["failure_mode"] == "cross_language_degradation"
    assert alignment["operational_failure_risk"] == "HIGH"
