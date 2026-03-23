from __future__ import annotations

import numpy as np

from src.crypto.octree import HyperbolicOctree


def test_hyperbolic_octree_stats_capture_sparse_allocation() -> None:
    octree = HyperbolicOctree(grid_size=32, max_depth=4)
    octree.insert(np.array([0.10, 0.05, 0.00]), "light_realm")
    octree.insert(np.array([0.55, -0.15, 0.20]), "shadow_realm")
    octree.insert(np.array([-0.45, 0.40, -0.10]), "path")

    stats = octree.stats()

    assert stats["grid_size"] == 32
    assert stats["max_depth"] == 4
    assert stats["point_count"] == 3
    assert stats["occupied_voxels"] >= 1
    assert stats["spectral_voxels"] >= 1
    assert stats["node_count"] >= stats["leaf_count"] >= 1
    assert 0 <= stats["max_depth_used"] <= 4
    assert 0.0 < stats["occupancy_ratio"] < 1.0


def test_hyperbolic_octree_deeper_depth_increases_resolution_surface() -> None:
    shallow = HyperbolicOctree(grid_size=32, max_depth=2)
    deep = HyperbolicOctree(grid_size=32, max_depth=5)
    point = np.array([0.42, -0.18, 0.11])

    shallow.insert(point, "light_realm")
    deep.insert(point, "light_realm")

    shallow_stats = shallow.stats()
    deep_stats = deep.stats()

    assert shallow_stats["point_count"] == deep_stats["point_count"] == 1
    assert deep_stats["max_depth_used"] >= shallow_stats["max_depth_used"]
    assert deep_stats["node_count"] >= shallow_stats["node_count"]
