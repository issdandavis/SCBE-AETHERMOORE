from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


Point = tuple[float, float]


@dataclass(frozen=True)
class SemanticFeature:
    name: str
    weight: float
    octave_level: int
    sides: int


@dataclass(frozen=True)
class PackedCell:
    feature: SemanticFeature
    radius: float
    center: Point
    rotation: float


@dataclass(frozen=True)
class SemanticTokenShape:
    token: str
    outer_sides: int
    outer_radius: float
    cells: tuple[PackedCell, ...]


@dataclass(frozen=True)
class PackingReport:
    token: str
    outer_hull_area: float
    inner_area: float
    utilization: float
    collision_count: int
    boundary_violation_count: int
    octave_link_count: int
    phase_link_count: int
    fit_score: float
    semantic_loss: float


@dataclass(frozen=True)
class BenchmarkReport:
    source: dict[str, str]
    passed: bool
    generated_shapes: list[dict[str, object]]
    reports: list[dict[str, object]]
    baseline_reports: list[dict[str, object]]
    aggregate: dict[str, float]


DEFAULT_FEATURES: dict[str, list[SemanticFeature]] = {
    "CALLABLE": [
        SemanticFeature("syntax_role", 0.90, 0, 6),
        SemanticFeature("argument_shape", 0.80, 1, 5),
        SemanticFeature("side_effects", 0.55, 2, 3),
        SemanticFeature("resource_cost", 0.70, 3, 4),
        SemanticFeature("test_surface", 0.65, 1, 6),
        SemanticFeature("failure_mode", 0.60, 2, 5),
    ],
    "CONTROL_FLOW": [
        SemanticFeature("branch", 0.85, 0, 3),
        SemanticFeature("loop", 0.75, 1, 4),
        SemanticFeature("guard", 0.80, 1, 5),
        SemanticFeature("exit", 0.60, 2, 3),
        SemanticFeature("phase", 0.55, 3, 6),
        SemanticFeature("risk", 0.70, 2, 5),
    ],
    "DATA_SYMBOL": [
        SemanticFeature("type", 0.90, 0, 4),
        SemanticFeature("scope", 0.65, 1, 5),
        SemanticFeature("lineage", 0.70, 2, 6),
        SemanticFeature("codec", 0.55, 3, 4),
        SemanticFeature("entropy", 0.60, 1, 3),
    ],
    "GOVERNANCE_GATE": [
        SemanticFeature("policy", 0.95, 0, 6),
        SemanticFeature("decision", 0.90, 1, 4),
        SemanticFeature("audit", 0.75, 2, 5),
        SemanticFeature("replay", 0.70, 2, 3),
        SemanticFeature("fallback", 0.65, 3, 6),
        SemanticFeature("escalation", 0.80, 1, 5),
    ],
}


def regular_polygon_vertices(
    sides: int,
    radius: float,
    center: Point = (0.0, 0.0),
    rotation: float = 0.0,
) -> list[Point]:
    if sides < 3:
        raise ValueError("regular polygon needs at least 3 sides")
    if radius <= 0:
        raise ValueError("radius must be positive")
    return [
        (
            center[0] + radius * math.cos(rotation + 2.0 * math.pi * index / sides),
            center[1] + radius * math.sin(rotation + 2.0 * math.pi * index / sides),
        )
        for index in range(sides)
    ]


def polygon_area(vertices: Sequence[Point]) -> float:
    area = 0.0
    for index, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(index + 1) % len(vertices)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def edge_normals(vertices: Sequence[Point]) -> list[Point]:
    normals: list[Point] = []
    for index, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(index + 1) % len(vertices)]
        edge_x = x2 - x1
        edge_y = y2 - y1
        length = math.hypot(edge_x, edge_y)
        if length == 0:
            continue
        normals.append((-edge_y / length, edge_x / length))
    return normals


def project(vertices: Sequence[Point], axis: Point) -> tuple[float, float]:
    values = [x * axis[0] + y * axis[1] for x, y in vertices]
    return min(values), max(values)


def intervals_overlap(left: tuple[float, float], right: tuple[float, float], clearance: float = 0.0) -> bool:
    return left[0] <= right[1] + clearance and right[0] <= left[1] + clearance


def sat_overlap(left: Sequence[Point], right: Sequence[Point], clearance: float = 0.0) -> bool:
    for axis in edge_normals(left) + edge_normals(right):
        if not intervals_overlap(project(left, axis), project(right, axis), clearance):
            return False
    return True


def point_inside_convex_polygon(point: Point, polygon: Sequence[Point], epsilon: float = 1e-9) -> bool:
    sign = None
    for index, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(index + 1) % len(polygon)]
        cross = (x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)
        if abs(cross) <= epsilon:
            continue
        current = cross > 0
        if sign is None:
            sign = current
        elif sign != current:
            return False
    return True


def polygon_inside_convex_polygon(inner: Sequence[Point], outer: Sequence[Point]) -> bool:
    return all(point_inside_convex_polygon(point, outer) for point in inner)


def distance(left: Point, right: Point) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


def cell_vertices(cell: PackedCell) -> list[Point]:
    return regular_polygon_vertices(cell.feature.sides, cell.radius, cell.center, cell.rotation)


def feature_radius(feature: SemanticFeature, base_radius: float = 0.18) -> float:
    return base_radius * (0.72 + 0.42 * feature.weight) / (2 ** (feature.octave_level / 2.0))


def fit_score(shape: SemanticTokenShape) -> float:
    report = evaluate_shape(shape)
    if report.semantic_loss == 0.0:
        return report.fit_score + 10.0
    return report.fit_score - 10.0 * report.semantic_loss


def deterministic_candidate(
    token: str,
    outer_sides: int,
    features: Sequence[SemanticFeature],
    attempt: int,
    rng: random.Random,
) -> SemanticTokenShape:
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    cells: list[PackedCell] = []
    for index, feature in enumerate(features):
        shell_base = [0.08, 0.38, 0.54, 0.70][feature.octave_level]
        shell = shell_base + 0.008 * (attempt % 5)
        phase = index * golden_angle + attempt * 0.239 + rng.uniform(-0.055, 0.055)
        radius = feature_radius(feature)
        cells.append(
            PackedCell(
                feature=feature,
                radius=radius,
                center=(shell * math.cos(phase), shell * math.sin(phase)),
                rotation=phase / 2.0,
            )
        )
    return SemanticTokenShape(token=token, outer_sides=outer_sides, outer_radius=1.0, cells=tuple(cells))


def optimize_token_shape(
    token: str,
    outer_sides: int,
    features: Sequence[SemanticFeature],
    attempts: int = 512,
    seed: int = 618,
) -> SemanticTokenShape:
    rng = random.Random(seed + sum(ord(ch) for ch in token))
    candidates: list[SemanticTokenShape] = []
    for attempt in range(attempts):
        candidates.append(deterministic_candidate(token, outer_sides, features, attempt, rng))
    return max(candidates, key=fit_score)


def baseline_token_shape(token: str, outer_sides: int, features: Sequence[SemanticFeature]) -> SemanticTokenShape:
    cells: list[PackedCell] = []
    for index, feature in enumerate(features):
        radius = feature_radius(feature)
        # Flat lane baseline intentionally ignores octave shells and harmonic phase.
        cells.append(
            PackedCell(
                feature=feature,
                radius=radius,
                center=(-0.42 + 0.17 * index, 0.0),
                rotation=0.0,
            )
        )
    return SemanticTokenShape(token=token, outer_sides=outer_sides, outer_radius=1.0, cells=tuple(cells))


def octave_linked(left: PackedCell, right: PackedCell) -> bool:
    if abs(left.feature.octave_level - right.feature.octave_level) != 1:
        return False
    return not sat_overlap(cell_vertices(left), cell_vertices(right))


def phase_linked(left: PackedCell, right: PackedCell, tolerance: float = 0.20) -> bool:
    phase_delta = abs((left.rotation - right.rotation + math.pi) % (2.0 * math.pi) - math.pi)
    return phase_delta <= tolerance and not sat_overlap(cell_vertices(left), cell_vertices(right))


def evaluate_shape(shape: SemanticTokenShape) -> PackingReport:
    outer_vertices = regular_polygon_vertices(shape.outer_sides, shape.outer_radius)
    cell_polygons = [cell_vertices(cell) for cell in shape.cells]
    outer_area = polygon_area(outer_vertices)
    inner_area = sum(polygon_area(vertices) for vertices in cell_polygons)
    collisions = sum(
        1
        for index, left in enumerate(cell_polygons)
        for right in cell_polygons[index + 1 :]
        if sat_overlap(left, right, clearance=0.002)
    )
    boundary_violations = sum(
        1 for vertices in cell_polygons if not polygon_inside_convex_polygon(vertices, outer_vertices)
    )
    octave_links = sum(
        1
        for index, left in enumerate(shape.cells)
        for right in shape.cells[index + 1 :]
        if octave_linked(left, right)
    )
    phase_links = sum(
        1
        for index, left in enumerate(shape.cells)
        for right in shape.cells[index + 1 :]
        if phase_linked(left, right)
    )
    utilization = inner_area / outer_area
    semantic_loss = min(1.0, collisions * 0.18 + boundary_violations * 0.32)
    score = utilization + 0.025 * octave_links + 0.02 * phase_links - semantic_loss
    return PackingReport(
        token=shape.token,
        outer_hull_area=outer_area,
        inner_area=inner_area,
        utilization=utilization,
        collision_count=collisions,
        boundary_violation_count=boundary_violations,
        octave_link_count=octave_links,
        phase_link_count=phase_links,
        fit_score=score,
        semantic_loss=semantic_loss,
    )


def shape_to_record(shape: SemanticTokenShape) -> dict[str, object]:
    return {
        "token": shape.token,
        "outer_sides": shape.outer_sides,
        "outer_radius": shape.outer_radius,
        "cells": [
            {
                "feature": cell.feature.name,
                "weight": cell.feature.weight,
                "octave_level": cell.feature.octave_level,
                "sides": cell.feature.sides,
                "radius": cell.radius,
                "center": list(cell.center),
                "rotation": cell.rotation,
            }
            for cell in shape.cells
        ],
    }


def build_benchmark() -> BenchmarkReport:
    specs = [
        ("CALLABLE", 6),
        ("CONTROL_FLOW", 8),
        ("DATA_SYMBOL", 5),
        ("GOVERNANCE_GATE", 7),
    ]
    optimized_shapes = [
        optimize_token_shape(token, outer_sides, DEFAULT_FEATURES[token])
        for token, outer_sides in specs
    ]
    baselines = [
        baseline_token_shape(token, outer_sides, DEFAULT_FEATURES[token])
        for token, outer_sides in specs
    ]
    reports = [evaluate_shape(shape) for shape in optimized_shapes]
    baseline_reports = [evaluate_shape(shape) for shape in baselines]
    avg_loss = sum(report.semantic_loss for report in reports) / len(reports)
    avg_baseline_loss = sum(report.semantic_loss for report in baseline_reports) / len(baseline_reports)
    avg_score = sum(report.fit_score for report in reports) / len(reports)
    avg_baseline_score = sum(report.fit_score for report in baseline_reports) / len(baseline_reports)
    return BenchmarkReport(
        source={
            "inspiration": "polygon packing optimization and separating-axis collision checks",
            "implementation": "independent SCBE semantic geometry probe; no GPL source vendored",
            "boundary": "outer hull identity stays invariant; inner geometry can re-pack only if semantic loss stays bounded",
        },
        passed=all(report.semantic_loss == 0.0 for report in reports) and avg_score > avg_baseline_score,
        generated_shapes=[shape_to_record(shape) for shape in optimized_shapes],
        reports=[asdict(report) for report in reports],
        baseline_reports=[asdict(report) for report in baseline_reports],
        aggregate={
            "avg_semantic_loss": avg_loss,
            "avg_baseline_semantic_loss": avg_baseline_loss,
            "avg_fit_score": avg_score,
            "avg_baseline_fit_score": avg_baseline_score,
            "fit_score_lift": avg_score - avg_baseline_score,
        },
    )


def write_report(path: Path) -> BenchmarkReport:
    report = build_benchmark()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the layered semantic geometry packing benchmark.")
    parser.add_argument("--out", type=Path, default=Path("artifacts/experiments/layered_geometry_semantic_packing.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = write_report(args.out)
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
