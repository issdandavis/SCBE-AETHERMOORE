from __future__ import annotations

from hydra.lattice25d_ops import NoteRecord
from src.knowledge.storage_interaction_mesh import StorageInteractionMesh


def test_storage_interaction_mesh_ingests_note_into_all_surfaces() -> None:
    mesh = StorageInteractionMesh(focus_phase_rad=0.5, focus_bandwidth=0.25)
    notes = [
        NoteRecord(
            note_id="storage-note-1",
            text="Governance storage note with routing metrics, spectral overlap, and bounded documentation payload.",
            tags=("storage", "governance"),
            source="test",
            authority="public",
            tongue="DR",
            phase_rad=0.5,
        )
    ]

    records = mesh.ingest_notes(notes)
    stats = mesh.stats()

    assert len(records) == 1
    assert stats["record_count"] == 1
    assert stats["attachment_ring_count"] == 1
    assert stats["entropic_escape_count"] in {0, 1}
    assert stats["adaptive_k_mean"] >= 1
    assert stats["lattice"]["bundle_count"] == 1
    assert stats["hyperbolic_octree"]["point_count"] == 1
    assert stats["quasi_drive"]["total_cells"] == 1
    assert records[0].hyperbolic_realm in {"light_realm", "path", "shadow_realm"}
    assert records[0].adaptive_k >= 1


def test_storage_interaction_mesh_applies_negative_vector_fold() -> None:
    mesh = StorageInteractionMesh(fold_negative_vectors=True, fold_threshold=0.1)
    notes = [
        NoteRecord(
            note_id="storage-note-fold",
            text="quiet quiet quiet quiet quiet quiet quiet quiet",
            tags=("storage", "fold"),
            source="test",
            authority="sealed",
            tongue="KO",
            phase_rad=0.2,
        )
    ]

    records = mesh.ingest_notes(notes)
    stats = mesh.stats()

    assert len(records) == 1
    assert records[0].fold_applied is True
    assert records[0].fold_target_octant is not None
    assert stats["fold_count"] == 1
    assert stats["lattice"]["octree_voxel_count"] >= 2
    assert isinstance(records[0].entropic_escape, bool)
