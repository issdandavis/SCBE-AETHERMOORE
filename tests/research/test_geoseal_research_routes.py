from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.research.geoseal_research_routes import build_research_route_matrix, render_routes_text

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_research_routes_cover_requested_rag_sources() -> None:
    matrix = build_research_route_matrix()
    source_ids = {route["source_id"] for route in matrix["routes"]}

    assert matrix["schema_version"] == "scbe_geoseal_research_routes_v1"
    assert {
        "arxiv_public",
        "scbe_github_pages_site",
        "public_news_clearnet",
        "flight_public_adsb",
        "air_traffic_radio_public",
        "starlink_public_space_telemetry",
        "public_broadcast_archives",
        "google_public_discovery",
        "tor_trusted_onion_research",
        "official_public_data_apis",
    }.issubset(source_ids)
    assert matrix["route_count"] == len(matrix["routes"])


def test_research_routes_keep_live_and_tor_sources_quarantine_first() -> None:
    matrix = build_research_route_matrix()
    routes = {route["source_id"]: route for route in matrix["routes"]}

    assert routes["tor_trusted_onion_research"]["safety_tier"] == "QUARANTINE_BY_DEFAULT"
    assert routes["tor_trusted_onion_research"]["training_status"] == "retrieval_only_until_allowed"
    assert "trusted registry only" in routes["tor_trusted_onion_research"]["gate"]
    assert routes["flight_public_adsb"]["safety_tier"] == "QUARANTINE_LIVE_OPERATIONS"
    assert routes["air_traffic_radio_public"]["safety_tier"] == "QUARANTINE_LIVE_OPERATIONS"


def test_research_route_filters_and_text_renderer() -> None:
    aviation = build_research_route_matrix(family="aviation")
    assert aviation["route_count"] == 1
    assert aviation["routes"][0]["source_id"] == "flight_public_adsb"

    starlink = build_research_route_matrix(query="starlink")
    assert starlink["route_count"] == 1
    assert starlink["routes"][0]["family"] == "space_telemetry"

    website = build_research_route_matrix(query="aethermoore")
    assert website["route_count"] == 1
    assert website["routes"][0]["source_id"] == "scbe_github_pages_site"

    tor = build_research_route_matrix(query="tor")
    assert tor["route_count"] == 1
    assert tor["routes"][0]["source_id"] == "tor_trusted_onion_research"

    text = render_routes_text(build_research_route_matrix(source_id="arxiv_public"))
    assert "GeoSeal Research Source Routes" in text
    assert "arxiv_public" in text


def test_research_routes_cli_json_output() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/research/geoseal_research_routes.py", "--family", "tor", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    matrix = json.loads(proc.stdout)
    assert matrix["route_count"] == 1
    assert matrix["routes"][0]["source_id"] == "tor_trusted_onion_research"


def test_geoseal_cli_research_sources_passthrough() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", "research-sources", "--query", "google", "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    matrix = json.loads(proc.stdout)
    assert matrix["route_count"] == 1
    assert matrix["routes"][0]["source_id"] == "google_public_discovery"
