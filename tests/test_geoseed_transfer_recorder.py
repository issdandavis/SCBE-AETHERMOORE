from __future__ import annotations

import pytest

from src.geoseed.transfer_recorder import (
    LN_PHI,
    AtomTransferRecorder,
    TransferMatrix,
    normalize_tongue,
    transfer_cost,
)


def test_normalize_tongue_accepts_case_and_spaces() -> None:
    assert normalize_tongue(" ca ") == "CA"


def test_normalize_tongue_rejects_unknown_abbreviation() -> None:
    with pytest.raises(ValueError, match="unknown tongue"):
        normalize_tongue("ZZ")


def test_transfer_cost_uses_uniform_ln_phi_shell_hops() -> None:
    assert transfer_cost("KO", "KO") == pytest.approx(0.0)
    assert transfer_cost("KO", "AV") == pytest.approx(LN_PHI)
    assert transfer_cost("KO", "DR") == pytest.approx(5 * LN_PHI)
    assert transfer_cost("UM", "RU") == pytest.approx(2 * LN_PHI)


def test_record_creates_immutable_transfer_event() -> None:
    recorder = AtomTransferRecorder(session_id="unit")
    event = recorder.record("ko", "ru", "seed", metadata={"source": "tokenizer"})

    assert event.from_tongue == "KO"
    assert event.to_tongue == "RU"
    assert event.token == "seed"
    assert event.step == 0
    assert event.geodesic_cost == pytest.approx(2 * LN_PHI)
    assert event.is_self is False
    assert event.metadata == {"source": "tokenizer"}
    assert event.to_dict()["geodesic_cost"] == round(2 * LN_PHI, 12)


def test_record_batch_accepts_tuples_and_mappings() -> None:
    recorder = AtomTransferRecorder()
    events = recorder.record_batch(
        [
            ("KO", "AV", "alpha"),
            {"from_tongue": "AV", "to_tongue": "AV", "token": "hold", "metadata": {"ok": True}},
        ]
    )

    assert len(events) == 2
    assert [event.step for event in events] == [0, 1]
    assert recorder.event_count == 2
    assert events[1].is_self is True
    assert events[1].metadata == {"ok": True}


def test_event_filters_track_token_source_and_destination() -> None:
    recorder = AtomTransferRecorder()
    recorder.record("KO", "RU", "seed")
    recorder.record("AV", "RU", "seed")
    recorder.record("RU", "CA", "branch")

    assert len(recorder.events_for_token("seed")) == 2
    assert [event.token for event in recorder.events_from("RU")] == ["branch"]
    assert [event.from_tongue for event in recorder.events_to("RU")] == ["KO", "AV"]


def test_transfer_matrix_counts_rates_and_dominant_flow() -> None:
    recorder = AtomTransferRecorder()
    recorder.record("KO", "RU", "a")
    recorder.record("KO", "RU", "b")
    recorder.record("KO", "KO", "hold")
    recorder.record("AV", "CA", "c")

    matrix = recorder.transfer_matrix()
    assert isinstance(matrix, TransferMatrix)
    assert len(matrix.counts) == 6
    assert all(len(row) == 6 for row in matrix.counts)
    assert matrix.counts[0][2] == 2
    assert matrix.counts[0][0] == 1
    assert matrix.rates[0][2] == pytest.approx(2 / 3)
    assert matrix.costs[0][2] == round(2 * LN_PHI, 12)
    assert matrix.total_events == 4
    assert matrix.self_transfer_count == 1
    assert matrix.cross_transfer_count == 3
    assert matrix.dominant_flow()[0] == ("KO", "RU", 2)


def test_recorder_to_dict_reports_dominant_flow_with_rate_and_cost() -> None:
    recorder = AtomTransferRecorder()
    recorder.record("KO", "RU", "a")
    recorder.record("KO", "RU", "b")
    recorder.record("KO", "KO", "hold")
    recorder.record("AV", "CA", "c")

    assert recorder.to_dict()["summary"]["dominant_flow"] == {
        "from_tongue": "KO",
        "to_tongue": "RU",
        "count": 2,
        "rate": pytest.approx(2 / 3),
        "geodesic_cost": round(2 * LN_PHI, 12),
    }


def test_empty_matrix_has_no_dominant_flow() -> None:
    matrix = AtomTransferRecorder().transfer_matrix()
    assert matrix.dominant_flow() == []
    assert AtomTransferRecorder().to_dict()["summary"]["dominant_flow"] is None


def test_mean_hop_distance_defaults_to_cross_shell_events() -> None:
    recorder = AtomTransferRecorder()
    recorder.record("KO", "KO", "self")
    recorder.record("KO", "AV", "one")
    recorder.record("KO", "RU", "two")

    assert recorder.total_geodesic_cost() == pytest.approx(3 * LN_PHI)
    assert recorder.mean_hop_distance() == pytest.approx(1.5 * LN_PHI)
    assert recorder.mean_hop_distance(include_self=True) == pytest.approx(LN_PHI)


def test_summary_and_serialization_are_audit_ready() -> None:
    recorder = AtomTransferRecorder(session_id="transfer-test")
    recorder.record("KO", "DR", "deep")

    payload = recorder.to_dict()
    assert payload["schema_version"] == "geoseed_transfer_recorder_v1"
    assert payload["session_id"] == "transfer-test"
    assert payload["summary"]["event_count"] == 1
    assert payload["summary"]["dominant_flow"]["to_tongue"] == "DR"
    assert payload["matrix"]["counts"][0][5] == 1
    assert payload["events"][0]["token"] == "deep"


def test_reset_clears_events_and_step_counter() -> None:
    recorder = AtomTransferRecorder()
    recorder.record("KO", "AV", "first")
    recorder.reset()
    event = recorder.record("AV", "RU", "second")

    assert recorder.event_count == 1
    assert event.step == 0
