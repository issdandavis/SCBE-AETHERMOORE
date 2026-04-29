from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.geoseal_mission_compass import build_mars_mission_compass, infer_goal_tongue

REPO_ROOT = Path(__file__).resolve().parents[1]


def _mission_payload() -> dict:
    return {
        "mission_id": "ares-smoke",
        "agent_id": "geo-01",
        "goal": "Map the terrain, code a repair solution, collect science samples, and navigate home.",
        "position": [0.05, 0.02, 0.0, 0.0, 0.0, 0.0],
        "home_position": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "terrain": [
            {
                "id": "ridge",
                "position": [0.20, 0.04, 0, 0, 0, 0],
                "hazard": 0.2,
                "difficulty": 0.4,
                "signal": 0.9,
                "slope": 0.3,
                "roughness": 0.4,
                "stratigraphy_hint": "layered outcrop",
            },
            {
                "id": "crater",
                "position": [0.50, -0.20, 0, 0, 0, 0],
                "hazard": 0.8,
                "difficulty": 0.7,
                "signal": 0.3,
                "slope": 0.8,
                "roughness": 0.9,
            },
            {
                "id": "basalt",
                "position": [0.12, 0.30, 0, 0, 0, 0],
                "hazard": 0.1,
                "difficulty": 0.3,
                "signal": 0.8,
                "resource": "sample",
                "mineral_hint": "basaltic",
            },
        ],
    }


def test_goal_tongue_inference_prioritizes_mission_language() -> None:
    assert infer_goal_tongue("code a navigation patch") == "AV"
    assert infer_goal_tongue("navigate home to base") == "CA"
    assert infer_goal_tongue("map terrain hazards") == "KO"


def test_mars_mission_compass_builds_minimap_routes_and_actions() -> None:
    packet = build_mars_mission_compass(_mission_payload())

    assert packet["version"] == "geoseal-mars-mission-compass-v1"
    assert packet["transport_packet"]["sha256"]
    assert packet["semantic_phrase"]["contract"].startswith(
        "GeoSeal is the sole mission substrate"
    )

    metric = packet["metric_payload"]
    assert metric["minimap"]["cell_count"] == 3
    assert metric["home_route"]["waypoints"] == ["current", "home"]
    assert metric["return_route"]["waypoints"][-1] == "home"
    assert "geology_tagging_from_telemetry" in metric["software_capabilities"]
    assert any(
        tool["tool"] == "navigation_camera" for tool in metric["physical_tool_manual"]
    )
    assert any(
        cell["geology"]["mineral_hint"] == "basaltic"
        for cell in metric["minimap"]["cells"]
    )
    assert len(packet["action_packets"]) == 6

    action_kinds = {p["semantic_phrase"]["kind"] for p in packet["action_packets"]}
    assert {
        "map_terrain",
        "code_solution",
        "navigate_home",
        "compress_handoff",
    } <= action_kinds
    for action in packet["action_packets"]:
        assert action["semantic_phrase"]
        assert action["metric_payload"]["tongue"]
        assert action["transport_packet"]["sha256"]


def test_mars_mission_compass_is_deterministic() -> None:
    a = build_mars_mission_compass(_mission_payload())
    b = build_mars_mission_compass(_mission_payload())
    assert a["transport_packet"]["sha256"] == b["transport_packet"]["sha256"]


def test_geoseal_cli_mars_mission_json(tmp_path: Path) -> None:
    mission = tmp_path / "mission.json"
    mission.write_text(json.dumps(_mission_payload()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "mars-mission",
            "--input",
            str(mission),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)},
    )

    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["mission_id"] == "ares-smoke"
    assert packet["metric_payload"]["minimap"]["cell_count"] == 3
