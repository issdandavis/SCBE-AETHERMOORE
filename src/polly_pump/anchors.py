from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from src.harmonic.state21_product_metric import product_metric_distance_v1


def _bearing_delta(a_deg: float, b_deg: float) -> float:
    return abs(((a_deg - b_deg + 180.0) % 360.0) - 180.0)


@dataclass(frozen=True)
class SymbolicLocator:
    wing: str
    hall: str
    room: str
    closet: str | None = None
    drawer: str | None = None


@dataclass(frozen=True)
class OrientationFrame:
    bearing_deg: float = 0.0
    celestial_anchor: str | None = None
    cardinal_frame: str = "N-E"


@dataclass(frozen=True)
class ZoomAnchor:
    anchor_id: str
    symbolic_locator: SymbolicLocator
    scale_band: float
    gateway_type: str
    orientation: OrientationFrame = OrientationFrame()
    visual_ref: str | None = None
    audio_ref: str | None = None
    empirical_ref: str | None = None
    manifold_position: tuple[float, ...] | None = None
    parent_anchor_id: str | None = None


@dataclass(frozen=True)
class AnchorTransition:
    source_anchor_id: str
    target_anchor_id: str
    geometry_distance: float
    bearing_delta_deg: float
    scale_delta: float
    symbolic_penalty: float
    transition_cost: float


def _fallback_geometry(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Fallback geometry requires equal-length vectors")
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def compute_anchor_transition(source: ZoomAnchor, target: ZoomAnchor) -> AnchorTransition:
    geometry_distance = 0.0
    if source.manifold_position is not None and target.manifold_position is not None:
        if len(source.manifold_position) == 21 and len(target.manifold_position) == 21:
            geometry_distance = product_metric_distance_v1(source.manifold_position, target.manifold_position)
        else:
            geometry_distance = _fallback_geometry(source.manifold_position, target.manifold_position)

    bearing_delta = _bearing_delta(source.orientation.bearing_deg, target.orientation.bearing_deg)
    scale_delta = abs(float(source.scale_band) - float(target.scale_band))

    symbolic_penalty = 0.0
    if source.symbolic_locator.wing != target.symbolic_locator.wing:
        symbolic_penalty += 0.35
    if source.symbolic_locator.hall != target.symbolic_locator.hall:
        symbolic_penalty += 0.2
    if source.orientation.celestial_anchor and target.orientation.celestial_anchor:
        if source.orientation.celestial_anchor != target.orientation.celestial_anchor:
            symbolic_penalty += 0.1

    transition_cost = geometry_distance + scale_delta + (bearing_delta / 180.0) + symbolic_penalty
    return AnchorTransition(
        source_anchor_id=source.anchor_id,
        target_anchor_id=target.anchor_id,
        geometry_distance=geometry_distance,
        bearing_delta_deg=bearing_delta,
        scale_delta=scale_delta,
        symbolic_penalty=symbolic_penalty,
        transition_cost=transition_cost,
    )

