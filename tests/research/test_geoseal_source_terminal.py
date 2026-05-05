from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.research.geoseal_source_terminal import build_source_terminal_state, render_source_terminal_text

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_source_terminal_groups_routes_by_lane() -> None:
    state = build_source_terminal_state()

    assert state["schema_version"] == "scbe_geoseal_source_terminal_v1"
    assert state["route_count"] >= 9
    assert {"KO", "RU", "CA", "UM", "DR"}.issubset(set(state["lanes"]))
    assert state["commands"]["machine"] == "geoseal research-sources --json"


def test_source_terminal_text_is_human_readable() -> None:
    text = render_source_terminal_text(build_source_terminal_state(query="tor"))

    assert "GeoSeal Source Finder Terminal" in text
    assert "Lane Board" in text
    assert "QUARANTINE_BY_DEFAULT" in text
    assert "geoseal research-terminal --family tor" in text


def test_geoseal_cli_research_terminal_json() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", "research-terminal", "--query", "starlink", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_geoseal_source_terminal_v1"
    assert payload["route_count"] == 1
    assert "CA" in payload["lanes"]


def test_node_geoseal_doctor_advertises_research_terminal() -> None:
    proc = subprocess.run(
        ["node", str(REPO_ROOT / "bin" / "geoseal.cjs"), "doctor", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "research-terminal" in payload["advertised_commands"]
    assert "research-sources" in payload["advertised_commands"]
    assert "polymarket" in payload["advertised_commands"]
