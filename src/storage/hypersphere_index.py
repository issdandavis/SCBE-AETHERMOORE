"""Experimental hypersphere index for tongue-aware retrieval.

The index maps 6D tongue vectors into concentric Poincare-ball layers.
It is intentionally standalone so we can benchmark safely before integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _normalize_to_ball(vector: list[float], max_radius: float) -> list[float]:
    if not vector:
        raise ValueError("Vector cannot be empty.")
    norm = _vector_norm(vector)
    if norm == 0.0:
        return [0.0 for _ in vector]
    if norm < max_radius:
        return list(vector)
    scale = max_radius / norm
    return [component * scale for component in vector]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    denom = _vector_norm(a) * _vector_norm(b)
    if denom == 0.0:
        return 0.0
    return _dot(a, b) / denom


def poincare_distance(a: list[float], b: list[float], epsilon: float = 1e-9) -> float:
    """Hyperbolic distance in the Poincare ball."""

    norm_a_sq = _dot(a, a)
    norm_b_sq = _dot(b, b)
    diff_sq = _dot([x - y for x, y in zip(a, b)], [x - y for x, y in zip(a, b)])
    denom = max((1.0 - norm_a_sq) * (1.0 - norm_b_sq), epsilon)
    arg = 1.0 + (2.0 * diff_sq / denom)
    if arg < 1.0:
        arg = 1.0
    return math.acosh(arg)


@dataclass(frozen=True)
class HyperSphereRecord:
    doc_id: str
    text: str
    vector: list[float]
    layer: int
    radius: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HyperSphereSearchHit:
    doc_id: str
    score: float
    layer: int
    radius: float
    hyperbolic_distance: float
    cosine_similarity: float
    text: str
    metadata: dict[str, Any]


class HyperSphereIndex:
    """Concentric-layer index over vectors in a Poincare ball."""

    def __init__(self, *, dimensions: int = 6, layer_count: int = 8, max_radius: float = 0.95) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be > 0")
        if layer_count <= 1:
            raise ValueError("layer_count must be > 1")
        if not (0.0 < max_radius < 1.0):
            raise ValueError("max_radius must be in (0, 1)")
        self.dimensions = dimensions
        self.layer_count = layer_count
        self.max_radius = max_radius
        self._records: list[HyperSphereRecord] = []
        self._layers: dict[int, list[HyperSphereRecord]] = {i: [] for i in range(layer_count)}

    def _layer_for_radius(self, radius: float) -> int:
        if radius <= 0.0:
            return 0
        slot = int((radius / self.max_radius) * self.layer_count)
        return int(_clamp(slot, 0, self.layer_count - 1))

    def add(self, *, doc_id: str, text: str, vector: list[float], metadata: dict[str, Any] | None = None) -> None:
        if len(vector) != self.dimensions:
            raise ValueError(f"Expected {self.dimensions}D vector, got {len(vector)}D")
        normalized = _normalize_to_ball(vector, self.max_radius)
        radius = _vector_norm(normalized)
        layer = self._layer_for_radius(radius)
        record = HyperSphereRecord(
            doc_id=doc_id,
            text=text,
            vector=normalized,
            layer=layer,
            radius=radius,
            metadata=dict(metadata or {}),
        )
        self._records.append(record)
        self._layers[layer].append(record)

    @property
    def size(self) -> int:
        return len(self._records)

    def layer_sizes(self) -> dict[int, int]:
        return {layer: len(items) for layer, items in self._layers.items()}

    def search(
        self,
        *,
        query_vector: list[float],
        top_k: int = 10,
        layer_window: int = 1,
        candidate_cap: int = 2000,
    ) -> list[HyperSphereSearchHit]:
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Expected {self.dimensions}D query vector, got {len(query_vector)}D")
        if top_k <= 0:
            return []
        if self.size == 0:
            return []

        query = _normalize_to_ball(query_vector, self.max_radius)
        query_radius = _vector_norm(query)
        query_layer = self._layer_for_radius(query_radius)
        layer_window = max(0, layer_window)

        selected_layers = range(
            max(0, query_layer - layer_window),
            min(self.layer_count, query_layer + layer_window + 1),
        )
        candidates: list[HyperSphereRecord] = []
        for layer in selected_layers:
            candidates.extend(self._layers[layer])

        if not candidates:
            candidates = list(self._records)
        if len(candidates) > candidate_cap:
            candidates = candidates[:candidate_cap]

        hits: list[HyperSphereSearchHit] = []
        for record in candidates:
            h_dist = poincare_distance(query, record.vector)
            cosine = _cosine_similarity(query, record.vector)
            layer_gap = abs(record.layer - query_layer)
            # Lower hyperbolic distance and stronger directional alignment score higher.
            score = (1.0 / (1.0 + h_dist)) + (0.45 * cosine) - (0.03 * layer_gap)
            hits.append(
                HyperSphereSearchHit(
                    doc_id=record.doc_id,
                    score=score,
                    layer=record.layer,
                    radius=record.radius,
                    hyperbolic_distance=h_dist,
                    cosine_similarity=cosine,
                    text=record.text,
                    metadata=record.metadata,
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]
