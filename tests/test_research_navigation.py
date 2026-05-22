from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.research_navigation import (
    build_research_evidence_packet,
    build_youtube_navigation_packet,
    extract_youtube_video_id,
)

ROOT = Path(__file__).resolve().parents[1]


def test_research_evidence_packet_extracts_title_links_and_security() -> None:
    content = """
    <html>
      <head><title>Useful Source</title></head>
      <body>
        <p>This page explains a stable research workflow.</p>
        <a href="/paper">Paper</a>
      </body>
    </html>
    """
    packet = build_research_evidence_packet(url="https://example.com/root", content=content, fetch=False)
    payload = packet.to_dict()

    assert payload["schema_version"] == "scbe-research-evidence-v1"
    assert payload["title"] == "Useful Source"
    assert "stable research workflow" in payload["text_excerpt"]
    assert payload["links"][0]["href"] == "https://example.com/paper"
    assert payload["metrics"]["link_count"] == 1
    assert "governance_decision" in payload["security"]


def test_extract_youtube_video_id_from_watch_and_short_urls() -> None:
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ?si=abc") == "dQw4w9WgXcQ"
    assert extract_youtube_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_youtube_navigation_packet_can_be_metadata_only() -> None:
    payload = build_youtube_navigation_packet(target="https://youtu.be/dQw4w9WgXcQ", fetch_metadata=False)

    assert payload["schema_version"] == "scbe-youtube-navigation-v1"
    assert payload["video_id"] == "dQw4w9WgXcQ"
    assert payload["canonical_url"].endswith("v=dQw4w9WgXcQ")
    assert payload["transcript"]["requested"] is False
    assert payload["metrics"]["source_count"] == 1


def test_research_nav_cli_outputs_json_from_inline_content() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "research-nav",
            "--url",
            "https://example.com/root",
            "--content",
            "<title>Inline Evidence</title><a href='/x'>x</a>",
            "--no-fetch",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["title"] == "Inline Evidence"
    assert payload["links"][0]["href"] == "https://example.com/x"


def test_youtube_nav_cli_outputs_json_without_network_by_default() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "youtube-nav",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["video_id"] == "dQw4w9WgXcQ"
    assert payload["transcript"]["requested"] is False
