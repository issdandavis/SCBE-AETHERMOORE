"""Tests for the 6D quasi-crystal voxel drive.

Tests marked xfail call features that are spec'd but not yet implemented.
When the feature is built, remove the xfail marker.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from src.knowledge.quasicrystal_voxel_drive import QuasiCrystalVoxelDrive

# =========================================================================== #
#  Working tests (match current API)
# =========================================================================== #


def test_store_and_retrieve_with_correct_vector() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    payload = b"phase-safe-storage"
    coords = [0.2, 0.1, 0.3, 0.7, 0.2, 0.1]

    cell = drive.store("cell-a", payload, coords, category="security")
    assert bool(cell.is_valid) is True

    recovered = drive.retrieve("cell-a", coords)
    assert recovered == payload


def test_wrong_vector_returns_noise() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    payload = b"intent-bound-blob"
    store_coords = [0.3, 0.1, 0.2, 0.8, 0.1, 0.1]
    wrong_coords = [0.9, 0.9, 0.9, 0.1, 0.1, 0.1]

    drive.store("cell-b", payload, store_coords, category="math")
    recovered = drive.retrieve("cell-b", wrong_coords)
    # Wrong vector produces noise (XOR with wrong Chladni keystream)
    assert recovered != payload


def test_stats_categories_populated() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    drive.store("c1", b"a", [0.1, 0.2, 0.3, 0.2, 0.1, 0.0], category="science")
    drive.store("c2", b"b", [0.8, 0.1, 0.2, 0.1, 0.0, 0.0], category="governance")

    stats = drive.stats()
    assert stats["total_cells"] == 2
    assert stats["categories"]["science"] == 1
    assert stats["categories"]["governance"] == 1
    assert "phase_distribution" in stats


def test_export_writes_valid_json() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    drive.store("c3", b"export-check", [0.1, 0.1, 0.1, 0.2, 0.3, 0.4], category="data")

    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "qc_drive.json"
        exported = drive.export(str(out_path))
        assert Path(exported).exists()

        parsed = json.loads(Path(exported).read_text(encoding="utf-8"))
        assert parsed["drive_type"] == "QuasiCrystalVoxelDrive"
        assert parsed["dimensions"] == 6
        assert parsed["total_cells"] == 1


def test_phason_rekey_changes_epoch() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    epoch_before = drive._phason_epoch
    drive.phason_rekey(b"new-entropy")
    assert drive._phason_epoch == epoch_before + 1


def test_query_nearby_finds_close_cells() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    drive.store("near-1", b"a", [0.3, 0.1, 0.2, 0.7, 0.1, 0.1])
    drive.store("near-2", b"b", [0.35, 0.1, 0.2, 0.7, 0.1, 0.1])
    drive.store("far-1", b"c", [0.9, 0.9, 0.9, 0.1, 0.1, 0.1])

    nearby = drive.query_nearby([0.3, 0.1, 0.2, 0.7, 0.1, 0.1], radius=0.3)
    assert "near-1" in nearby
    assert "near-2" in nearby


def test_get_slab_returns_tongue_data() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    drive.store("s1", b"data", [0.1, 0.1, 0.1, 0.8, 0.1, 0.1], category="test")
    slab = drive.get_slab("CA")  # CA should be dominant for [0.1,0.1,0.1,0.8,0.1,0.1]
    assert isinstance(slab, dict)


def test_multiple_stores_in_same_slab() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    for i in range(5):
        drive.store(
            f"batch-{i}",
            f"data-{i}".encode(),
            [0.1, 0.1, 0.1, 0.8, 0.1, 0.1 + i * 0.01],
        )
    stats = drive.stats()
    assert stats["total_cells"] == 5


def test_depth_tree_parent_child() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    drive.store("parent", b"root", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5], category="root")
    drive.store(
        "child",
        b"leaf",
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        category="leaf",
        parent_id="parent",
    )
    assert drive.cells["child"].depth == 1
    assert "child" in drive.cells["parent"].children


# =========================================================================== #
#  Spec'd but unimplemented — xfail until built
# =========================================================================== #


@pytest.mark.xfail(reason="strict mode not yet implemented on retrieve()")
def test_strict_retrieve_rejects_wrong_vector() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    drive.store("cell-strict", b"data", [0.3, 0.1, 0.2, 0.8, 0.1, 0.1])
    recovered = drive.retrieve("cell-strict", [0.9, 0.9, 0.9, 0.1, 0.1, 0.1], strict=True)
    assert recovered is None


@pytest.mark.xfail(reason="fail_closed not yet implemented on store()")
def test_fail_closed_rejects_outside_window() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    drive.phason_rekey(b"shift")
    with pytest.raises(PermissionError):
        drive.store("cell-fc", b"data", [0.0] * 6, fail_closed=True)


@pytest.mark.xfail(reason="storage_tier not yet on VoxelCell")
def test_storage_tier_assigned() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=24)
    cell = drive.store("tier-1", b"data", [0.9, 0.1, 0.1, 0.2, 0.1, 0.0], category="ops")
    assert 0 <= cell.storage_tier <= 2


@pytest.mark.xfail(reason="spin_coherence not yet implemented")
def test_spin_coherence_affects_projection() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    spin = [0.9, 0.1, 0.0, 0.2, 0.1, 0.7]
    cell = drive.store("spin-cell", b"data", [0.25, 0.15, 0.2, 0.6, 0.1, 0.1], spin_coherence=spin)
    assert cell is not None


@pytest.mark.xfail(reason="red_team_probe not yet implemented")
def test_red_team_probe() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    coords = [0.35, 0.2, 0.25, 0.75, 0.1, 0.05]
    drive.store("probe-cell", b"data", coords)
    report = drive.red_team_probe_near_collision("probe-cell", coords, attempts=48)
    assert report["unexpected_accepts"] == 0


@pytest.mark.xfail(reason="ttl_seconds / expiry not yet implemented")
def test_ttl_expiry() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    cell = drive.store("exp-cell", b"data", [0.2] * 6, ttl_seconds=5)
    assert cell is not None
