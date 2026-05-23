from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "eval" / "aether_coding_score.v1.json"


def test_aether_coding_score_weights_sum_to_100() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert data["schema_version"] == "scbe_aether_coding_score_v1"
    assert sum(track["weight"] for track in data["tracks"]) == 100


def test_aether_coding_score_has_claim_guardrails() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    guardrails = data["claim_guardrails"]
    assert any("smoke run" in guardrail for guardrail in guardrails)
    assert any("simulated competitor" in guardrail for guardrail in guardrails)
    assert any("harness" in guardrail and "cost" in guardrail for guardrail in guardrails)


def test_aether_coding_score_tracks_are_actionable() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    for track in data["tracks"]:
        assert track["track_id"]
        assert track["weight"] > 0
        assert track["primary_benchmarks"]
        assert track["repo_status"]
        assert track["first_scbe_action"]
