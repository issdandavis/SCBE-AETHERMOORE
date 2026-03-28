from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "web_research_training_pipeline.py"
    spec = importlib.util.spec_from_file_location("web_research_training_pipeline", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_rss_items_extracts_links():
    mod = _load_module()
    xml = b"""<?xml version='1.0'?>
    <rss><channel>
      <item><title>A</title><link>https://example.com/a</link><pubDate>t1</pubDate></item>
      <item><title>B</title><link>https://example.com/b</link><pubDate>t2</pubDate></item>
    </channel></rss>
    """
    rows = mod.parse_rss_items(xml, topic="space ai", limit=5)
    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/a"
    assert rows[1]["topic"] == "space ai"


def test_build_training_rows_routes_allow_and_quarantine():
    mod = _load_module()
    payload = {
        "results": [
            {
                "url": "https://example.com/allow",
                "decision": "ALLOW",
                "content": {"preview": "clean content", "sha256": "abc", "length": 320},
                "threat_scan": {"verdict": "CLEAN", "risk_score": 0.05},
                "matrix": {"decision": {"confidence": 0.87}},
            },
            {
                "url": "https://example.com/deny",
                "decision": "DENY",
                "content": {"preview": "bad content", "sha256": "def", "length": 100},
                "threat_scan": {"verdict": "MALICIOUS", "risk_score": 0.92},
                "matrix": {"decision": {"confidence": 0.99}},
            },
        ]
    }
    allowed, quarantined = mod.build_training_rows(payload, run_id="r1", topics=["space"])
    assert len(allowed) == 1
    assert len(quarantined) == 1
    assert allowed[0]["source_url"] == "https://example.com/allow"
    assert quarantined[0]["source_url"] == "https://example.com/deny"


def test_choose_action_quarantines_on_failed_core_health():
    mod = _load_module()
    action, reason, conf = mod.choose_action(
        allowed_count=12,
        quarantined_count=2,
        audit_status="ALLOW",
        core_health_passed=False,
    )
    assert action == "QUARANTINE"
    assert "core health" in reason
    assert 0.0 <= conf <= 1.0
