"""Graph / manifold projection of the Prime Spacetime Atlas.

A VIEW on top of :mod:`src.geoseed.prime_atlas`. It embeds the multi-coordinate
prime addresses into a low-dimensional space so you can SEE which regions of
number-space cluster — but it holds the same discipline as the rest of the atlas:

  * It projects only FACT / KNOWN_STRUCTURE coordinates by default. A
    FALSIFIED_PROJECTION coordinate is refused unless explicitly opted in (and
    then the projection is flagged), so the picture cannot be quietly built from
    hallucinated geometry.
  * Any cluster / axis the projection appears to show is a HYPOTHESIS until it
    clears `alignment_vs_null` (re-exported here). A pretty embedding is not a
    path.

The honest expectation, stated up front: over a WIDE index range the only strong
axis is SCALE (log value / PNT density); the local coordinates (gaps, ratios) are
the locally-pseudorandom wall and contribute a near-isotropic cloud with no real
clusters. Zoom into a NARROW window and even scale collapses — the projection
becomes featureless. The view is built to make that truth visible, not to hide it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src.geoseed.prime_atlas import (
    COORDINATE_STATUS,
    PrimeAddress,
    alignment_vs_null,  # re-exported: the real-vs-hallucinated test
)

# Linearly meaningful scalar coordinates for a manifold embedding. Excludes
# value/index (identity/position, not structure), residues/graph_signature
# (non-scalar / circular / falsified), and curvature (FALSIFIED_PROJECTION).
DEFAULT_MANIFOLD_FEATURES = (
    "log_value",
    "log_log_value",
    "gap_prev",
    "gap_next",
    "ratio_prev",
    "ratio_next",
    "ap_length",
)


@dataclass(frozen=True)
class ManifoldProjection:
    """A low-dimensional embedding of prime addresses, with honest provenance."""

    features: tuple[str, ...]
    coords: tuple[tuple[float, ...], ...]  # (n_points, n_components)
    explained_variance_ratio: tuple[float, ...]
    loadings: tuple[tuple[float, ...], ...]  # (n_components, n_features)
    contained_falsified: bool

    def axis(self, component: int) -> list[float]:
        """The per-point values along one projected component."""
        return [row[component] for row in self.coords]

    def to_dict(self) -> dict[str, object]:
        return {
            "features": list(self.features),
            "coords": [list(row) for row in self.coords],
            "explained_variance_ratio": list(self.explained_variance_ratio),
            "loadings": [list(row) for row in self.loadings],
            "contained_falsified": self.contained_falsified,
        }


def _validate_features(features: Sequence[str], include_falsified: bool) -> bool:
    unknown = [f for f in features if f not in COORDINATE_STATUS]
    if unknown:
        raise ValueError(f"unknown coordinate(s): {unknown}")
    falsified = [
        f for f in features if COORDINATE_STATUS[f][0] == "FALSIFIED_PROJECTION"
    ]
    if falsified and not include_falsified:
        raise ValueError(
            f"refusing to project FALSIFIED_PROJECTION coordinate(s) {falsified} — "
            "they are proven non-predictive; pass include_falsified=True to override knowingly"
        )
    return bool(falsified)


def project_manifold(
    addresses: Sequence[PrimeAddress],
    n_components: int = 2,
    features: Sequence[str] = DEFAULT_MANIFOLD_FEATURES,
    include_falsified: bool = False,
) -> ManifoldProjection:
    """Standardize the chosen coordinates and embed via PCA (numpy SVD).

    Returns coordinates, the per-component explained-variance ratio, and the
    loadings (so each axis is interpretable — you always know what it means).
    """
    features = tuple(features)
    if n_components < 1 or n_components > len(features):
        raise ValueError("n_components must be in [1, len(features)]")
    if len(addresses) <= n_components:
        raise ValueError("need more points than components")
    contained_falsified = _validate_features(features, include_falsified)

    matrix = np.array(
        [[float(getattr(a, f)) for f in features] for a in addresses], dtype=float
    )
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std == 0.0] = 1.0  # a flat coordinate contributes nothing, not a divide-by-zero
    standardized = (matrix - mean) / std

    _u, singular, vt = np.linalg.svd(standardized, full_matrices=False)
    variance = (singular**2) / (len(addresses) - 1)
    evr = variance / variance.sum()
    coords = standardized @ vt[:n_components].T

    return ManifoldProjection(
        features=features,
        coords=tuple(tuple(float(v) for v in row) for row in coords),
        explained_variance_ratio=tuple(float(v) for v in evr[:n_components]),
        loadings=tuple(tuple(float(v) for v in row) for row in vt[:n_components]),
        contained_falsified=contained_falsified,
    )


def dominant_loading(
    projection: ManifoldProjection, component: int = 0
) -> tuple[str, float]:
    """Which coordinate drives a component most — names what the axis 'is'."""
    row = projection.loadings[component]
    idx = max(range(len(row)), key=lambda i: abs(row[i]))
    return projection.features[idx], row[idx]


def relationship_graph_degrees(
    addresses: Sequence[PrimeAddress], edge: str = "shared_wheel_lane"
) -> dict[str, object]:
    """A lightweight relationship graph over the addresses (the 'graph' view).

    Nodes are primes; edges by `edge`:
      * "shared_wheel_lane" — same value mod 30030 (a real KNOWN_STRUCTURE relation)
      * "shared_ap_difference" — both sit on a prime AP of the same common difference
    Returns degree sequence + connected-component count via union-find. A high-degree
    node is a graph position, NOT a path — alignment_vs_null still decides if it means
    anything.
    """
    n = len(addresses)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    if edge == "shared_wheel_lane":
        key = lambda a: a.wheel_lane  # noqa: E731
    elif edge == "shared_ap_difference":
        key = lambda a: a.ap_difference if a.ap_length >= 3 else None  # noqa: E731
    else:
        raise ValueError("edge must be 'shared_wheel_lane' or 'shared_ap_difference'")

    buckets: dict[object, list[int]] = {}
    for i, address in enumerate(addresses):
        k = key(address)
        if k is None:
            continue
        buckets.setdefault(k, []).append(i)

    degrees = [0] * n
    for members in buckets.values():
        if len(members) < 2:
            continue
        for j in members[1:]:
            union(members[0], j)
        for i in members:
            degrees[i] += len(members) - 1

    components = len({find(i) for i in range(n)})
    return {
        "edge": edge,
        "nodes": n,
        "degrees": degrees,
        "max_degree": max(degrees) if degrees else 0,
        "mean_degree": (sum(degrees) / n) if n else 0.0,
        "connected_components": components,
    }


__all__ = [
    "DEFAULT_MANIFOLD_FEATURES",
    "ManifoldProjection",
    "project_manifold",
    "dominant_loading",
    "relationship_graph_degrees",
    "alignment_vs_null",
]


if __name__ == "__main__":
    from src.geoseed.prime_atlas import build_prime_atlas

    wide = build_prime_atlas(1_000, 4_000)
    proj = project_manifold(wide, n_components=3)
    print("features:", proj.features)
    print("explained variance:", [round(v, 4) for v in proj.explained_variance_ratio])
    for c in range(3):
        name, load = dominant_loading(proj, c)
        print(f"  PC{c + 1} dominated by {name} ({load:+.3f})")
    log_values = [a.log_value for a in wide]
    print("PC1 vs log_value:", alignment_vs_null(proj.axis(0), log_values, seeds=200))
