from src.harmonic.tarski_sheaf import (
    complement_boolean_restriction,
    enumerate_global_sections,
    fail_to_noise_projection,
    is_global_intent_consistent,
    make_temporal_sheaf,
    obstruction_count,
)


TETRADIC = ("Ti", "Tm", "Tg", "Tp")
TRIADIC = ("Ti", "Tm", "Tg")


def test_tetradic_constant_sheaf_has_only_uniform_global_sections() -> None:
    sheaf = make_temporal_sheaf(TETRADIC)

    sections = enumerate_global_sections(sheaf)

    assert {tuple(section[node] for node in TETRADIC) for section in sections} == {
        (0, 0, 0, 0),
        (1, 1, 1, 1),
    }


def test_fail_to_noise_projects_inconsistent_pattern_to_bottom() -> None:
    sheaf = make_temporal_sheaf(TETRADIC)
    local_variant = {"Ti": 1, "Tm": 1, "Tg": 0, "Tp": 1}

    projected = fail_to_noise_projection(sheaf, local_variant)

    assert projected == {"Ti": 0, "Tm": 0, "Tg": 0, "Tp": 0}
    assert is_global_intent_consistent(sheaf, projected)


def test_adversarial_twist_creates_obstruction_from_all_ones() -> None:
    sheaf = make_temporal_sheaf(
        TETRADIC,
        twisted_edges={
            ("Ti", "Tg"): complement_boolean_restriction,
            ("Tg", "Ti"): complement_boolean_restriction,
        },
    )

    all_ones = {node: 1 for node in TETRADIC}

    assert not is_global_intent_consistent(sheaf, all_ones)
    assert obstruction_count(sheaf, all_ones) >= 1


def test_triadic_global_consensus_still_supports_uniform_sections() -> None:
    sheaf = make_temporal_sheaf(TRIADIC)

    sections = enumerate_global_sections(sheaf)

    assert {tuple(section[node] for node in TRIADIC) for section in sections} == {
        (0, 0, 0),
        (1, 1, 1),
    }
