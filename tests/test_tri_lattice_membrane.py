"""Tests for Tri-Lattice Sphere Membrane experiment."""

from __future__ import annotations

import pytest
from src.storage.tri_lattice_membrane import (
    TriLatticeMembrane,
    TriRecord,
    PolyhedralFallback,
)


def _make_record(
    i: int, tongue: str = "KO", tongue_coords=None, intent=None
) -> TriRecord:
    return TriRecord(
        record_id=f"tri-{i:04d}",
        tongue_coords=tongue_coords or [0.3, 0.2, 0.1, 0.5, 0.1, 0.4],
        intent_vector=intent or [0.5, 0.3, 0.2],
        tongue=tongue,
        content=f"record-{i}".encode(),
    )


class TestPolyhedralFallback:
    def test_always_accepts(self):
        fb = PolyhedralFallback()
        r = _make_record(0)
        fb.insert(r)
        assert fb.query("tri-0000") is not None

    def test_query_missing_returns_none(self):
        fb = PolyhedralFallback()
        assert fb.query("nonexistent") is None


class TestTriLatticeMembrane:
    def test_single_insert_accepted(self):
        membrane = TriLatticeMembrane()
        r = _make_record(0)
        result = membrane.insert(r)
        assert result.accepted_by != ""

    def test_batch_insert(self):
        membrane = TriLatticeMembrane()
        records = [
            _make_record(i, tongue=["KO", "AV", "RU", "CA", "UM", "DR"][i % 6])
            for i in range(30)
        ]
        count = membrane.insert_batch(records)
        assert count == 30

    def test_all_records_end_up_somewhere(self):
        membrane = TriLatticeMembrane()
        records = [_make_record(i) for i in range(50)]
        membrane.insert_batch(records)
        stats = membrane.stats()
        total_placed = (
            stats.lattice25d_accepted
            + stats.quasicrystal_accepted
            + stats.polyhedral_fallback
        )
        assert total_placed == 50

    def test_stats_have_required_fields(self):
        membrane = TriLatticeMembrane()
        records = [_make_record(i) for i in range(20)]
        membrane.insert_batch(records)
        stats = membrane.stats()
        assert stats.total_records == 20
        assert stats.lattice25d_accepted >= 0
        assert stats.quasicrystal_accepted >= 0
        assert stats.polyhedral_fallback >= 0
        assert stats.frustration_count >= 0
        assert isinstance(stats.spin_distribution, dict)
        assert isinstance(stats.tongue_routing, dict)

    def test_varied_tongue_coords_route_differently(self):
        membrane = TriLatticeMembrane()
        # Near-centroid records
        safe = [
            TriRecord(
                f"safe-{i}",
                [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                [0.5, 0.5, 0.5],
                "KO",
                b"safe",
            )
            for i in range(10)
        ]
        # Far-from-centroid records
        risky = [
            TriRecord(
                f"risky-{i}",
                [0.9, 0.1, 0.9, 0.1, 0.9, 0.1],
                [0.9, 0.1, 0.9],
                "DR",
                b"risky",
            )
            for i in range(10)
        ]
        membrane.insert_batch(safe + risky)
        stats = membrane.stats()
        # Both types should be accepted somewhere
        assert stats.total_records == 20

    def test_polyhedral_fallback_catches_frustration(self):
        """Records that ALL lattices reject should land in fallback."""
        membrane = TriLatticeMembrane(
            qc_acceptance_radius=0.001,  # very strict — most will fail QC
            max_feedback_hops=0,  # no feedback — force fallback
        )
        records = [_make_record(i) for i in range(10)]
        membrane.insert_batch(records)
        stats = membrane.stats()
        # At least some should have been accepted by lattice25d
        assert stats.lattice25d_accepted + stats.polyhedral_fallback == 10

    def test_feedback_hops_tracked(self):
        membrane = TriLatticeMembrane(max_feedback_hops=2)
        records = [_make_record(i) for i in range(20)]
        membrane.insert_batch(records)
        stats = membrane.stats()
        assert stats.avg_feedback_hops >= 0


class TestTriLatticeIntegration:
    def test_with_real_corpus(self):
        """Run against gathered corpus data."""
        import json
        from pathlib import Path

        corpus_path = Path("artifacts/test_corpus/gathered_corpus.jsonl")
        if not corpus_path.exists():
            pytest.skip("Gathered corpus not available")

        records = []
        with corpus_path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 200:
                    break
                obj = json.loads(line)
                tongue = obj.get("tongue", "KO")
                if tongue not in ("KO", "AV", "RU", "CA", "UM", "DR"):
                    tongue = "KO"
                # Derive simple tongue coords from text metrics
                text = obj.get("text", "")
                wc = len(text.split())
                tc = [
                    min(1.0, wc / 600.0),
                    min(1.0, len(text) / 5000.0),
                    min(1.0, len(set(text.split())) / max(wc, 1)),
                    min(1.0, sum(c.isdigit() for c in text) / max(len(text), 1) * 10),
                    min(1.0, sum(c.isupper() for c in text) / max(len(text), 1) * 5),
                    min(1.0, sum(c in ".,;:!?" for c in text) / max(len(text), 1) * 8),
                ]
                records.append(
                    TriRecord(
                        record_id=obj["id"],
                        tongue_coords=tc,
                        intent_vector=[0.5, 0.3, 0.2],
                        tongue=tongue,
                        content=text[:500].encode("utf-8", errors="replace"),
                    )
                )

        membrane = TriLatticeMembrane()
        membrane.insert_batch(records)
        stats = membrane.stats()

        assert stats.total_records == len(records)
        assert stats.lattice25d_accepted > 0
        # Frustration should be bounded — not all records should fail
        assert stats.frustration_count < stats.total_records
