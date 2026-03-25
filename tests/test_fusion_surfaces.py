"""Tests for Yu-Gi-Oh fusion storage surfaces."""

from __future__ import annotations

import numpy as np
import pytest

from src.storage.fusion_surfaces import CymaticCone, SemiSphereCone, TongueRouter

# =========================================================================== #
#  CymaticCone (Octree + Chladni access control)
# =========================================================================== #


class TestCymaticCone:
    def test_insert_and_retrieve_with_correct_vector(self):
        cone = CymaticCone(max_depth=3)
        content = b"governance audit record"
        tongue_coords = [0.3, 0.1, 0.2, 0.7, 0.1, 0.1]

        cone.insert(
            "rec-001",
            np.array([0.2, 0.1, 0.05]),
            tongue_coords,
            content,
            realm="light_realm",
        )

        recovered = cone.retrieve("rec-001", tongue_coords)
        assert recovered == content

    def test_wrong_vector_returns_noise(self):
        cone = CymaticCone(max_depth=3)
        content = b"secret data"
        correct = [0.3, 0.1, 0.2, 0.7, 0.1, 0.1]
        wrong = [0.9, 0.9, 0.9, 0.1, 0.1, 0.1]

        cone.insert("rec-002", np.array([0.1, 0.1, 0.1]), correct, content)
        noise = cone.retrieve("rec-002", wrong)

        assert noise is not None
        assert noise != content

    def test_spatial_query_returns_realm(self):
        cone = CymaticCone(max_depth=3)
        coord = np.array([0.2, 0.1, 0.05])
        cone.insert("rec-003", coord, [0.3, 0.1, 0.2, 0.7, 0.1, 0.1], b"data")

        result = cone.query_spatial(coord)
        assert result is not None

    def test_stats_compaction(self):
        cone = CymaticCone(max_depth=3)
        for i in range(20):
            x = 0.1 + (i % 5) * 0.1
            y = 0.1 + (i // 5) * 0.1
            cone.insert(
                f"rec-{i}",
                np.array([x, y, 0.05]),
                [0.3, 0.1, 0.2, 0.5, 0.1, 0.1],
                f"data-{i}".encode(),
            )

        stats = cone.stats()
        assert stats["record_count"] == 20
        assert stats["node_explosion"] > 0
        assert stats["compaction_score"] > 0

    def test_missing_record_returns_none(self):
        cone = CymaticCone()
        assert cone.retrieve("nonexistent", [0.1] * 6) is None


# =========================================================================== #
#  SemiSphereCone (Lattice hemisphere + Octree cone)
# =========================================================================== #


class TestSemiSphereCone:
    def test_safe_records_go_to_hemisphere(self):
        ssc = SemiSphereCone(radius_threshold=0.5)
        # Near origin → hemisphere
        zone = ssc.insert(
            "safe-001",
            np.array([0.1, 0.1, 0.05]),
            x=0.1,
            y=0.1,
            phase_rad=0.5,
            tongue="KO",
        )
        assert zone == "hemisphere"

    def test_risky_records_go_to_cone(self):
        ssc = SemiSphereCone(radius_threshold=0.5)
        # Near boundary → cone
        zone = ssc.insert(
            "risky-001",
            np.array([0.6, 0.4, 0.3]),
            x=0.6,
            y=0.4,
            phase_rad=1.0,
            tongue="DR",
        )
        assert zone == "cone"

    def test_mixed_workload_splits_correctly(self):
        ssc = SemiSphereCone(radius_threshold=0.5)

        for i in range(30):
            r = 0.1 + (i / 30) * 0.8  # 0.1 to 0.9
            coord = np.array([r * 0.6, r * 0.5, r * 0.3])
            ssc.insert(
                f"mix-{i}",
                coord,
                x=r * 0.6,
                y=r * 0.5,
                phase_rad=i * 0.2,
                tongue="KO",
            )

        stats = ssc.stats()
        assert stats["hemisphere_count"] > 0
        assert stats["cone_count"] > 0
        assert stats["record_count"] == 30
        assert stats["hemisphere_ratio"] + stats["cone_ratio"] == pytest.approx(1.0, abs=0.01)

    def test_hemisphere_query_returns_results(self):
        ssc = SemiSphereCone(radius_threshold=0.5)
        for i in range(10):
            ssc.insert(
                f"h-{i}",
                np.array([0.1 + i * 0.02, 0.1, 0.05]),
                x=0.1 + i * 0.02,
                y=0.1,
                phase_rad=i * 0.3,
                tongue="AV",
            )

        results = ssc.query_nearest(0.15, 0.1, 0.5, tongue="AV", top_k=3)
        assert len(results) > 0

    def test_stats_show_adaptive_density(self):
        ssc = SemiSphereCone(radius_threshold=0.5)
        for i in range(40):
            r = 0.1 + (i / 40) * 0.8
            coord = np.array([r * 0.7, r * 0.4, r * 0.2])
            ssc.insert(f"ad-{i}", coord, x=r * 0.7, y=r * 0.4, phase_rad=i * 0.15)

        stats = ssc.stats()
        assert stats["total_nodes"] > 0
        assert stats["node_explosion"] > 0


# =========================================================================== #
#  TongueRouter (Sphere pre-filter + Lattice query)
# =========================================================================== #


class TestTongueRouter:
    def test_insert_and_routed_query(self):
        router = TongueRouter()
        for i in range(20):
            tongue = ["KO", "AV", "RU", "CA", "UM", "DR"][i % 6]
            router.insert(
                f"tr-{i}",
                x=0.1 * (i % 5),
                y=0.1 * (i // 5),
                phase_rad=i * 0.3,
                tongue=tongue,
                tongue_coords=[0.1 * (j == (i % 6)) for j in range(6)] + [0.0] * 0,
                intent_vector=[0.5, 0.3, 0.2],
            )

        results = router.query_routed(0.1, 0.1, 0.5, [0.5, 0.3, 0.2])
        assert len(results) > 0

    def test_route_tongue_returns_valid_tongue(self):
        router = TongueRouter()
        for i in range(12):
            tongue = ["KO", "AV", "RU", "CA", "UM", "DR"][i % 6]
            tc = [0.0] * 6
            tc[i % 6] = 0.8
            router.insert(
                f"rt-{i}",
                x=0.1 * i,
                y=0.1,
                phase_rad=i * 0.5,
                tongue=tongue,
                tongue_coords=tc,
                intent_vector=[0.5, 0.5, 0.5],
            )

        dominant = router.route_tongue(0.0, bandwidth=0.5)
        assert dominant in ("KO", "AV", "RU", "CA", "UM", "DR")

    def test_stats_include_both_surfaces(self):
        router = TongueRouter()
        for i in range(10):
            router.insert(
                f"st-{i}",
                x=0.1 * i,
                y=0.1,
                phase_rad=i * 0.3,
                tongue="KO",
                tongue_coords=[0.5, 0.1, 0.1, 0.1, 0.1, 0.1],
                intent_vector=[0.5, 0.3, 0.2],
            )

        stats = router.stats()
        assert stats["record_count"] == 10
        assert stats["lattice_nodes"] > 0
        assert stats["sphere_points"] > 0
        assert stats["tongue_evenness"] >= 0
