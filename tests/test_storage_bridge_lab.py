"""Tests for the multi-surface storage bridge lab."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from hydra.lattice25d_ops import NoteRecord
from scripts.system.storage_bridge_lab import (
    HYPOTHESIS_DECK,
    BridgeConfig,
    StorageBridgeLab,
    build_bridge_workload,
    get_hypothesis_deck,
    _mirror_coord,
    _note_to_geometry,
)

# --------------------------------------------------------------------------- #
#  Workload
# --------------------------------------------------------------------------- #


def test_bridge_workload_is_deterministic():
    first = build_bridge_workload(seed=99, count=16)
    second = build_bridge_workload(seed=99, count=16)
    assert len(first) == 16
    assert [n.note_id for n in first] == [n.note_id for n in second]
    assert [n.text for n in first] == [n.text for n in second]


def test_workload_covers_all_tongues():
    notes = build_bridge_workload(seed=1, count=12)
    tongues = {n.tongue for n in notes}
    assert tongues == {"KO", "AV", "RU", "CA", "UM", "DR"}


def test_workload_covers_all_authorities():
    notes = build_bridge_workload(seed=1, count=12)
    auths = {n.authority for n in notes}
    assert auths == {"public", "sealed", "pilot"}


# --------------------------------------------------------------------------- #
#  Geometry derivation
# --------------------------------------------------------------------------- #


def test_note_to_geometry_returns_required_keys():
    note = NoteRecord(note_id="test-001", text="Sample governance audit record.")
    geo = _note_to_geometry(note, 0)

    assert "coord_3d" in geo
    assert "tongue_coords" in geo
    assert "intent_vector" in geo
    assert "realm" in geo
    assert len(geo["tongue_coords"]) == 6
    assert len(geo["intent_vector"]) == 3
    assert np.linalg.norm(geo["coord_3d"]) < 0.94


def test_geometry_coord_stays_in_poincare_ball():
    notes = build_bridge_workload(seed=7, count=50)
    for idx, note in enumerate(notes):
        geo = _note_to_geometry(note, idx)
        assert np.linalg.norm(geo["coord_3d"]) < 0.94, f"Note {idx} escaped ball"


def test_tongue_coords_are_bounded():
    notes = build_bridge_workload(seed=3, count=20)
    for idx, note in enumerate(notes):
        geo = _note_to_geometry(note, idx)
        for i, val in enumerate(geo["tongue_coords"]):
            assert 0.0 <= val <= 1.0, f"tongue_coords[{i}] = {val} out of [0,1]"


# --------------------------------------------------------------------------- #
#  Negative-vector fold
# --------------------------------------------------------------------------- #


def test_mirror_coord_returns_none_for_positive_intent():
    coord = np.array([0.3, 0.2, 0.1])
    result = _mirror_coord(coord, [0.5, 0.8, 0.3])
    assert result is None


def test_mirror_coord_flips_negative_axes():
    coord = np.array([0.3, 0.2, 0.1])
    result = _mirror_coord(coord, [-0.5, 0.8, -0.3])
    assert result is not None
    assert result[0] < 0  # x flipped
    assert result[1] > 0  # y unchanged
    assert result[2] < 0  # z flipped


def test_mirror_coord_stays_in_ball():
    coord = np.array([0.9, 0.1, 0.05])
    result = _mirror_coord(coord, [-1.0, -1.0, -1.0])
    assert result is not None
    assert np.linalg.norm(result) <= 0.94


# --------------------------------------------------------------------------- #
#  Bridge: all 4 surfaces receive records
# --------------------------------------------------------------------------- #


def test_ingest_returns_4_receipts_per_record():
    lab = StorageBridgeLab(BridgeConfig(negative_fold=False))
    note = NoteRecord(note_id="r-001", text="Simple test record for bridge.")
    receipts = lab.ingest(note)

    surfaces = {r.surface for r in receipts}
    assert surfaces == {"octree", "lattice25d", "qc_drive", "sphere"}
    assert all(r.stored for r in receipts)


def test_ingest_with_fold_may_add_fifth_receipt():
    lab = StorageBridgeLab(BridgeConfig(negative_fold=True))
    # Force a note whose intent will have a component that _might_ go negative
    # (intent_from_metrics produces [governance, research, cohesion] all >= 0.2,
    #  so fold won't actually fire — but the path still works)
    note = NoteRecord(note_id="fold-001", text="Test fold record." * 20)
    receipts = lab.ingest(note)
    # Should have at least octree, lattice25d, qc_drive, sphere
    surfaces = [r.surface for r in receipts]
    assert "octree" in surfaces
    assert "lattice25d" in surfaces
    assert "qc_drive" in surfaces
    assert "sphere" in surfaces


def test_batch_ingest_counts():
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=5, count=10)
    count = lab.ingest_batch(notes)
    assert count == 10
    assert lab.record_count == 10


# --------------------------------------------------------------------------- #
#  Compare: metrics from all surfaces
# --------------------------------------------------------------------------- #


def test_compare_returns_all_surfaces():
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=8, count=16)
    lab.ingest_batch(notes)
    report = lab.compare()

    assert "surfaces" in report
    assert set(report["surfaces"].keys()) == {
        "octree",
        "lattice25d",
        "qc_drive",
        "sphere",
    }
    assert report["record_count"] == 16


def test_compare_node_explosion_is_positive():
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=9, count=20)
    lab.ingest_batch(notes)
    report = lab.compare()

    for name, surface in report["surfaces"].items():
        assert surface["node_explosion"] >= 0, f"{name} node_explosion negative"


def test_compare_compaction_scores_are_positive():
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=10, count=20)
    lab.ingest_batch(notes)
    report = lab.compare()

    for name in ("octree", "lattice25d", "qc_drive"):
        assert report["surfaces"][name]["compaction_score"] > 0, f"{name} compaction zero"


def test_compare_governance_trace_rate_nonzero():
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=11, count=12)
    lab.ingest_batch(notes)
    report = lab.compare()

    for surface, rate in report["governance_trace_rate"].items():
        assert rate > 0, f"{surface} governance trace rate is 0"


def test_compare_summary_picks_winners():
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=12, count=20)
    lab.ingest_batch(notes)
    report = lab.compare()

    assert report["summary"]["best_compaction"] in ("octree", "lattice25d", "qc_drive")
    assert report["summary"]["lowest_node_explosion"] in (
        "octree",
        "lattice25d",
        "qc_drive",
        "sphere",
    )


# --------------------------------------------------------------------------- #
#  Export
# --------------------------------------------------------------------------- #


def test_export_writes_valid_json(tmp_path: Path):
    lab = StorageBridgeLab()
    notes = build_bridge_workload(seed=13, count=8)
    lab.ingest_batch(notes)

    out = tmp_path / "bridge_test.json"
    lab.export(str(out))

    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "surfaces" in data
    assert "hypothesis_deck" in data
    assert len(data["hypothesis_deck"]) == len(HYPOTHESIS_DECK)


# --------------------------------------------------------------------------- #
#  Hypothesis deck
# --------------------------------------------------------------------------- #


def test_hypothesis_deck_has_required_fields():
    deck = get_hypothesis_deck()
    required = {
        "knob",
        "surface",
        "purpose",
        "expected_effect",
        "metric_to_watch",
        "fail_condition",
        "sweep_values",
    }
    for card in deck:
        assert required.issubset(card.keys()), f"Card {card['knob']} missing fields"
        assert len(card["sweep_values"]) >= 2, f"Card {card['knob']} needs >=2 sweep values"


def test_hypothesis_deck_covers_all_surfaces():
    deck = get_hypothesis_deck()
    surfaces = {card["surface"] for card in deck}
    assert surfaces == {"octree", "lattice25d", "qc_drive", "sphere"}


# --------------------------------------------------------------------------- #
#  Config knob isolation
# --------------------------------------------------------------------------- #


def test_different_configs_produce_different_metrics():
    """Two configs with different octree depths should produce different node counts."""
    notes = build_bridge_workload(seed=14, count=16)

    lab_shallow = StorageBridgeLab(BridgeConfig(octree_max_depth=3))
    lab_shallow.ingest_batch(notes)
    r_shallow = lab_shallow.compare()

    lab_deep = StorageBridgeLab(BridgeConfig(octree_max_depth=6))
    lab_deep.ingest_batch(notes)
    r_deep = lab_deep.compare()

    # Deeper octree should have more nodes
    assert r_deep["surfaces"]["octree"]["node_count"] >= r_shallow["surfaces"]["octree"]["node_count"]
