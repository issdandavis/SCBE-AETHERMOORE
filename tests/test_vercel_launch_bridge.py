from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_vercel_launch_rewrites_root_and_launch_to_agent_page() -> None:
    config = json.loads((REPO_ROOT / "vercel.json").read_text(encoding="utf-8"))
    routes = {(item["src"], item["dest"]) for item in config["routes"]}

    assert {"src": "api/agent/*.js", "use": "@vercel/node"} in config["builds"]
    assert ("^/$", "/api/agent/launch.js") in routes
    assert ("^/launch$", "/api/agent/launch.js") in routes
    assert ("^/api/agent/(.*)$", "/api/agent/$1.js") in routes


def test_vercelignore_ships_launch_handler_with_api_bridge() -> None:
    ignore = (REPO_ROOT / ".vercelignore").read_text(encoding="utf-8")
    handler = REPO_ROOT / "api" / "agent" / "launch.js"

    assert handler.exists()
    assert "!api" in ignore
    assert "!api/**" in ignore


def test_launch_page_links_to_public_docs_and_bridge_endpoints() -> None:
    source = (REPO_ROOT / "api" / "agent" / "launch.js").read_text(encoding="utf-8")

    assert "/api/agent/health" in source
    assert "/api/agent/status?limit=5" in source
    assert "https://aethermoore.com/SCBE-AETHERMOORE" in source
