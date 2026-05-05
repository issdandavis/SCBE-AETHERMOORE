from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.research import polymarket_public_api
from scripts.research.polymarket_public_api import PolymarketRequest, build_polymarket_packet

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_polymarket_route_packet_is_read_only() -> None:
    packet = build_polymarket_packet(PolymarketRequest(mode="search", query="election", limit=250, live=False))

    assert packet["schema_version"] == "scbe_polymarket_public_packet_v1"
    assert packet["mode"] == "search"
    assert packet["request"]["limit"] == 100
    assert packet["source"]["source_id"] == "polymarket_public_prediction_markets"
    assert packet["safety"]["tier"] == "READ_ONLY_NO_TRADING"
    assert "https://gamma-api.polymarket.com/public-search" in packet["url"]
    assert "q=election" in packet["url"]
    assert "authenticated trading" in packet["source"]["blocked"]


def test_polymarket_midpoint_requires_token_id() -> None:
    with pytest.raises(ValueError, match="token_id is required"):
        build_polymarket_packet(PolymarketRequest(mode="midpoint"))


def test_polymarket_cli_passthrough_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "polymarket",
            "--mode",
            "search",
            "--query",
            "ai",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    packet = json.loads(proc.stdout)
    assert packet["mode"] == "search"
    assert packet["request"]["query"] == "ai"
    assert packet["safety"]["tier"] == "READ_ONLY_NO_TRADING"


def test_live_search_preview_compacts_nested_events(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = {
        "events": [
            {
                "id": "event-1",
                "slug": "sample-event",
                "title": "Sample event",
                "description": "large text should not be copied into preview",
                "tags": [{"id": "1", "label": "AI", "slug": "ai", "extra": "drop"}],
                "markets": [
                    {
                        "id": "market-1",
                        "slug": "sample-market",
                        "question": "Will this compact?",
                        "description": "large market text should not be copied",
                        "bestBid": 0.4,
                        "bestAsk": 0.42,
                        "clobTokenIds": '["1", "2"]',
                    }
                ],
            }
        ],
        "pagination": {"totalResults": 1},
    }

    monkeypatch.setattr(polymarket_public_api, "_fetch_json", lambda url, timeout: sample)
    packet = build_polymarket_packet(PolymarketRequest(mode="search", query="ai", live=True, limit=1))

    event = packet["data"]["events"][0]
    market = event["markets"][0]
    assert "description" not in event
    assert "description" not in market
    assert event["tags"] == [{"id": "1", "label": "AI", "slug": "ai"}]
    assert market["question"] == "Will this compact?"
