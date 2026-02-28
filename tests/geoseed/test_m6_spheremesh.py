from src.geoseed.composition import DressedBitComposer
from src.geoseed.dressing import BitDresser
from src.geoseed.m6_spheremesh import M6Event, M6SphereMesh


def test_bit_dresser_and_composer_roundtrip_shape():
    dresser = BitDresser(layer_count=14)
    bits = dresser.dress_text("alpha beta gamma", tongue="KO", run_id="t1")

    assert len(bits) == 3
    assert all(len(bit.layer_path) == 14 for bit in bits)
    assert all(len(bit.state21d) == 21 for bit in bits)

    unit = DressedBitComposer().compose(bits, unit_id="u1")
    assert unit.unit_id == "u1"
    assert len(unit.state21d) == 21
    assert unit.confidence > 0


def test_m6_ingest_event_outputs_state21d():
    mesh = M6SphereMesh(resolution=1, signal_dim=16)
    event = M6Event(
        record_id="evt-001",
        summary="governance policy compute security",
        tongue_vector={"RU": 0.5, "CA": 0.3, "UM": 0.2},
        metadata={"source": "test"},
    )

    record = mesh.ingest_event(event, steps=1)

    assert record["record_id"] == "evt-001"
    assert len(record["state21d"]) == 21
    assert mesh.snapshot()["history_count"] == 1


def test_m6_sacred_egg_gate():
    mesh = M6SphereMesh(resolution=1, signal_dim=16)
    mesh.register_egg(
        egg_id="egg-1",
        required_tongues=["KO", "CA", "UM"],
        min_phi_weight=10.0,
        ttl_seconds=600,
    )

    ok, reason = mesh.hatch_egg("egg-1", ["KO", "AV"])
    assert ok is False
    assert "missing_required_tongues" in reason

    ok2, reason2 = mesh.hatch_egg("egg-1", ["KO", "CA", "UM"])
    assert ok2 is True
    assert reason2 == "hatched"
