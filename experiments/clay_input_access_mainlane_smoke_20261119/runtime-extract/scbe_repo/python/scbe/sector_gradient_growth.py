"""Bounded sector-node growth and packed gradients for radial token images.

This module is a derived visual surface over :mod:`algebraic_radial_token_table`.
It never changes token identity, table coordinates, relay weights, or governance.
Opcode bytes are projected through the existing trichromatic board, packed into
piecewise gradients, and subdivided only when a radial split lowers measured RGB
reconstruction error.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Sequence

from PIL import Image

from python.scbe.algebraic_radial_token_table import (
    AlgebraicCell,
    AlgebraicRadialTokenTable,
    TAU,
)
from python.scbe.board import rgb as opcode_rgb

RGB = tuple[int, int, int]
MAX_GRADIENT_STOPS = 256


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _validate_rgb(color: Sequence[int]) -> RGB:
    if len(color) != 3 or any(isinstance(channel, bool) or not isinstance(channel, int) for channel in color):
        raise ValueError("RGB colors must contain exactly three integer channels")
    if any(channel < 0 or channel > 255 for channel in color):
        raise ValueError("RGB channels must be in [0, 255]")
    return int(color[0]), int(color[1]), int(color[2])


def _lerp_color(left: RGB, right: RGB, amount: float) -> RGB:
    bounded = max(0.0, min(1.0, amount))
    return tuple(round(a + (b - a) * bounded) for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class GradientStop:
    position: float
    color: RGB


@dataclass(frozen=True, slots=True)
class SectorGradientNode:
    node_id: str
    parent_id: str | None
    child_ids: tuple[str, ...]
    sector: int
    depth: int
    ordinal_start: int
    ordinal_end: int
    radius_start: float
    radius_end: float
    sample_cell_ids: tuple[int, ...]
    gradient_stops: tuple[GradientStop, ...]
    sample_count: int
    flat_mse: float
    gradient_mse: float


@dataclass(frozen=True, slots=True)
class SectorGradientMetrics:
    root_count: int
    node_count: int
    leaf_count: int
    grown_node_count: int
    max_observed_depth: int
    flat_mse: float
    fixed_gradient_mse: float
    adaptive_gradient_mse: float
    packed_stop_count: int


class SectorGradientMesh:
    """An immutable adaptive visual mesh over a radial token table."""

    def __init__(
        self,
        *,
        table: AlgebraicRadialTokenTable,
        colors: Sequence[RGB],
        source_bytes: bytes,
        nodes: Sequence[SectorGradientNode],
        root_ids: Sequence[str],
        config: dict[str, int | float],
    ) -> None:
        self.table = table
        self.colors = tuple(colors)
        self.source_bytes = bytes(source_bytes)
        self.nodes = tuple(nodes)
        self.root_ids = tuple(root_ids)
        self.config = dict(config)
        self._by_id = {node.node_id: node for node in self.nodes}
        self._validate_mesh()
        self.metrics = self._metrics()

    @property
    def leaves(self) -> tuple[SectorGradientNode, ...]:
        return tuple(node for node in self.nodes if not node.child_ids)

    def color_at(self, node: SectorGradientNode, radius: float) -> RGB:
        """Interpolate a packed node gradient at an absolute radial position."""

        stops = node.gradient_stops
        if len(stops) == 1 or radius <= stops[0].position:
            return stops[0].color
        if radius >= stops[-1].position:
            return stops[-1].color
        for left, right in zip(stops, stops[1:], strict=True):
            if left.position <= radius <= right.position:
                span = right.position - left.position
                amount = 0.0 if span == 0.0 else (radius - left.position) / span
                return _lerp_color(left.color, right.color, amount)
        return stops[-1].color

    def render(self, *, size: int = 256, background: RGB = (0, 0, 0)) -> Image.Image:
        """Rasterize the sector polygons with pixel-level gradient interpolation."""

        if size < 8 or size > 4096:
            raise ValueError("image size must be in [8, 4096]")
        background = _validate_rgb(background)
        sector_width = TAU / self.table.spec.sector_count
        leaves_by_sector: dict[int, list[SectorGradientNode]] = {
            sector: [] for sector in range(self.table.spec.sector_count)
        }
        for node in self.leaves:
            leaves_by_sector[node.sector].append(node)
        for sector_nodes in leaves_by_sector.values():
            sector_nodes.sort(key=lambda node: node.radius_start)

        pixels: list[RGB] = []
        center = (size - 1) / 2.0
        scale = max(center, 1.0)
        for y in range(size):
            dy = (center - y) / scale
            for x in range(size):
                dx = (x - center) / scale
                radius = math.hypot(dx, dy)
                if radius > 1.0:
                    pixels.append(background)
                    continue
                angle = math.atan2(dy, dx) % TAU
                sector = min(self.table.spec.sector_count - 1, int(angle / sector_width))
                selected = leaves_by_sector[sector][-1]
                for candidate in leaves_by_sector[sector]:
                    if candidate.radius_start <= radius <= candidate.radius_end:
                        selected = candidate
                        break
                pixels.append(self.color_at(selected, radius))

        image = Image.new("RGB", (size, size))
        image.putdata(pixels)
        return image

    def save_png(self, path: str | Path, *, size: int = 256, background: RGB = (0, 0, 0)) -> str:
        """Write a deterministic PNG and return its SHA-256 digest."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.render(size=size, background=background).save(target, format="PNG", optimize=False, compress_level=9)
        return sha256(target.read_bytes()).hexdigest()

    def receipt(self) -> dict[str, object]:
        core: dict[str, object] = {
            "schema": "scbe.sector-gradient-growth.v1",
            "claim_boundary": "derived visual mechanics only; no model-quality, independence, or speed claim",
            "source_opcode_sha256": sha256(self.source_bytes).hexdigest(),
            "table_receipt_sha256": self.table.receipt()["receipt_sha256"],
            "config": self.config,
            "root_ids": list(self.root_ids),
            "nodes": [asdict(node) for node in self.nodes],
            "metrics": asdict(self.metrics),
        }
        return {**core, "receipt_sha256": sha256(_canonical_json(core)).hexdigest()}

    def _metrics(self) -> SectorGradientMetrics:
        roots = [self._by_id[node_id] for node_id in self.root_ids]
        leaves = list(self.leaves)

        def weighted_mse(rows: Sequence[SectorGradientNode], field: str) -> float:
            samples = sum(node.sample_count for node in rows)
            if samples == 0:
                return 0.0
            return math.fsum(getattr(node, field) * node.sample_count for node in rows) / samples

        base_stop_budget = int(self.config["max_gradient_stops"])
        table_cells = {cell.cell_id: cell for cell in self.table.base_cells}

        def refit_root_mse(node: SectorGradientNode) -> tuple[float, float]:
            samples = tuple((table_cells[cell_id], self.colors[cell_id]) for cell_id in node.sample_cell_ids)
            _, flat_mse, gradient_mse = _fit_stops(samples, base_stop_budget)
            return flat_mse, gradient_mse

        root_fits = tuple(refit_root_mse(node) for node in roots)
        root_samples = sum(node.sample_count for node in roots)
        flat_mse = (
            math.fsum(value[0] * node.sample_count for node, value in zip(roots, root_fits, strict=True)) / root_samples
            if root_samples
            else 0.0
        )
        fixed_gradient_mse = (
            math.fsum(value[1] * node.sample_count for node, value in zip(roots, root_fits, strict=True)) / root_samples
            if root_samples
            else 0.0
        )

        return SectorGradientMetrics(
            root_count=len(roots),
            node_count=len(self.nodes),
            leaf_count=len(leaves),
            grown_node_count=sum(bool(node.child_ids) for node in self.nodes),
            max_observed_depth=max(node.depth for node in self.nodes),
            flat_mse=flat_mse,
            fixed_gradient_mse=fixed_gradient_mse,
            adaptive_gradient_mse=weighted_mse(leaves, "gradient_mse"),
            packed_stop_count=sum(len(node.gradient_stops) for node in leaves),
        )

    def _validate_mesh(self) -> None:
        if len(self._by_id) != len(self.nodes):
            raise ValueError("visual node IDs must be unique")
        if len(self.colors) != self.table.spec.cell_count:
            raise ValueError("one color is required per table cell")
        expected = set(range(self.table.spec.cell_count))
        covered = [cell_id for node in self.leaves for cell_id in node.sample_cell_ids]
        if len(covered) != len(set(covered)) or set(covered) != expected:
            raise ValueError("leaf nodes must cover every cell exactly once")
        max_depth = int(self.config["max_depth"])
        if any(node.depth > max_depth for node in self.nodes):
            raise ValueError("visual node depth exceeds the configured bound")
        for node in self.nodes:
            if not 0.0 <= node.radius_start < node.radius_end <= 1.0:
                raise ValueError("visual node radius bounds must partition [0, 1]")
            if node.child_ids and any(child_id not in self._by_id for child_id in node.child_ids):
                raise ValueError("visual node references a missing child")
            if not node.gradient_stops:
                raise ValueError("every visual node needs at least one gradient stop")
            if any(not math.isfinite(stop.position) for stop in node.gradient_stops):
                raise ValueError("gradient stop positions must be finite")
            if tuple(sorted(stop.position for stop in node.gradient_stops)) != tuple(
                stop.position for stop in node.gradient_stops
            ):
                raise ValueError("gradient stops must be ordered")


def _packed_stops(samples: Sequence[tuple[AlgebraicCell, RGB]], max_stops: int) -> tuple[GradientStop, ...]:
    stop_count = min(max_stops, len(samples))
    if stop_count == 1:
        cell, color = samples[0]
        return (GradientStop(cell.radius, color),)
    indices = [round(step * (len(samples) - 1) / (stop_count - 1)) for step in range(stop_count)]
    unique_indices = tuple(dict.fromkeys(indices))
    return tuple(GradientStop(samples[index][0].radius, samples[index][1]) for index in unique_indices)


def _predict(stops: Sequence[GradientStop], radius: float) -> RGB:
    if len(stops) == 1 or radius <= stops[0].position:
        return stops[0].color
    if radius >= stops[-1].position:
        return stops[-1].color
    for left, right in zip(stops, stops[1:], strict=True):
        if left.position <= radius <= right.position:
            span = right.position - left.position
            return _lerp_color(
                left.color,
                right.color,
                0.0 if span == 0.0 else (radius - left.position) / span,
            )
    return stops[-1].color


def _errors(samples: Sequence[tuple[AlgebraicCell, RGB]], stops: Sequence[GradientStop]) -> tuple[float, float]:
    means = tuple(round(math.fsum(color[channel] for _, color in samples) / len(samples)) for channel in range(3))
    flat_squared = 0.0
    gradient_squared = 0.0
    for cell, color in samples:
        predicted = _predict(stops, cell.radius)
        flat_squared += math.fsum((color[channel] - means[channel]) ** 2 for channel in range(3))
        gradient_squared += math.fsum((color[channel] - predicted[channel]) ** 2 for channel in range(3))
    divisor = len(samples) * 3
    return flat_squared / divisor, gradient_squared / divisor


def _fit_stops(
    samples: Sequence[tuple[AlgebraicCell, RGB]], max_stops: int
) -> tuple[tuple[GradientStop, ...], float, float]:
    """Fit packed stops, retaining the flat packed baseline when it is better."""

    stops = _packed_stops(samples, max_stops)
    flat_mse, gradient_mse = _errors(samples, stops)
    if gradient_mse <= flat_mse:
        return stops, flat_mse, gradient_mse
    mean_color = tuple(round(math.fsum(color[channel] for _, color in samples) / len(samples)) for channel in range(3))
    flat_stop = (GradientStop((samples[0][0].radius + samples[-1][0].radius) / 2.0, mean_color),)
    _, packed_flat_mse = _errors(samples, flat_stop)
    return flat_stop, flat_mse, packed_flat_mse


def build_sector_gradient_mesh(
    table: AlgebraicRadialTokenTable,
    opcode_bytes: Sequence[int],
    *,
    max_depth: int = 3,
    max_gradient_stops: int = 3,
    leaf_gradient_stops: int | None = None,
    split_error_threshold: float = 64.0,
    min_samples_to_split: int = 4,
) -> SectorGradientMesh:
    """Pack opcode colors and grow error-reducing radial sector nodes."""

    if len(opcode_bytes) != table.spec.cell_count:
        raise ValueError("opcode byte count must match table cell_count")
    if any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255 for value in opcode_bytes):
        raise ValueError("opcode bytes must be integers in [0, 255]")
    if max_depth < 0 or max_depth > 12:
        raise ValueError("max_depth must be in [0, 12]")
    if max_gradient_stops < 1 or max_gradient_stops > MAX_GRADIENT_STOPS:
        raise ValueError(f"max_gradient_stops must be in [1, {MAX_GRADIENT_STOPS}]")
    resolved_leaf_stops = max_gradient_stops if leaf_gradient_stops is None else leaf_gradient_stops
    if resolved_leaf_stops < max_gradient_stops or resolved_leaf_stops > MAX_GRADIENT_STOPS:
        raise ValueError(
            f"leaf_gradient_stops must be in [max_gradient_stops, {MAX_GRADIENT_STOPS}]"
        )
    if min_samples_to_split < 2:
        raise ValueError("min_samples_to_split must be at least two")
    if not math.isfinite(split_error_threshold) or split_error_threshold < 0:
        raise ValueError("split_error_threshold must be finite and non-negative")

    colors = tuple(opcode_rgb(value) for value in opcode_bytes)
    by_sector: dict[int, list[tuple[AlgebraicCell, RGB]]] = {sector: [] for sector in range(table.spec.sector_count)}
    for cell in table.base_cells:
        by_sector[cell.sector].append((cell, colors[cell.cell_id]))
    for samples in by_sector.values():
        samples.sort(key=lambda item: item[0].ordinal)

    nodes: list[SectorGradientNode] = []
    root_ids: list[str] = []

    def grow(
        samples: Sequence[tuple[AlgebraicCell, RGB]],
        *,
        sector: int,
        depth: int,
        path: str,
        parent_id: str | None,
        radius_start: float,
        radius_end: float,
    ) -> str:
        node_id = f"sector:{sector}:node:{path}"
        stops, flat_mse, gradient_mse = _fit_stops(samples, max_gradient_stops)
        child_specs: list[tuple[Sequence[tuple[AlgebraicCell, RGB]], float, float, str]] = []

        if depth < max_depth and len(samples) >= min_samples_to_split:
            midpoint = len(samples) // 2
            left = samples[:midpoint]
            right = samples[midpoint:]
            boundary = (left[-1][0].radius + right[0][0].radius) / 2.0
            left_error = _fit_stops(left, max_gradient_stops)[2]
            right_error = _fit_stops(right, max_gradient_stops)[2]
            child_error = (left_error * len(left) + right_error * len(right)) / len(samples)
            if gradient_mse > split_error_threshold and child_error + 1e-12 < gradient_mse:
                child_specs = [
                    (left, radius_start, boundary, f"{path}0"),
                    (right, boundary, radius_end, f"{path}1"),
                ]

        if not child_specs and resolved_leaf_stops > max_gradient_stops:
            stops, flat_mse, gradient_mse = _fit_stops(samples, resolved_leaf_stops)

        node_index = len(nodes)
        nodes.append(
            SectorGradientNode(
                node_id=node_id,
                parent_id=parent_id,
                child_ids=(),
                sector=sector,
                depth=depth,
                ordinal_start=samples[0][0].ordinal,
                ordinal_end=samples[-1][0].ordinal,
                radius_start=radius_start,
                radius_end=radius_end,
                sample_cell_ids=tuple(cell.cell_id for cell, _ in samples),
                gradient_stops=stops,
                sample_count=len(samples),
                flat_mse=flat_mse,
                gradient_mse=gradient_mse,
            )
        )
        child_ids = tuple(
            grow(
                child_samples,
                sector=sector,
                depth=depth + 1,
                path=child_path,
                parent_id=node_id,
                radius_start=child_start,
                radius_end=child_end,
            )
            for child_samples, child_start, child_end, child_path in child_specs
        )
        if child_ids:
            nodes[node_index] = SectorGradientNode(
                **{
                    **asdict(nodes[node_index]),
                    "child_ids": child_ids,
                    "gradient_stops": stops,
                }
            )
        return node_id

    for sector in range(table.spec.sector_count):
        root_ids.append(
            grow(
                by_sector[sector],
                sector=sector,
                depth=0,
                path="r",
                parent_id=None,
                radius_start=0.0,
                radius_end=1.0,
            )
        )

    return SectorGradientMesh(
        table=table,
        colors=colors,
        source_bytes=bytes(opcode_bytes),
        nodes=nodes,
        root_ids=root_ids,
        config={
            "max_depth": max_depth,
            "max_gradient_stops": max_gradient_stops,
            "leaf_gradient_stops": resolved_leaf_stops,
            "split_error_threshold": split_error_threshold,
            "min_samples_to_split": min_samples_to_split,
        },
    )


__all__ = [
    "GradientStop",
    "MAX_GRADIENT_STOPS",
    "SectorGradientMesh",
    "SectorGradientMetrics",
    "SectorGradientNode",
    "build_sector_gradient_mesh",
]
