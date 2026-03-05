"""Tests for the 6D quasi-crystal voxel drive."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import tempfile

import pytest

from src.knowledge.quasicrystal_voxel_drive import QuasiCrystalVoxelDrive


def test_store_and_retrieve_with_correct_vector() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    payload = b"phase-safe-storage"
    coords = [0.2, 0.1, 0.3, 0.7, 0.2, 0.1]

    cell = drive.store("cell-a", payload, coords, category="security")
    assert cell.is_valid is True

    recovered = drive.retrieve("cell-a", coords, strict=True)
    assert recovered == payload


def test_wrong_vector_is_rejected_in_strict_mode() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    payload = b"intent-bound-blob"
    store_coords = [0.3, 0.1, 0.2, 0.8, 0.1, 0.1]
    wrong_coords = [0.9, 0.9, 0.9, 0.1, 0.1, 0.1]

    drive.store("cell-b", payload, store_coords, category="math")
    recovered = drive.retrieve("cell-b", wrong_coords, strict=True)
    assert recovered is None


def test_fail_closed_when_outside_acceptance_window() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    drive.phason_rekey(b"force-window-shift")

    with pytest.raises(PermissionError):
        drive.store(
            "cell-c",
            b"blocked-on-invalid-window",
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            fail_closed=True,
        )


def test_stats_and_sparse_tensor_indexing() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    drive.store("c1", b"a", [0.1, 0.2, 0.3, 0.2, 0.1, 0.0], category="science")
    drive.store("c2", b"b", [0.8, 0.1, 0.2, 0.1, 0.0, 0.0], category="governance")

    stats = drive.stats()
    assert stats["total_cells"] == 2
    assert stats["sparse_tensor_slots"] >= 1
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
        assert "metrics" in parsed
        assert "tiers" in parsed


def test_policy_routing_assigns_valid_storage_tier() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=24)
    entries = [
        ("t1", b"alpha", [0.9, 0.1, 0.1, 0.2, 0.1, 0.0], "ops"),
        ("t2", b"beta", [0.1, 0.7, 0.1, 0.1, 0.1, 0.0], "transport"),
        ("t3", b"gamma", [0.1, 0.1, 0.1, 0.9, 0.1, 0.0], "security"),
    ]

    for cid, payload, coords, category in entries:
        cell = drive.store(cid, payload, coords, category=category)
        assert 0 <= cell.storage_tier <= 2

    stats = drive.stats()
    assert "tiers" in stats
    assert sum(stats["tiers"].values()) == 3


def test_harmonic_modifier_spin_hook_changes_storage_projection() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    coords = [0.25, 0.15, 0.2, 0.6, 0.1, 0.1]
    spin = [0.9, 0.1, 0.0, 0.2, 0.1, 0.7]
    cell = drive.store("spin-cell", b"spin-aware", coords, spin_coherence=spin)

    normalized = drive._validate_coords(coords)
    assert cell.tongue_coords != normalized
    assert drive.retrieve("spin-cell", coords, strict=True, spin_coherence=spin) == b"spin-aware"


def test_red_team_probe_reports_no_unexpected_accepts() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=32)
    coords = [0.35, 0.2, 0.25, 0.75, 0.1, 0.05]
    drive.store("probe-cell", b"probe-payload", coords, category="security")
    report = drive.red_team_probe_near_collision("probe-cell", coords, attempts=48, similarity_min=0.98)

    assert report["status"] in {"ok", "alert"}
    assert report["unexpected_accepts"] == 0
    assert report["near_collision_attempts"] >= 0


def test_metrics_include_expiry_counters_and_export() -> None:
    drive = QuasiCrystalVoxelDrive(resolution=16)
    cell = drive.store("exp-cell", b"expiring", [0.2, 0.2, 0.2, 0.4, 0.2, 0.1], ttl_seconds=5)
    # Force expiry and trigger fail-closed path.
    expired = datetime.now(timezone.utc) - timedelta(seconds=2)
    drive.cells["exp-cell"].expires_at_utc = expired.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert drive.retrieve("exp-cell", cell.tongue_coords, strict=True) is None

    metrics = drive.metrics()
    assert set(metrics.keys()) == {"storage_size_bytes", "memory_count", "expired_total"}
    assert metrics["expired_total"] >= 1

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "metrics.json"
        exported = drive.export_metrics(str(out))
        assert out.exists()
        parsed = json.loads(out.read_text(encoding="utf-8"))
        assert parsed == exported
