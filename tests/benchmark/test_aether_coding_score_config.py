from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "eval" / "aether_coding_score.v1.json"
CLAIM_REGISTRY = ROOT / "config" / "eval" / "aether_research_claim_registry.v1.json"


def test_aether_coding_score_weights_sum_to_100() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert data["schema_version"] == "scbe_aether_coding_score_v1"
    assert sum(track["weight"] for track in data["tracks"]) == 100


def test_aether_coding_score_has_claim_guardrails() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    guardrails = data["claim_guardrails"]
    assert any("smoke run" in guardrail for guardrail in guardrails)
    assert any("simulated competitor" in guardrail for guardrail in guardrails)
    assert any(
        "harness" in guardrail and "cost" in guardrail for guardrail in guardrails
    )


def test_aether_coding_score_tracks_are_actionable() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    for track in data["tracks"]:
        assert track["track_id"]
        assert track["weight"] > 0
        assert track["primary_benchmarks"]
        assert track["repo_status"]
        assert track["first_scbe_action"]


def test_aether_coding_score_points_to_claim_registry() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    registry_path = ROOT / data["research_claim_registry"]
    assert registry_path == CLAIM_REGISTRY
    assert registry_path.exists()


def test_research_claim_registry_has_status_fences() -> None:
    data = json.loads(CLAIM_REGISTRY.read_text(encoding="utf-8"))

    assert data["schema_version"] == "aether_research_claim_registry_v1"
    statuses = {claim["status"] for claim in data["claims"]}
    assert {"verified", "watch", "reject_for_public_claims"}.issubset(statuses)

    for claim in data["claims"]:
        assert claim["claim_id"]
        assert claim["area"]
        assert claim["status"] in data["status_levels"]
        assert claim["claim"]
        assert claim["repo_action"]
        assert claim["public_language"]


def test_research_claim_registry_blocks_unsupported_public_claims() -> None:
    data = json.loads(CLAIM_REGISTRY.read_text(encoding="utf-8"))

    rejected = {
        claim["claim_id"]: claim
        for claim in data["claims"]
        if claim["status"] == "reject_for_public_claims"
    }
    assert "first_ai_programmer_index" in rejected
    assert "gated_kertos_model" in rejected
    assert all(not claim["source_url"] for claim in rejected.values())


def test_watch_claims_are_not_marked_verified() -> None:
    data = json.loads(CLAIM_REGISTRY.read_text(encoding="utf-8"))

    watch = {
        claim["claim_id"]: claim
        for claim in data["claims"]
        if claim["status"] == "watch"
    }
    assert "frontier_model_escape_april_2026" in watch
    assert "aethelgard_dynamic_capability_governance" in watch
