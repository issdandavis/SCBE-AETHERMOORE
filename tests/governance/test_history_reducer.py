import math
from dataclasses import replace

from python.scbe.ca_opcode_table import ca_opcode_to_atomic_state
from python.scbe.history_reducer import (
    FibonacciTrustLadder,
    reduce_atomic_history,
    reduce_years,
)


def test_fibonacci_trust_ladder_accrues_and_trims_window():
    ladder = FibonacciTrustLadder(max_window=5)

    for _ in range(6):
        ladder.update(0.0)

    assert len(ladder.values) == 5
    assert ladder.current > 1.0
    assert 0.3 <= ladder.factor() <= 1.8


def test_fibonacci_trust_ladder_records_betrayal_decay():
    ladder = FibonacciTrustLadder()
    ladder.update(0.0)
    before = ladder.current

    after = ladder.update(1.0)

    assert ladder.betrayal_count == 1
    assert after < before


def test_reduce_atomic_history_emits_checkpoint_and_trust_state():
    state, result = reduce_atomic_history(["after", "build", "the", "compiler"])

    assert len(state.memory) == 1
    assert math.isclose(state.memory[0]["trust_level"], result.trust_level)
    assert math.isclose(state.memory[0]["rhombic_score"], result.rhombic_score)
    assert state.memory[0]["tokens"] == ["after", "build", "the", "compiler"]
    assert result.dual_state in (0, 1)
    assert "lane_alignment" in result.checkpoint
    assert result.drift_norm >= 0.0
    assert len(result.drift_components) == 4


def test_reduce_atomic_history_detects_negative_betrayal_packet():
    state, _ = reduce_atomic_history(["build", "allow", "after"])
    state, result = reduce_atomic_history(
        ["not", "deny", "never", "without"],
        state=state,
        context_class="safety",
    )

    assert result.betrayal_delta == 1.0
    assert state.trust_ladder.betrayal_count == 1


def test_reduce_years_preserves_path_dependence():
    state = reduce_years(
        [
            ["build", "allow", "after"],
            ["not", "deny", "never", "without"],
            ["after", "write", "the", "record"],
        ],
        context_class="timeline",
    )

    assert len(state.memory) == 3
    assert state.memory[1]["betrayal_count"] >= 1


def test_negative_packet_has_higher_drift_than_positive_packet():
    _, positive = reduce_atomic_history(["build", "allow", "after"], context_class="timeline")
    _, negative = reduce_atomic_history(["not", "deny", "never", "without"], context_class="safety")

    assert negative.negative_ratio > positive.negative_ratio
    assert negative.drift_norm > positive.drift_norm


def test_reduce_atomic_history_flags_cross_language_degradation_for_misaligned_opcode_state():
    bad_state = replace(ca_opcode_to_atomic_state(0x00), code_lane="python")
    state, result = reduce_atomic_history(
        atomic_states=[bad_state],
        context_class="ca_opcode",
    )

    assert len(state.memory) == 1
    assert result.lane_alignment["expected_lanes"] == ["c"]
    assert result.lane_alignment["actual_lanes"] == ["python"]
    assert result.lane_alignment["failure_mode"] == "cross_language_degradation"
    assert result.checkpoint["lane_alignment"]["operational_failure_risk"] == "HIGH"
