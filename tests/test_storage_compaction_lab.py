from __future__ import annotations

from scripts.system.storage_compaction_lab import (
    build_lattice_workload,
    build_octree_workload,
    evaluate_hyperbolic_octree,
    evaluate_lattice25d,
    sweep_storage_knob,
)


def test_octree_workload_is_deterministic() -> None:
    first = build_octree_workload(seed=19)
    second = build_octree_workload(seed=19)

    assert first == second
    assert len(first) == 88


def test_lattice_workload_is_deterministic() -> None:
    first = build_lattice_workload(seed=23, cluster_count=3, bundles_per_cluster=10)
    second = build_lattice_workload(seed=23, cluster_count=3, bundles_per_cluster=10)

    assert first == second
    assert len(first) == 30


def test_evaluate_hyperbolic_octree_returns_compaction_metrics() -> None:
    report = evaluate_hyperbolic_octree(max_depth=4, grid_size=32, seed=7)

    assert report["point_count"] > 0
    assert report["occupied_voxels"] > 0
    assert report["storage_units"] >= report["node_count"]
    assert report["points_per_occupied_voxel"] > 0
    assert report["compaction_score"] > 0


def test_evaluate_lattice25d_returns_hybrid_metrics() -> None:
    report = evaluate_lattice25d(
        cell_size=0.4,
        max_depth=4,
        index_mode="hybrid",
        quadtree_capacity=2,
        quadtree_z_variance=0.0,
        seed=11,
    )

    assert report["bundle_count"] > 0
    assert report["occupied_cells"] > 0
    assert report["octree_voxel_count"] == report["bundle_count"]
    assert report["index_mode"] == "hybrid"
    assert report["bundles_per_cell"] > 0
    assert report["storage_units"] > report["occupied_cells"]
    assert report["compaction_score"] > 0
    assert report["quadtree"]["node_count"] >= report["quadtree"]["leaf_count"] >= 1


def test_sweep_storage_knob_ranks_cards() -> None:
    report = sweep_storage_knob(
        system="hyperbolic-octree",
        knob="max_depth",
        values=[3, 5],
        seed=5,
    )

    assert report["best_card"] is not None
    assert len(report["cards"]) == 2
    assert report["cards"][0]["rank"] == 1
    assert report["cards"][0]["system"] == "hyperbolic-octree"
    assert report["cards"][0]["verdict"] == "best-current-tradeoff"
