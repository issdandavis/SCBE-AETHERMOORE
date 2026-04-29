"""GeoSeal mission compass packets for terrain, code, and return routing.

This module keeps a remote agent's mission state in one GeoSeal-shaped
contract: telemetry is converted into waypoints, routes, minimap cells, and
action packets that can be sealed, replayed, or fed into training lanes.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.geoseal import clamp_to_ball, hyperbolic_distance
from src.geoseal_compass import (
    COMPASS_BEARINGS,
    TONGUES,
    bearing_to_string,
    build_segment,
    compute_bearing,
    create_waypoint,
    generate_compass_rose,
    plan_route,
    triadic_temporal_distance,
)

MISSION_VERSION = "geoseal-mars-mission-compass-v1"
DEFAULT_DIMENSION = 6

GOAL_TONGUE_HINTS: Dict[str, tuple[str, ...]] = {
    "KO": ("map", "terrain", "survey", "search", "scan", "locate", "prioritize"),
    "AV": ("code", "build", "script", "software", "patch", "compile", "automate"),
    "RU": ("repair", "recover", "fault", "debug", "stabilize", "verify"),
    "CA": ("home", "return", "navigate", "route", "base", "landing", "safe"),
    "UM": ("science", "sample", "analyze", "model", "optimize", "experiment"),
    "DR": ("communicate", "relay", "compress", "archive", "explain", "handoff"),
}

ACTION_TONGUES: Dict[str, str] = {
    "map_terrain": "KO",
    "code_solution": "AV",
    "stabilize_faults": "RU",
    "navigate_home": "CA",
    "science_sample": "UM",
    "compress_handoff": "DR",
}


@dataclass(frozen=True)
class TerrainSample:
    """A single telemetry point projected into the GeoSeal mission surface."""

    id: str
    label: str
    position: List[float]
    difficulty: float = 0.0
    hazard: float = 0.0
    signal: float = 1.0
    resource: Optional[str] = None
    slope: float = 0.0
    roughness: float = 0.0
    albedo: Optional[float] = None
    mineral_hint: Optional[str] = None
    stratigraphy_hint: Optional[str] = None
    time: float = 0.0


def _clamp_unit(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return min(1.0, max(0.0, number))


def _as_vector(value: Any, dimension: int = DEFAULT_DIMENSION) -> List[float]:
    if isinstance(value, Mapping):
        raw = [value.get(k, 0.0) for k in ("x", "y", "z", "w", "u", "v")]
    elif isinstance(value, list):
        raw = value
    else:
        raw = []
    vec = []
    for item in raw[:dimension]:
        try:
            vec.append(float(item))
        except (TypeError, ValueError):
            vec.append(0.0)
    while len(vec) < dimension:
        vec.append(0.0)
    return clamp_to_ball(vec, 0.92)


def infer_goal_tongue(goal: str) -> str:
    """Map a mission goal to the dominant GeoSeal tongue."""

    low = (goal or "").lower()
    scores = {tongue: 0 for tongue in TONGUES}
    for tongue, hints in GOAL_TONGUE_HINTS.items():
        scores[tongue] = sum(1 for hint in hints if hint in low)
    best = max(TONGUES, key=lambda tongue: (scores[tongue], -TONGUES.index(tongue)))
    return best if scores[best] > 0 else "KO"


def parse_terrain_samples(
    payload: Mapping[str, Any], dimension: int = DEFAULT_DIMENSION
) -> List[TerrainSample]:
    """Parse telemetry terrain samples into bounded Poincare-ball points."""

    samples: List[TerrainSample] = []
    for idx, item in enumerate(
        payload.get("terrain", []) or payload.get("telemetry", []) or []
    ):
        if not isinstance(item, Mapping):
            continue
        sid = str(item.get("id") or f"sample-{idx:03d}")
        label = str(item.get("label") or item.get("name") or sid)
        position = _as_vector(item.get("position", item), dimension)
        samples.append(
            TerrainSample(
                id=sid,
                label=label,
                position=position,
                difficulty=_clamp_unit(
                    item.get("difficulty", item.get("terrain_difficulty", 0.0))
                ),
                hazard=_clamp_unit(item.get("hazard", item.get("risk", 0.0))),
                signal=_clamp_unit(
                    item.get("signal", item.get("signal_strength", 1.0)), 1.0
                ),
                resource=str(item["resource"]) if item.get("resource") else None,
                slope=_clamp_unit(item.get("slope", 0.0)),
                roughness=_clamp_unit(item.get("roughness", 0.0)),
                albedo=(
                    _clamp_unit(item["albedo"])
                    if item.get("albedo") is not None
                    else None
                ),
                mineral_hint=(
                    str(item["mineral_hint"]) if item.get("mineral_hint") else None
                ),
                stratigraphy_hint=(
                    str(item["stratigraphy_hint"])
                    if item.get("stratigraphy_hint")
                    else None
                ),
                time=float(item.get("time", idx + 1)),
            )
        )
    return samples


def _sample_score(origin: List[float], sample: TerrainSample) -> float:
    distance = hyperbolic_distance(origin, sample.position)
    risk = (
        sample.hazard * 1.4
        + sample.difficulty * 0.9
        + sample.slope * 0.8
        + sample.roughness * 0.7
        + (1.0 - sample.signal) * 0.5
    )
    return distance + risk


def _route_samples(
    origin: List[float], samples: Iterable[TerrainSample], limit: int
) -> List[TerrainSample]:
    return sorted(samples, key=lambda sample: _sample_score(origin, sample))[:limit]


def _minimap_cell(sample: TerrainSample, origin: List[float]) -> Dict[str, Any]:
    bearing = compute_bearing(origin, sample.position)
    return {
        "id": sample.id,
        "label": sample.label,
        "position": [round(v, 6) for v in sample.position],
        "risk": round(
            (sample.hazard + sample.difficulty + (1.0 - sample.signal)) / 3.0, 6
        ),
        "hazard": sample.hazard,
        "difficulty": sample.difficulty,
        "geology": {
            "slope": sample.slope,
            "roughness": sample.roughness,
            "albedo": sample.albedo,
            "mineral_hint": sample.mineral_hint,
            "stratigraphy_hint": sample.stratigraphy_hint,
        },
        "signal": sample.signal,
        "resource": sample.resource,
        "dominant_tongue": bearing.dominant_tongue,
        "bearing": bearing_to_string(bearing),
    }


def _packet_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _action_packet(
    kind: str, goal: str, route_tongue: str, context: Mapping[str, Any]
) -> Dict[str, Any]:
    semantic_phrase = {
        "kind": kind,
        "goal": goal,
        "role": {
            "map_terrain": "map terrain from telemetry",
            "code_solution": "build or patch the mission solution",
            "stabilize_faults": "detect and stabilize route or execution faults",
            "navigate_home": "return to the home/base waypoint",
            "science_sample": "collect or analyze useful mission data",
            "compress_handoff": "compress state for relay or recovery",
        }[kind],
    }
    metric_payload = {
        "tongue": ACTION_TONGUES[kind],
        "mission_tongue": route_tongue,
        "phase": COMPASS_BEARINGS[ACTION_TONGUES[kind]],
        "context": dict(context),
    }
    transport_packet = {
        "encoding": "geoseal-action-packet-v1",
        "sha256": _packet_hash(
            {"semantic_phrase": semantic_phrase, "metric_payload": metric_payload}
        ),
    }
    return {
        "semantic_phrase": semantic_phrase,
        "metric_payload": metric_payload,
        "transport_packet": transport_packet,
    }


def build_mars_mission_compass(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a full GeoSeal mission packet from goal + telemetry."""

    goal = str(payload.get("goal") or "Map terrain, code solutions, and navigate home.")
    mission_id = str(payload.get("mission_id") or "mission")
    agent_id = str(payload.get("agent_id") or "agent")
    dimension = int(payload.get("dimension") or DEFAULT_DIMENSION)
    dimension = max(2, min(21, dimension))

    origin_pos = _as_vector(
        payload.get("position") or payload.get("current_position"), dimension
    )
    home_pos = _as_vector(
        payload.get("home_position")
        or payload.get("base_position")
        or [0.0] * dimension,
        dimension,
    )
    route_tongue = infer_goal_tongue(goal)
    samples = parse_terrain_samples(payload, dimension)
    selected = _route_samples(origin_pos, samples, int(payload.get("max_samples") or 8))

    current = create_waypoint(
        "current",
        f"{agent_id} current",
        origin_pos,
        COMPASS_BEARINGS[route_tongue],
        0.0,
        route_tongue,
    )
    terrain_waypoints = [
        create_waypoint(
            sample.id,
            sample.label,
            sample.position,
            COMPASS_BEARINGS[_minimap_cell(sample, origin_pos)["dominant_tongue"]],
            sample.time,
        )
        for sample in selected
    ]
    home = create_waypoint(
        "home",
        "home/base",
        home_pos,
        COMPASS_BEARINGS["CA"],
        max([s.time for s in selected], default=0.0) + 1.0,
        "CA",
    )

    terrain_route = (
        plan_route([current, *terrain_waypoints], min_governance=0.05)
        if terrain_waypoints
        else None
    )
    home_route = plan_route([current, home], min_governance=0.05)

    if terrain_waypoints:
        last = terrain_waypoints[-1]
        return_route = plan_route([last, home], min_governance=0.05)
    else:
        return_route = home_route

    minimap_cells = [_minimap_cell(sample, origin_pos) for sample in selected]
    worst_risk = max((cell["risk"] for cell in minimap_cells), default=0.0)
    action_context = {
        "mission_id": mission_id,
        "agent_id": agent_id,
        "sample_count": len(samples),
        "selected_sample_count": len(selected),
        "worst_minimap_risk": round(worst_risk, 6),
        "home_distance": round(home_route.total_distance, 6),
    }
    actions = [
        _action_packet("map_terrain", goal, route_tongue, action_context),
        _action_packet("code_solution", goal, route_tongue, action_context),
        _action_packet("stabilize_faults", goal, route_tongue, action_context),
        _action_packet("navigate_home", goal, route_tongue, action_context),
        _action_packet("science_sample", goal, route_tongue, action_context),
        _action_packet("compress_handoff", goal, route_tongue, action_context),
    ]

    metric_payload = {
        "mission_tongue": route_tongue,
        "dimension": dimension,
        "software_capabilities": [
            "visual_inertial_odometry",
            "stereo_or_monocular_terrain_reconstruction",
            "slope_roughness_hazard_mapping",
            "geology_tagging_from_telemetry",
            "route_to_home_with_governance_scores",
            "code_patch_packet_generation",
            "fault_stabilization_and_handoff_compression",
        ],
        "physical_tool_manual": build_physical_tool_manual(),
        "current_position": [round(v, 6) for v in origin_pos],
        "home_position": [round(v, 6) for v in home_pos],
        "terrain_route": _route_summary(terrain_route),
        "home_route": _route_summary(home_route),
        "return_route": _route_summary(return_route),
        "minimap": {
            "source": "telemetry",
            "cell_count": len(minimap_cells),
            "cells": minimap_cells,
        },
        "compass_rose": generate_compass_rose(),
    }
    semantic_phrase = {
        "goal": goal,
        "contract": (
            "GeoSeal is the sole mission substrate for terrain mapping, coding solutions, "
            "navigation home, and handoff."
        ),
    }
    transport_packet = {
        "encoding": MISSION_VERSION,
        "sha256": _packet_hash(
            {
                "semantic_phrase": semantic_phrase,
                "metric_payload": metric_payload,
                "actions": actions,
            }
        ),
    }
    return {
        "version": MISSION_VERSION,
        "mission_id": mission_id,
        "agent_id": agent_id,
        "semantic_phrase": semantic_phrase,
        "metric_payload": metric_payload,
        "transport_packet": transport_packet,
        "action_packets": actions,
    }


def build_physical_tool_manual() -> List[Dict[str, Any]]:
    """Physical instruments an agent can request, simulate, or document."""

    return [
        {
            "tool": "navigation_camera",
            "purpose": "surface-relative motion, visual odometry, hazard context, landing-zone checks",
            "agent_rule": (
                "ingest images and confidence; do not assume depth without stereo, motion, radar, or range data"
            ),
        },
        {
            "tool": "stereo_or_zoom_science_camera",
            "purpose": "outcrop shape, layering, texture, color, stratigraphy, traverse scouting",
            "agent_rule": "tag geology hypotheses separately from confirmed mineralogy",
        },
        {
            "tool": "imu_inclinometer_altimeter",
            "purpose": "attitude, acceleration, slope estimate, altitude above ground, flight/drive stability",
            "agent_rule": "treat drift and feature-poor terrain as route risk that must be surfaced in the minimap",
        },
        {
            "tool": "environment_sensors",
            "purpose": "wind, pressure, temperature, dust, humidity, thermal stress, flight envelope limits",
            "agent_rule": "convert conditions into go/no-go and energy/thermal constraints",
        },
        {
            "tool": "geochemistry_or_spectroscopy_payload",
            "purpose": "elemental/mineral/organic clues when a rover-class instrument is available",
            "agent_rule": "keep remote visual geology separate from instrument-confirmed chemistry",
        },
        {
            "tool": "ground_penetrating_radar",
            "purpose": "subsurface layering and buried geologic structure when available",
            "agent_rule": "route radar-derived layers as a separate depth lane in the metric payload",
        },
        {
            "tool": "radio_or_relay_link",
            "purpose": "handoff packets, health telemetry, command windows, map updates",
            "agent_rule": "compress state through DR handoff packets when bandwidth or light-time is constrained",
        },
        {
            "tool": "power_and_thermal_system",
            "purpose": "battery, solar/RTG budget, heater duty cycle, survival limits",
            "agent_rule": "block routes that spend energy or heat beyond mission envelope",
        },
    ]


def _route_summary(route: Optional[Any]) -> Optional[Dict[str, Any]]:
    if route is None:
        return None
    return {
        "waypoints": [wp.id for wp in route.waypoints],
        "segments": [
            {
                "from": segment.from_wp.id,
                "to": segment.to_wp.id,
                "distance": round(segment.distance, 6),
                "bearing": bearing_to_string(segment.bearing),
                "dominant_tongue": segment.bearing.dominant_tongue,
                "governance_score": round(segment.governance_score, 6),
                "phase_deviation": round(segment.phase_deviation, 6),
                "temporal_span": round(segment.temporal_span, 6),
            }
            for segment in route.segments
        ],
        "total_distance": round(route.total_distance, 6),
        "min_governance_score": round(route.min_governance_score, 6),
        "avg_governance_score": round(route.avg_governance_score, 6),
        "triadic_temporal_distance": round(triadic_temporal_distance(route), 6),
        "is_viable": route.is_viable,
    }
