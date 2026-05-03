#!/usr/bin/env python3
"""Readable terminal front-end for GeoSeal agentic source finding."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.research.geoseal_research_routes import build_research_route_matrix  # noqa: E402

SCHEMA_VERSION = "scbe_geoseal_source_terminal_v1"


LANE_NAMES = {
    "KO": "intent and discovery",
    "AV": "media and archive",
    "RU": "risk and citation",
    "CA": "telemetry and compute",
    "UM": "knowledge synthesis",
    "DR": "audio and final report",
}


def _short(value: Any, limit: int = 78) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)]}..."


def build_source_terminal_state(
    *,
    family: str | None = None,
    source_id: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    matrix = build_research_route_matrix(family=family, source_id=source_id, query=query)
    lanes: dict[str, list[dict[str, Any]]] = {}
    for route in matrix["routes"]:
        lanes.setdefault(route["lane"], []).append(route)

    next_actions = [
        "Use geoseal research-sources --json for machine packets.",
        "Open primary sources before quoting or training from any discovery result.",
        "Keep live aviation, radio, satellite, and Tor evidence quarantine-first until promoted.",
        "Write retrieved evidence under the route evidence_target path family.",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "title": "GeoSeal Source Finder Terminal",
        "filters": {"family": family, "source_id": source_id, "query": query},
        "route_count": matrix["route_count"],
        "families": matrix["families"],
        "safety_tiers": matrix["safety_tiers"],
        "lanes": lanes,
        "global_policy": matrix["global_policy"],
        "next_actions": next_actions,
        "commands": {
            "all": "geoseal research-terminal",
            "machine": "geoseal research-sources --json",
            "tor": "geoseal research-terminal --family tor",
            "arxiv": "geoseal research-terminal --query arxiv",
            "news": "geoseal research-terminal --family news",
        },
    }


def render_source_terminal_text(state: dict[str, Any]) -> str:
    lines = [
        "GeoSeal Source Finder Terminal",
        "=" * 34,
        f"Routes: {state['route_count']} | Families: {len(state['families'])} | Safety tiers: {len(state['safety_tiers'])}",
    ]
    filters = {key: value for key, value in state.get("filters", {}).items() if value}
    if filters:
        lines.append("Filters: " + ", ".join(f"{key}={value}" for key, value in filters.items()))
    lines.extend(["", "Lane Board", "-" * 34])

    for lane in ["KO", "AV", "RU", "CA", "UM", "DR"]:
        routes = state.get("lanes", {}).get(lane, [])
        if not routes:
            continue
        lines.append(f"{lane}  {LANE_NAMES.get(lane, 'research lane')}")
        for route in routes:
            command = " ".join(route["default_command"])
            lines.append(
                f"  [{route['family']}] {route['source_id']} "
                f"safety={route['safety_tier']} train={route['training_status']}"
            )
            lines.append(f"    gate: {_short(route['gate'], 104)}")
            lines.append(f"    run:  {_short(command, 104)}")
            lines.append(f"    out:  {route['evidence_target']}")

    lines.extend(["", "Safety Legend", "-" * 34])
    for tier, count in sorted(state["safety_tiers"].items()):
        lines.append(f"- {tier}: {count}")

    lines.extend(["", "Operator Commands", "-" * 34])
    for label, command in state["commands"].items():
        lines.append(f"- {label}: {command}")

    lines.extend(["", "Policy", "-" * 34])
    lines.extend(f"- {note}" for note in state["global_policy"])
    lines.extend(["", "Next Actions", "-" * 34])
    lines.extend(f"- {action}" for action in state["next_actions"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", default=None)
    parser.add_argument("--source-id", default=None, dest="source_id")
    parser.add_argument("--query", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    state = build_source_terminal_state(family=args.family, source_id=args.source_id, query=args.query)
    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True))
    else:
        print(render_source_terminal_text(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
