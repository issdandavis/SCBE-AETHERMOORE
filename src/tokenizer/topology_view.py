from __future__ import annotations

import math
from typing import Any

from src.ca_lexicon import ALL_LANG_MAP, ALL_TONGUE_NAMES, EXTENDED_LANG_MAP, LANG_MAP, TONGUE_NAMES
from src.contracts.operation_panel import build_operation_panel


def _safe_id(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text)


def _heading_label(angle_degrees: float) -> str:
    headings = ("east", "north_east", "north", "north_west", "west", "south_west", "south", "south_east")
    shifted = (angle_degrees + 22.5) % 360.0
    return headings[int(shifted // 45.0) % len(headings)]


def _normalize_feature_vector(vector: list[float]) -> list[float]:
    scales = (118.0, 18.0, 7.0, 8.0, 4.0, 7.0, 5.0, 1.0)
    normalized: list[float] = []
    for index, value in enumerate(vector):
        scale = scales[index] if index < len(scales) else max(abs(value), 1.0)
        normalized.append(round(max(0.0, min(1.0, float(value) / float(scale or 1.0))), 6))
    return normalized


def _polygon_vertices(
    normalized_vector: list[float],
    *,
    traversal_index: int,
    spiral_state: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    vertices: list[dict[str, Any]] = []
    spiral_position = spiral_state.get("position", {}) if isinstance(spiral_state, dict) else {}
    z_bias = float(spiral_position.get("z", 0.0)) * 0.25
    centroid_x = 0.0
    centroid_y = 0.0
    centroid_z = 0.0
    count = max(1, len(normalized_vector))
    for axis_index, value in enumerate(normalized_vector):
        theta = (2.0 * math.pi * axis_index) / count
        radius = 0.22 + (0.78 * value)
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        z = z_bias + ((float(axis_index) / max(1.0, float(count - 1))) - 0.5) * 0.35
        vertex = {
            "axis_index": axis_index,
            "value": round(value, 6),
            "x": round(x, 6),
            "y": round(y, 6),
            "z": round(z, 6),
        }
        vertices.append(vertex)
        centroid_x += x
        centroid_y += y
        centroid_z += z

    centroid = {
        "x": round(centroid_x / count, 6),
        "y": round(centroid_y / count, 6),
        "z": round(centroid_z / count, 6),
    }
    return vertices, centroid


def _area_proxy(vertices: list[dict[str, Any]]) -> float:
    if len(vertices) < 3:
        return 0.0
    area = 0.0
    for index, vertex in enumerate(vertices):
        nxt = vertices[(index + 1) % len(vertices)]
        area += (float(vertex["x"]) * float(nxt["y"])) - (float(nxt["x"]) * float(vertex["y"]))
    return round(abs(area) * 0.5, 6)


def _keyboard_slot(position: dict[str, int]) -> str:
    row = int(position.get("row", 0))
    col = int(position.get("col", 0))
    row_label = chr(ord("A") + row)
    return f"{row_label}{col + 1}"


def _command_phase_candidates(packet: dict[str, Any]) -> list[str]:
    lexical_tokens = [str(token) for token in packet.get("lexical_tokens", [])]
    quarks = [str(item) for item in packet.get("semantic_expression", {}).get("quarks", [])]
    candidates: list[str] = []
    token_set = set(lexical_tokens)

    if "+" in token_set:
        candidates.append("arithmetic:add")
    if "-" in token_set:
        candidates.append("arithmetic:sub")
    if "*" in token_set:
        candidates.append("arithmetic:mul")
    if "/" in token_set:
        candidates.append("arithmetic:div")
    if "%" in token_set:
        candidates.append("arithmetic:mod")
    if "==" in token_set:
        candidates.append("comparison:eq")
    if "!=" in token_set:
        candidates.append("comparison:neq")
    if "<=" in token_set:
        candidates.append("comparison:lte")
    if ">=" in token_set:
        candidates.append("comparison:gte")
    if "<" in token_set:
        candidates.append("comparison:lt")
    if ">" in token_set:
        candidates.append("comparison:gt")
    if "arithmetic_transform" in quarks and not candidates:
        candidates.extend(
            [
                "arithmetic:add",
                "arithmetic:sub",
                "arithmetic:mul",
                "arithmetic:div",
                "arithmetic:mod",
            ]
        )
    if "comparison_gate" in quarks and not any(item.startswith("comparison:") for item in candidates):
        candidates.extend(
            [
                "comparison:eq",
                "comparison:neq",
                "comparison:lt",
                "comparison:lte",
                "comparison:gt",
                "comparison:gte",
            ]
        )

    semantic_label = str(packet.get("semantic_expression", {}).get("label", "")).strip()
    if semantic_label and semantic_label != "generic_program_bin":
        candidates.append(semantic_label)

    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _command_band_hints(packet: dict[str, Any]) -> set[str]:
    hints: set[str] = set()
    lexical_tokens = {str(token) for token in packet.get("lexical_tokens", [])}
    quarks = {str(item) for item in packet.get("semantic_expression", {}).get("quarks", [])}
    if any(token in {"+", "-", "*", "/", "%"} for token in lexical_tokens) or "arithmetic_transform" in quarks:
        hints.add("ARITHMETIC")
    if any(token in {"and", "or", "not", "&", "|", "^", "<<", ">>"} for token in lexical_tokens):
        hints.add("LOGIC")
    if any(token in {"==", "!=", "<", ">", "<=", ">="} for token in lexical_tokens) or "comparison_gate" in quarks:
        hints.add("COMPARISON")
    if any(quark in {"iteration_flow", "summary_emit"} for quark in quarks):
        hints.add("AGGREGATION")
    return hints


def _active_command_bindings(packet: dict[str, Any], keyboard_command_map: list[dict[str, Any]]) -> dict[str, Any]:
    lexical_tokens = [str(token) for token in packet.get("lexical_tokens", [])]
    lexical_token_set = {token.lower() for token in lexical_tokens}
    semantic_label = str(packet.get("semantic_expression", {}).get("label", "")).strip().lower()
    phase_candidates = _command_phase_candidates(packet)
    band_hints = _command_band_hints(packet)

    scored: list[dict[str, Any]] = []
    for entry in keyboard_command_map:
        command_key = str(entry.get("command_key", "")).lower()
        phase_operation = str(entry.get("phase_operation", ""))
        band = str(entry.get("band", "")).upper()
        score = 0.0
        reasons: list[str] = []

        if phase_operation in phase_candidates:
            score += 10.0
            reasons.append("phase_candidate")
        if semantic_label and command_key == semantic_label:
            score += 8.0
            reasons.append("semantic_label")
        if command_key in lexical_token_set:
            score += 4.0
            reasons.append("lexical_token")
        if band and band in band_hints:
            score += 2.0
            reasons.append("band_hint")
        if phase_operation.startswith("comparison:") and "comparison_gate" in packet.get("semantic_expression", {}).get(
            "quarks", []
        ):
            score += 1.5
            reasons.append("comparison_quark")
        if phase_operation.startswith("arithmetic:") and "arithmetic_transform" in packet.get(
            "semantic_expression", {}
        ).get("quarks", []):
            score += 1.5
            reasons.append("arithmetic_quark")

        if score <= 0.0:
            continue

        scored.append(
            {
                **entry,
                "topology_local_relevance_score": round(score, 3),
                "match_reasons": reasons,
            }
        )

    scored.sort(
        key=lambda item: (
            -float(item["topology_local_relevance_score"]),
            int(item.get("op_id", 999)),
        )
    )
    anchor = scored[0] if scored else None
    return {
        "phase_candidates": phase_candidates,
        "band_hints": sorted(band_hints),
        "anchor_command": anchor,
        "nearby_commands": scored[:8],
    }


def _operative_command(active_command_bindings: dict[str, Any]) -> dict[str, Any] | None:
    anchor = active_command_bindings.get("anchor_command")
    if not isinstance(anchor, dict):
        return None
    return {
        "command_key": anchor.get("command_key"),
        "phase_operation": anchor.get("phase_operation"),
        "key_slot": anchor.get("key_slot"),
        "binary_input": anchor.get("binary_input"),
        "op_id": anchor.get("op_id"),
        "band": anchor.get("band"),
        "topology_local_relevance_score": anchor.get("topology_local_relevance_score"),
        "match_reasons": anchor.get("match_reasons", []),
    }


def _route_packet(
    *,
    operative_command: dict[str, Any] | None,
    route_alignment: dict[str, Any],
    active_command_bindings: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(operative_command, dict):
        return None
    anchor_command = active_command_bindings.get("anchor_command") or {}
    support_commands = [
        entry.get("command_key")
        for entry in active_command_bindings.get("nearby_commands", [])
        if isinstance(entry, dict) and entry.get("command_key") != operative_command.get("command_key")
    ][:3]
    route_tongue = route_alignment.get("tongue")
    route_language = route_alignment.get("language")
    transport_tokens: dict[str, Any] = {}
    primary_transport_tokens = anchor_command.get("primary_transport_tokens", {})
    if route_tongue and route_tongue in primary_transport_tokens:
        transport_tokens[route_tongue] = primary_transport_tokens[route_tongue]
    return {
        "operative_command": operative_command.get("phase_operation"),
        "command_key": operative_command.get("command_key"),
        "key_slot": operative_command.get("key_slot"),
        "binary_input": operative_command.get("binary_input"),
        "route_tongue": route_tongue,
        "route_language": route_language,
        "transport_tokens": transport_tokens,
        "support_commands": support_commands,
    }


def _thought_field_cost_retro(
    *,
    polygons: list[dict[str, Any]],
    chains: list[dict[str, Any]],
    operative_command: dict[str, Any] | None,
    route_packet: dict[str, Any] | None,
    active_command_bindings: dict[str, Any],
) -> dict[str, Any]:
    support_count = len((route_packet or {}).get("support_commands", []))
    relevance_score = float((operative_command or {}).get("topology_local_relevance_score") or 0.0)
    match_reasons = list((operative_command or {}).get("match_reasons", []))
    polygon_count = len(polygons)
    segment_costs: list[dict[str, Any]] = []
    total_distance_cost = 0.0
    total_drift_cost = 0.0
    total_recovery_cost = 0.0
    total_time_cost = 0.0
    total_energy_cost = 0.0
    total_risk_cost = 0.0

    for _index, chain in enumerate(chains):
        distance_cost = float(chain.get("distance") or 0.0)
        drift_cost = abs(float(chain.get("delta", {}).get("z") or 0.0))
        recovery_cost = float(chain.get("torsion_proxy") or 0.0) * 0.2
        time_cost = 1.0
        energy_cost = max(0.05, distance_cost * 0.35)
        risk_cost = drift_cost * 0.5

        total_distance_cost += distance_cost
        total_drift_cost += drift_cost
        total_recovery_cost += recovery_cost
        total_time_cost += time_cost
        total_energy_cost += energy_cost
        total_risk_cost += risk_cost

        segment_costs.append(
            {
                "segment_id": chain.get("id"),
                "source": chain.get("source"),
                "target": chain.get("target"),
                "distance_cost": round(distance_cost, 6),
                "drift_cost": round(drift_cost, 6),
                "recovery_cost": round(recovery_cost, 6),
                "time_cost": round(time_cost, 6),
                "energy_cost": round(energy_cost, 6),
                "risk_cost": round(risk_cost, 6),
                "segment_total_cost": round(
                    distance_cost + drift_cost + recovery_cost + time_cost + energy_cost + risk_cost, 6
                ),
            }
        )

    correction_cost = round(support_count * 0.25, 6)
    conflict_cost = round(max(0.0, 1.0 - min(1.0, relevance_score / 10.0)), 6)
    objective_distance_cost = round(max(0.0, 1.0 - min(1.0, relevance_score / 12.0)), 6)
    route_total_cost = round(
        total_distance_cost
        + total_drift_cost
        + total_recovery_cost
        + total_time_cost
        + total_energy_cost
        + total_risk_cost
        + correction_cost
        + conflict_cost
        + objective_distance_cost,
        6,
    )
    corridor_efficiency = round(relevance_score / max(route_total_cost, 0.001), 6)
    preferred_leyline = "semantic_backbone"
    if total_drift_cost <= total_distance_cost * 0.2:
        preferred_leyline = "harmonic_spine"
    elif support_count >= 2:
        preferred_leyline = "binary_spine"

    return {
        "objective": {
            "operative_command": (route_packet or {}).get("operative_command"),
            "command_key": (route_packet or {}).get("command_key"),
            "route_tongue": (route_packet or {}).get("route_tongue"),
            "route_language": (route_packet or {}).get("route_language"),
        },
        "totals": {
            "distance_cost": round(total_distance_cost, 6),
            "drift_cost": round(total_drift_cost, 6),
            "recovery_cost": round(total_recovery_cost, 6),
            "time_cost": round(total_time_cost, 6),
            "energy_cost": round(total_energy_cost, 6),
            "risk_cost": round(total_risk_cost, 6),
            "correction_cost": correction_cost,
            "conflict_cost": conflict_cost,
            "objective_distance_cost": objective_distance_cost,
            "route_total_cost": route_total_cost,
        },
        "segments": segment_costs,
        "route_memory": {
            "polygon_count": polygon_count,
            "support_count": support_count,
            "match_reasons": match_reasons,
            "corridor_efficiency": corridor_efficiency,
            "preferred_leyline": preferred_leyline,
            "cheapest_next_support": next(
                (
                    entry.get("command_key")
                    for entry in active_command_bindings.get("nearby_commands", [])
                    if isinstance(entry, dict) and entry.get("command_key") != (route_packet or {}).get("command_key")
                ),
                None,
            ),
        },
    }


def _topology_dictionaries(packet: dict[str, Any]) -> dict[str, Any]:
    panel = build_operation_panel(include_extended=True)
    keyboard_command_map: list[dict[str, Any]] = []
    for cell in panel["alpha_panel"]["cells"]:
        keyboard_command_map.append(
            {
                "key_slot": _keyboard_slot(cell["position"]),
                "position": cell["position"],
                "op_id": cell["op_id"],
                "binary_input": cell["binary_input"],
                "command_key": cell["phase_command"]["command_key"],
                "phase_operation": cell["phase_command"]["phase_operation"],
                "band": cell["band"],
                "languages": {
                    tongue: {
                        "language": cell["languages"][tongue],
                        "template": cell["code_templates"][tongue],
                    }
                    for tongue in cell["languages"]
                },
                "primary_transport_tokens": {
                    tongue: next(
                        (
                            entry["transport_token"]
                            for entry in panel["overlays"]["sacred_transport_sheets"][tongue]
                            if entry["command_key"] == cell["phase_command"]["command_key"]
                        ),
                        None,
                    )
                    for tongue in TONGUE_NAMES
                },
            }
        )

    language_projections = [
        {
            "tongue": str(view.get("tongue")),
            "conlang": str(view.get("conlang")),
            "language": str(view.get("language")),
            "role": str(view.get("role")),
            "tokenizer_token_count": int(view.get("tokenizer", {}).get("token_count", 0)),
        }
        for view in packet.get("language_views", [])
    ]

    active_command_bindings = _active_command_bindings(packet, keyboard_command_map)
    return {
        "coding_languages": {
            "primary": dict(LANG_MAP),
            "extended": dict(EXTENDED_LANG_MAP),
            "all": dict(ALL_LANG_MAP),
        },
        "tokenizer_tongues": {
            "primary": list(TONGUE_NAMES),
            "extended": [tongue for tongue in ALL_TONGUE_NAMES if tongue not in TONGUE_NAMES],
            "language_projections": language_projections,
        },
        "keyboard_command_map": keyboard_command_map,
        "active_command_bindings": active_command_bindings,
    }


def build_topology_view(packet: dict[str, Any], *, max_binary_nodes: int = 32) -> dict[str, Any]:
    stisa = packet.get("stisa", {})
    field_definitions = stisa.get("field_definitions", [])
    stisa_rows = stisa.get("token_rows", [])
    binary_groups = stisa.get("binary_groups", [])[:max_binary_nodes]
    braille_lane = packet.get("braille_lane", {})
    braille_cells = braille_lane.get("binary_surface", {}).get("cells", [])[:max_binary_nodes]
    harmonic_states = braille_lane.get("harmonic_spiral", {}).get("states", [])[:max_binary_nodes]
    route = packet.get("route", {})
    language_views = packet.get("language_views", [])

    harmonic_by_index = {
        int(state.get("index", -1)): state
        for state in harmonic_states
        if isinstance(state, dict) and isinstance(state.get("index", -1), int)
    }
    binary_by_index = {
        int(group.get("index", -1)): group
        for group in binary_groups
        if isinstance(group, dict) and isinstance(group.get("index", -1), int)
    }
    braille_by_index = {
        int(cell.get("index", -1)): cell
        for cell in braille_cells
        if isinstance(cell, dict) and isinstance(cell.get("index", -1), int)
    }

    dictionaries = _topology_dictionaries(packet)
    active_command_bindings = dictionaries["active_command_bindings"]
    operative_command = _operative_command(active_command_bindings)

    polygons: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    centroid_vectors: list[tuple[float, float, float]] = []
    axis_totals = [0.0 for _ in field_definitions]
    traversal_order: list[str] = []

    for index, row in enumerate(stisa_rows):
        normalized = _normalize_feature_vector(list(row.get("feature_vector", [])))
        spiral_state = harmonic_by_index.get(index)
        vertices, centroid = _polygon_vertices(normalized, traversal_index=index, spiral_state=spiral_state)
        angle = (math.degrees(math.atan2(float(centroid["y"]), float(centroid["x"]))) + 360.0) % 360.0
        compass_sector = _heading_label(angle)
        area_proxy = _area_proxy(vertices)
        polygon_id = f"polygon:{index}:{_safe_id(str(row.get('token', 'token')))}"
        polygons.append(
            {
                "id": polygon_id,
                "traversal_index": index,
                "token": row.get("token"),
                "semantic_class": row.get("semantic_class"),
                "tongue": row.get("tongue"),
                "language": row.get("language"),
                "normalized_vector": normalized,
                "vertices": vertices,
                "centroid": centroid,
                "area_proxy": area_proxy,
                "compass_sector": compass_sector,
                "spiral_anchor": spiral_state.get("position", {}) if spiral_state else {},
                "binary_group": binary_by_index.get(index, {}),
                "braille_cell": braille_by_index.get(index, {}),
            }
        )
        nodes.append(
            {
                "id": polygon_id,
                "kind": "data_polygon",
                "label": str(row.get("token", "token")),
                "metadata": {
                    "semantic_class": row.get("semantic_class"),
                    "compass_sector": compass_sector,
                    "area_proxy": area_proxy,
                },
            }
        )
        traversal_order.append(polygon_id)
        centroid_vectors.append((float(centroid["x"]), float(centroid["y"]), float(centroid["z"])))
        for axis_index, value in enumerate(normalized):
            if axis_index < len(axis_totals):
                axis_totals[axis_index] += value

        if index in binary_by_index:
            edges.append(
                {
                    "source": polygon_id,
                    "target": f"binary_group:{index}",
                    "relation": "anchors_to_binary_group",
                }
            )
        if index in braille_by_index:
            braille_id = f"braille:{index}"
            nodes.append(
                {
                    "id": braille_id,
                    "kind": "braille_cell",
                    "label": braille_by_index[index].get("unicode", ""),
                    "metadata": braille_by_index[index],
                }
            )
            edges.append(
                {"source": f"binary_group:{index}", "target": braille_id, "relation": "projects_to_braille_cell"}
            )
        if index in harmonic_by_index:
            spiral_id = f"spiral:{index}"
            nodes.append(
                {
                    "id": spiral_id,
                    "kind": "harmonic_spiral_state",
                    "label": harmonic_by_index[index].get("validity", "spiral"),
                    "metadata": harmonic_by_index[index],
                }
            )
            edges.append(
                {
                    "source": f"binary_group:{index}",
                    "target": spiral_id,
                    "relation": "evolves_to_harmonic_state",
                }
            )

    for group in binary_groups:
        index = int(group.get("index", 0))
        nodes.append(
            {
                "id": f"binary_group:{index}",
                "kind": "binary_group",
                "label": str(group.get("bits", "")),
                "metadata": group,
            }
        )

    chains: list[dict[str, Any]] = []
    for index in range(len(polygons) - 1):
        source = polygons[index]
        target = polygons[index + 1]
        dx = float(target["centroid"]["x"]) - float(source["centroid"]["x"])
        dy = float(target["centroid"]["y"]) - float(source["centroid"]["y"])
        dz = float(target["centroid"]["z"]) - float(source["centroid"]["z"])
        distance = math.sqrt((dx * dx) + (dy * dy) + (dz * dz))
        angle = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
        chains.append(
            {
                "id": f"chain:{index}",
                "source": source["id"],
                "target": target["id"],
                "relation": "amino_backbone_traverse",
                "delta": {
                    "x": round(dx, 6),
                    "y": round(dy, 6),
                    "z": round(dz, 6),
                },
                "distance": round(distance, 6),
                "heading_degrees": round(angle, 6),
                "heading_label": _heading_label(angle),
                "torsion_proxy": round(abs(dz) + (distance / max(1.0, float(index + 1))), 6),
            }
        )
        edges.append(
            {
                "source": source["id"],
                "target": target["id"],
                "relation": "amino_backbone_traverse",
            }
        )

    polygon_count = len(polygons)
    axis_trends = []
    for axis_index, axis in enumerate(field_definitions):
        avg = axis_totals[axis_index] / polygon_count if polygon_count else 0.0
        axis_trends.append(
            {
                "axis_index": axis_index,
                "name": axis.get("name", f"axis_{axis_index}"),
                "mean_value": round(avg, 6),
            }
        )
    axis_trends.sort(key=lambda item: item["mean_value"], reverse=True)

    avg_x = sum(item[0] for item in centroid_vectors) / polygon_count if polygon_count else 0.0
    avg_y = sum(item[1] for item in centroid_vectors) / polygon_count if polygon_count else 0.0
    avg_z = sum(item[2] for item in centroid_vectors) / polygon_count if polygon_count else 0.0
    heading = (math.degrees(math.atan2(avg_y, avg_x)) + 360.0) % 360.0 if polygon_count else 0.0

    leylines = [
        {
            "id": "leyline:semantic_backbone",
            "kind": "semantic_backbone",
            "path": traversal_order,
        },
        {
            "id": "leyline:binary_spine",
            "kind": "binary_spine",
            "path": [f"binary_group:{group.get('index', 0)}" for group in binary_groups],
        },
        {
            "id": "leyline:harmonic_spine",
            "kind": "harmonic_spine",
            "path": [f"spiral:{state.get('index', 0)}" for state in harmonic_states],
        },
    ]
    for leyline in leylines:
        nodes.append(
            {
                "id": leyline["id"],
                "kind": "leyline",
                "label": leyline["kind"],
                "metadata": {"path_length": len(leyline["path"])},
            }
        )
        for target in leyline["path"]:
            edges.append({"source": leyline["id"], "target": target, "relation": "traces"})

    route_alignment = {
        "tongue": route.get("tongue", "KO"),
        "language": route.get("language", packet.get("language")),
    }
    route_packet = _route_packet(
        operative_command=operative_command,
        route_alignment=route_alignment,
        active_command_bindings=active_command_bindings,
    )
    cost_retro = _thought_field_cost_retro(
        polygons=polygons,
        chains=chains,
        operative_command=operative_command,
        route_packet=route_packet,
        active_command_bindings=active_command_bindings,
    )
    if isinstance(route_packet, dict):
        route_packet["cost_retro_summary"] = {
            "route_total_cost": cost_retro["totals"]["route_total_cost"],
            "preferred_leyline": cost_retro["route_memory"]["preferred_leyline"],
            "corridor_efficiency": cost_retro["route_memory"]["corridor_efficiency"],
        }
    if isinstance(operative_command, dict):
        operative_command["cost_retro_summary"] = {
            "route_total_cost": cost_retro["totals"]["route_total_cost"],
            "preferred_leyline": cost_retro["route_memory"]["preferred_leyline"],
        }

    return {
        "version": "scbe-topology-view-v1",
        "source_name": packet.get("source_name"),
        "language": packet.get("language"),
        "route_tongue": route.get("tongue", "KO"),
        "axes": field_definitions,
        "surfaces": {
            "source": {
                "name": packet.get("source_name"),
                "semantic_label": packet.get("semantic_expression", {}).get("label"),
            },
            "token_count": len(packet.get("lexical_tokens", [])),
            "stisa_row_count": len(stisa_rows),
            "binary_group_count": len(binary_groups),
            "braille_cell_count": len(braille_cells),
            "harmonic_spiral_state_count": len(harmonic_states),
            "language_projection_count": len(language_views),
        },
        "nodes": nodes,
        "edges": edges,
        "polygons": polygons,
        "chains": chains,
        "compass": {
            "heading_degrees": round(heading, 6),
            "heading_label": _heading_label(heading),
            "vertical_bias": round(avg_z, 6),
            "trend_axes": axis_trends[:3],
            "route_alignment": route_alignment,
        },
        "leylines": leylines,
        "dictionaries": dictionaries,
        "operative_command": operative_command,
        "route_packet": route_packet,
        "cost_retro": cost_retro,
        "traversal_order": traversal_order,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "polygon_count": len(polygons),
            "chain_count": len(chains),
            "leyline_count": len(leylines),
            "operative_command": operative_command,
            "route_packet": route_packet,
            "cost_retro": {
                "route_total_cost": cost_retro["totals"]["route_total_cost"],
                "preferred_leyline": cost_retro["route_memory"]["preferred_leyline"],
            },
        },
    }


def topology_to_mermaid(topology: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for polygon in topology.get("polygons", []):
        node_id = _safe_id(str(polygon["id"]))
        label = f"{polygon.get('token', 'token')}::{polygon.get('compass_sector', 'axis')}"
        lines.append(f'    {node_id}["polygon: {label}"]')
    for chain in topology.get("chains", []):
        source = _safe_id(str(chain["source"]))
        target = _safe_id(str(chain["target"]))
        relation = str(chain.get("heading_label", "flow"))
        lines.append(f"    {source} -->|{relation}| {target}")
    return "\n".join(lines)


def topology_to_dot(topology: dict[str, Any]) -> str:
    lines = ["digraph SCBETopologyView {", "  rankdir=LR;", "  node [shape=hexagon];"]
    for polygon in topology.get("polygons", []):
        node_id = _safe_id(str(polygon["id"]))
        label = f"{polygon.get('token', 'token')}::{polygon.get('compass_sector', 'axis')}"
        lines.append(f'  {node_id} [label="polygon: {label}"];')
    for chain in topology.get("chains", []):
        source = _safe_id(str(chain["source"]))
        target = _safe_id(str(chain["target"]))
        relation = str(chain.get("heading_label", "flow")).replace('"', "'")
        lines.append(f'  {source} -> {target} [label="{relation}"];')
    lines.append("}")
    return "\n".join(lines)


__all__ = ["build_topology_view", "topology_to_dot", "topology_to_mermaid"]
