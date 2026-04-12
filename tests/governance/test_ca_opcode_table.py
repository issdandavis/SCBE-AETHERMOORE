from dataclasses import replace

from python.scbe.ca_opcode_table import ca_opcode_to_atomic_state, validate_ca_table
from python.scbe.tongue_code_lanes import classify_code_lane_alignment


def test_validate_ca_table_passes():
    ok, errors = validate_ca_table()

    assert ok is True
    assert errors == []


def test_ca_opcode_state_binds_explicit_c_lane():
    state = ca_opcode_to_atomic_state(0x03)

    assert state.token == "div"
    assert state.context_class == "ca_opcode"
    assert state.language == "c"
    assert state.code_lane == "c"


def test_ca_opcode_lane_alignment_uses_runtime_profile_and_reports_doc_divergence():
    state = ca_opcode_to_atomic_state(0x00)
    alignment = classify_code_lane_alignment([state], context_class="ca_opcode")

    assert alignment["active_profile"] == "opcode_runtime"
    assert alignment["expected_lanes"] == ["c"]
    assert alignment["reference_lanes"] == ["sql"]
    assert alignment["actual_lanes"] == ["c"]
    assert alignment["failure_mode"] == "none"
    assert alignment["cross_profile_divergence"] is True


def test_ca_opcode_lane_mismatch_is_cross_language_degradation():
    state = replace(ca_opcode_to_atomic_state(0x00), code_lane="python")
    alignment = classify_code_lane_alignment([state], context_class="ca_opcode")

    assert alignment["expected_lanes"] == ["c"]
    assert alignment["actual_lanes"] == ["python"]
    assert alignment["mismatch_count"] == 1
    assert alignment["failure_mode"] == "cross_language_degradation"
    assert alignment["operational_failure_risk"] == "HIGH"
