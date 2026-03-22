from __future__ import annotations

from scripts.system.system_card_deck import build_system_cards, build_workflow_cards


def test_build_system_cards_assigns_standard_ranks():
    root_entries = [
        {
            "name": "src",
            "category": "canonical",
            "dirty_count": 10,
            "size_mb": 20.0,
            "recommended_action": "keep-active",
            "recommended_export_target": "github-monorepo",
            "reason": "core",
        },
        {
            "name": "docs",
            "category": "content-publishing",
            "dirty_count": 5,
            "size_mb": 5.0,
            "recommended_action": "keep-and-publish",
            "recommended_export_target": "github-monorepo",
            "reason": "docs",
        },
        {
            "name": "artifacts",
            "category": "generated-runtime",
            "dirty_count": 20,
            "size_mb": 200.0,
            "recommended_action": "export-and-ignore",
            "recommended_export_target": "cloud-archive",
            "reason": "generated",
        },
    ]

    deck = build_system_cards(root_entries)

    assert deck["spades"][0]["rank"] == "A"
    assert deck["spades"][0]["name"] == "src"
    assert deck["hearts"][0]["rank"] == "A"
    assert deck["diamonds"][0]["name"] == "artifacts"


def test_build_workflow_cards_sorts_red_first():
    workflows = [
        {"name": "ci", "category": "ci", "triage": "yellow", "conclusion": "failure", "fix": "inspect"},
        {"name": "codeql", "category": "security", "triage": "green", "conclusion": "success", "fix": None},
        {"name": "kindle-build", "category": "deploy", "triage": "red", "conclusion": "failure", "fix": "chmod gradlew"},
    ]

    cards = build_workflow_cards(workflows)

    assert cards[0]["name"] == "kindle-build"
    assert cards[0]["color"] == "red"
