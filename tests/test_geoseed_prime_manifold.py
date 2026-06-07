from __future__ import annotations

import pytest

from src.geoseed.prime_atlas import build_prime_atlas
from src.geoseed.prime_manifold import (
    DEFAULT_MANIFOLD_FEATURES,
    ManifoldProjection,
    alignment_vs_null,
    dominant_loading,
    project_manifold,
    relationship_graph_degrees,
)

_WIDE = build_prime_atlas(1_000, 4_000)  # spans scales
_NARROW = build_prime_atlas(100_000, 300)  # one scale band


def test_projection_shape_and_provenance() -> None:
    proj = project_manifold(_WIDE, n_components=3)
    assert isinstance(proj, ManifoldProjection)
    assert len(proj.coords) == len(_WIDE)
    assert all(len(row) == 3 for row in proj.coords)
    assert len(proj.explained_variance_ratio) == 3
    assert all(0.0 <= v <= 1.0 for v in proj.explained_variance_ratio)
    # descending variance
    assert list(proj.explained_variance_ratio) == sorted(
        proj.explained_variance_ratio, reverse=True
    )
    assert proj.contained_falsified is False
    name, _load = dominant_loading(proj, 0)
    assert name in DEFAULT_MANIFOLD_FEATURES


def test_wide_range_pc1_is_real_scale_axis() -> None:
    # Across scales, the one real axis is scale; PC1 must track log_value over its null.
    proj = project_manifold(_WIDE, n_components=2)
    log_values = [a.log_value for a in _WIDE]
    result = alignment_vs_null(proj.axis(0), log_values, seeds=200)
    assert result["beats_null"]
    assert result["real"] > 0.8


def test_narrow_window_collapses_to_the_wall() -> None:
    # Zoomed into one scale band, PC1 no longer means scale — it is the featureless
    # local cloud (the wall). PC1 vs log_value falls to the noise floor.
    proj = project_manifold(_NARROW, n_components=2)
    log_values = [a.log_value for a in _NARROW]
    result = alignment_vs_null(proj.axis(0), log_values, seeds=200)
    assert result["real"] < 0.2  # not a real scale axis anymore


def test_falsified_coordinate_is_refused_by_default() -> None:
    with pytest.raises(ValueError, match="FALSIFIED_PROJECTION"):
        project_manifold(_WIDE, features=("log_value", "curvature"))
    proj = project_manifold(
        _WIDE,
        n_components=1,
        features=("log_value", "curvature"),
        include_falsified=True,
    )
    assert proj.contained_falsified is True


def test_unknown_feature_rejected() -> None:
    with pytest.raises(ValueError, match="unknown coordinate"):
        project_manifold(_WIDE, features=("log_value", "not_a_coordinate"))


def test_graph_wheel_lane_is_sparse_ap_difference_clusters() -> None:
    lane = relationship_graph_degrees(_WIDE, "shared_wheel_lane")
    assert lane["nodes"] == len(_WIDE)
    assert len(lane["degrees"]) == len(_WIDE)
    assert lane["connected_components"] > 0.8 * lane["nodes"]  # nearly all isolated
    assert lane["max_degree"] <= 5

    apd = relationship_graph_degrees(_WIDE, "shared_ap_difference")
    assert apd["max_degree"] > 50  # known small even differences bucket many primes
    assert apd["connected_components"] < lane["connected_components"]


def test_graph_rejects_unknown_edge() -> None:
    with pytest.raises(ValueError, match="edge must be"):
        relationship_graph_degrees(_WIDE, "telepathy")
