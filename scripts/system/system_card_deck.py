from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "system-cards"
REPO_ORDERING_LATEST = REPO_ROOT / "artifacts" / "repo-ordering" / "latest.json"
WORKFLOW_AUDIT_LATEST = REPO_ROOT / "artifacts" / "system-audit" / "workflow_audit.json"

SUIT_BY_CATEGORY = {
    "canonical": ("spades", "black"),
    "subproject-local": ("spades", "black"),
    "content-publishing": ("hearts", "red"),
    "research-experimental": ("clubs", "blue"),
    "generated-runtime": ("diamonds", "gold"),
    "archive-snapshot": ("diamonds", "gold"),
    "legacy-readonly": ("diamonds", "gold"),
    "external-vendored": ("diamonds", "gold"),
    "workspace-meta": ("joker", "gray"),
    "root-file": ("clubs", "blue"),
    "unknown": ("clubs", "blue"),
}

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CATEGORY_WEIGHT = {
    "canonical": 50,
    "subproject-local": 45,
    "content-publishing": 35,
    "research-experimental": 30,
    "generated-runtime": 40,
    "legacy-readonly": 28,
    "archive-snapshot": 32,
    "external-vendored": 24,
    "root-file": 20,
    "unknown": 18,
    "workspace-meta": 10,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def priority_score(entry: dict[str, Any]) -> float:
    return (
        CATEGORY_WEIGHT.get(entry["category"], 10)
        + float(entry.get("dirty_count", 0)) * 3.0
        + float(entry.get("size_mb", 0.0)) / 8.0
    )


def build_system_cards(root_entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    jokers: list[dict[str, Any]] = []

    sorted_entries = sorted(root_entries, key=priority_score, reverse=True)
    for entry in sorted_entries:
        suit, color = SUIT_BY_CATEGORY.get(entry["category"], ("clubs", "blue"))
        card = {
            "name": entry["name"],
            "category": entry["category"],
            "suit": suit,
            "color": color,
            "score": round(priority_score(entry), 2),
            "dirty_count": entry.get("dirty_count", 0),
            "size_mb": entry.get("size_mb", 0.0),
            "recommended_action": entry.get("recommended_action"),
            "recommended_export_target": entry.get("recommended_export_target"),
            "reason": entry.get("reason"),
        }
        if suit == "joker":
            jokers.append(card)
        else:
            grouped[suit].append(card)

    deck: dict[str, list[dict[str, Any]]] = {}
    for suit, cards in grouped.items():
        ordered = []
        for index, card in enumerate(cards[: len(RANKS)]):
            ordered.append({**card, "rank": RANKS[index]})
        deck[suit] = ordered
    if jokers:
        deck["joker"] = [{**card, "rank": f"JOKER-{idx + 1}"} for idx, card in enumerate(jokers[:2])]
    return deck


def build_workflow_cards(workflows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for workflow in workflows:
        triage = workflow.get("triage", "yellow")
        cards.append(
            {
                "name": workflow["name"],
                "category": workflow.get("category", "ci"),
                "triage": triage,
                "color": {"green": "green", "yellow": "amber", "red": "red"}.get(triage, "gray"),
                "branch": workflow.get("branch", ""),
                "conclusion": workflow.get("conclusion", ""),
                "fix": workflow.get("fix"),
            }
        )
    return sorted(cards, key=lambda item: {"red": 0, "yellow": 1, "green": 2}.get(item["triage"], 3))


def markdown_report(deck: dict[str, list[dict[str, Any]]], workflow_cards: list[dict[str, Any]]) -> str:
    lines = ["# System Card Deck", "", "## Root Deck"]
    for suit in ("spades", "hearts", "clubs", "diamonds", "joker"):
        cards = deck.get(suit, [])
        if not cards:
            continue
        lines.append("")
        lines.append(f"### {suit.title()}")
        for card in cards:
            lines.append(
                f"- `{card['rank']}` {card['name']} | {card['category']} | "
                f"dirty={card['dirty_count']} | size_mb={card['size_mb']} | "
                f"{card['recommended_action']} -> {card['recommended_export_target']}"
            )

    lines.extend(["", "## Workflow Triage Cards"])
    for workflow in workflow_cards[:20]:
        lines.append(
            f"- `{workflow['triage']}` {workflow['name']} | {workflow['category']} | "
            f"{workflow['conclusion']} | {workflow.get('fix') or 'no fix note'}"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a card-deck view of the repo and workflow surfaces.")
    parser.add_argument("--repo-ordering", default=str(REPO_ORDERING_LATEST))
    parser.add_argument("--workflow-audit", default=str(WORKFLOW_AUDIT_LATEST))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_ordering = load_json(Path(args.repo_ordering))
    workflow_audit = load_json(Path(args.workflow_audit)) if Path(args.workflow_audit).exists() else []

    deck = build_system_cards(repo_ordering["root_entries"])
    workflow_cards = build_workflow_cards(workflow_audit)
    payload = {
        "generated_from": {
            "repo_ordering": str(Path(args.repo_ordering)),
            "workflow_audit": str(Path(args.workflow_audit)),
        },
        "deck": deck,
        "workflow_cards": workflow_cards,
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = ARTIFACT_DIR / "system_card_deck.json"
    md_path = ARTIFACT_DIR / "SYSTEM_CARD_DECK.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(deck, workflow_cards), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"wrote={json_path}")
        print(f"wrote={md_path}")
        for suit in ("spades", "hearts", "clubs", "diamonds", "joker"):
            print(f"{suit}={len(deck.get(suit, []))}")
        print(f"workflow_cards={len(workflow_cards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
