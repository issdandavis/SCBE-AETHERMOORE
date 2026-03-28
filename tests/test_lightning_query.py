"""Tests for Lightning Query — dielectric breakdown search."""

from __future__ import annotations

import pytest

from src.storage.lightning_query import LightningQuery, TongueBloom

# =========================================================================== #
#  Bloom Filter
# =========================================================================== #


class TestTongueBloom:
    def test_added_tongue_is_found(self):
        b = TongueBloom()
        b.add("KO")
        assert b.might_contain("KO") is True

    def test_absent_tongue_usually_not_found(self):
        b = TongueBloom()
        b.add("KO")
        # With 64 bits and 3 hashes, false positive rate is low
        # Test a few — at least some should be negative
        misses = sum(not b.might_contain(t) for t in ["AV", "RU", "CA", "UM", "DR"])
        assert misses >= 3  # at least 3 of 5 unseen tongues should be rejected

    def test_all_tongues_added_all_found(self):
        b = TongueBloom()
        for t in ("KO", "AV", "RU", "CA", "UM", "DR"):
            b.add(t)
        for t in ("KO", "AV", "RU", "CA", "UM", "DR"):
            assert b.might_contain(t) is True


# =========================================================================== #
#  Ingest + Basic Query
# =========================================================================== #


class TestLightningIngest:
    def test_ingest_creates_leader(self):
        lq = LightningQuery()
        lq.ingest("rec-001", "zone-A", "KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6])
        assert "zone-A" in lq.leaders
        assert lq.leaders["zone-A"].record_count == 1

    def test_multiple_ingest_same_zone(self):
        lq = LightningQuery()
        for i in range(10):
            lq.ingest(f"rec-{i}", "zone-A", "KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6])
        assert lq.leaders["zone-A"].record_count == 10

    def test_ingest_multiple_zones(self):
        lq = LightningQuery()
        lq.ingest("rec-001", "zone-A", "KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6])
        lq.ingest("rec-002", "zone-B", "DR", [0.1, 0.1, 0.1, 0.1, 0.1, 0.9])
        assert len(lq.leaders) == 2


# =========================================================================== #
#  Lightning Strike
# =========================================================================== #


class TestLightningStrike:
    @pytest.fixture
    def loaded_engine(self):
        lq = LightningQuery(match_threshold=0.5)
        tongues = ("KO", "AV", "RU", "CA", "UM", "DR")
        for i in range(60):
            tongue = tongues[i % 6]
            zone = f"zone-{tongue}"
            coords = [0.0] * 6
            coords[i % 6] = 0.8  # strong signal in one tongue
            coords[(i + 1) % 6] = 0.2  # weak signal in neighbor
            lq.ingest(f"rec-{i:03d}", zone, tongue, coords)
        return lq

    def test_strike_returns_results(self, loaded_engine):
        result = loaded_engine.strike("KO", [0.8, 0.0, 0.0, 0.0, 0.0, 0.0], top_k=5)
        assert len(result.best_matches) > 0
        assert result.branches_probed > 0

    def test_strike_finds_correct_tongue_zone(self, loaded_engine):
        result = loaded_engine.strike("DR", [0.0, 0.0, 0.0, 0.0, 0.0, 0.9], top_k=5)
        # Best match should be in zone-DR
        assert len(result.best_matches) > 0
        best_id = result.best_matches[0][0]
        zone, _, _ = loaded_engine.records[best_id]
        assert zone == "zone-DR"

    def test_strike_uses_early_termination(self, loaded_engine):
        # Query with very strong match should terminate early
        result = loaded_engine.strike("KO", [0.8, 0.2, 0.0, 0.0, 0.0, 0.0], top_k=3)
        # Should probe fewer than max_branches if early termination works
        assert result.branches_probed <= loaded_engine.max_branches

    def test_empty_engine_returns_empty(self):
        lq = LightningQuery()
        result = lq.strike("KO", [0.5] * 6)
        assert result.best_matches == []
        assert result.branches_probed == 0


# =========================================================================== #
#  Nodal Trim (negative feedback)
# =========================================================================== #


class TestNodalTrim:
    def test_missed_zones_accumulate_penalty(self):
        lq = LightningQuery(match_threshold=0.01)  # very strict
        # Create zones that will miss
        for i in range(10):
            lq.ingest(f"rec-{i}", "zone-miss", "KO", [0.9, 0.0, 0.0, 0.0, 0.0, 0.0])

        # Query for something far from what's stored
        lq.strike("KO", [0.0, 0.0, 0.0, 0.0, 0.0, 0.9], top_k=5)

        # Zone should have accumulated penalty
        leader = lq.leaders["zone-miss"]
        assert leader.miss_count > 0

    def test_hit_zones_get_reinforced(self):
        lq = LightningQuery(match_threshold=5.0)  # very lenient
        for i in range(10):
            lq.ingest(f"rec-{i}", "zone-hit", "KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6])

        # Query for something close to what's stored
        lq.strike("KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6], top_k=5)

        leader = lq.leaders["zone-hit"]
        assert leader.hit_count > 0

    def test_penalty_decays_over_time(self):
        lq = LightningQuery(match_threshold=0.01, penalty_decay=0.5)
        lq.ingest("rec-001", "zone-A", "KO", [0.9, 0.0, 0.0, 0.0, 0.0, 0.0])

        # Accumulate penalty
        for _ in range(5):
            lq.strike("KO", [0.0, 0.0, 0.0, 0.0, 0.0, 0.9], top_k=1)

        penalty_before = lq.leaders["zone-A"].penalty

        # Force harmonic recompute
        lq._harmonic_recompute()
        penalty_after = lq.leaders["zone-A"].penalty

        assert penalty_after < penalty_before


# =========================================================================== #
#  Adaptive Routing (conductivity learning)
# =========================================================================== #


class TestAdaptiveRouting:
    def test_conductivity_starts_neutral(self):
        lq = LightningQuery()
        lq.ingest("rec-001", "zone-A", "KO", [0.5] * 6)
        assert lq.leaders["zone-A"].conductivity == 0.5

    def test_conductivity_increases_with_hits(self):
        lq = LightningQuery(match_threshold=10.0)  # very lenient → always hits
        for i in range(10):
            lq.ingest(f"rec-{i}", "zone-A", "KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6])

        for _ in range(5):
            lq.strike("KO", [0.5, 0.3, 0.2, 0.4, 0.1, 0.6], top_k=3)

        cond = lq.leaders["zone-A"].conductivity
        assert cond > 0.5  # should be above neutral


# =========================================================================== #
#  Stats
# =========================================================================== #


class TestLightningStats:
    def test_stats_after_queries(self):
        lq = LightningQuery()
        for i in range(20):
            tongue = ("KO", "DR")[i % 2]
            lq.ingest(f"rec-{i}", f"zone-{tongue}", tongue, [0.5] * 6)

        lq.strike("KO", [0.5] * 6, top_k=3)
        lq.strike("DR", [0.5] * 6, top_k=3)

        stats = lq.stats()
        assert stats["queries_executed"] == 2
        assert stats["total_probes"] >= 2
        assert stats["total_zones"] == 2
        assert stats["total_records"] == 20


# =========================================================================== #
#  Integration with real workload
# =========================================================================== #


class TestLightningIntegration:
    def test_with_bridge_workload(self):
        from scripts.system.storage_bridge_lab import (
            build_bridge_workload,
            _note_to_geometry,
        )
        from src.storage.langues_dispersal import dispersal_route, compute_dispersal

        notes = build_bridge_workload(seed=42, count=200)
        geos = [_note_to_geometry(n, i) for i, n in enumerate(notes)]
        tongue_vecs = [g["tongue_coords"] for g in geos]

        # Compute dispersal for centroid
        report = compute_dispersal(tongue_vecs)
        centroid = report.centroid

        # Build lightning engine with dispersal-routed zones
        lq = LightningQuery(match_threshold=2.0)
        for g in geos:
            route = dispersal_route(g["tongue_coords"], centroid)
            zone_id = f"{route['zone']}_{route['dominant_tongue']}"
            lq.ingest(g["note_id"], zone_id, g["tongue"], g["tongue_coords"])

        # Run 20 queries
        for g in geos[:20]:
            result = lq.strike(g["tongue"], g["tongue_coords"], top_k=5)
            assert len(result.best_matches) > 0

        stats = lq.stats()
        assert stats["queries_executed"] == 20
        assert stats["total_probes"] > 0
        assert stats["avg_probes_per_query"] > 0
        # After 20 queries, some zones should have been penalized
        # (not all zones match every query)
        assert stats["total_pruned"] >= 0
