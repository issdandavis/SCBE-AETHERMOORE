#!/usr/bin/env python3
"""Pazaak-style bitboard planner for SCBE agent routing.

This is a deterministic planning primitive, not a model caller. It maps task
lanes into small bitboards and scores bounded "card" actions such as hold,
verify, focus, swap, double-team, discard, and claim-territory.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CARD_FILE = REPO_ROOT / "config" / "eval" / "agentic_pazaak_cards.v1.json"


@dataclass(frozen=True)
class TaskLane:
    lane_id: str
    value: int = 1
    risk: int = 0
    verified: bool = False
    blocked: bool = False
    context_noise: bool = False
    conflict: bool = False
    stalled: bool = False
    owner: str = ""


@dataclass(frozen=True)
class Card:
    card_id: str
    symbol: str
    name: str
    effect: str
    risk_delta: int
    value_delta: int
    best_for: tuple[str, ...]


@dataclass(frozen=True)
class Move:
    lane_id: str
    card_id: str
    card_name: str
    symbol: str
    score: float
    reason: str
    before: dict[str, Any]
    after: dict[str, Any]


def load_cards(path: Path = DEFAULT_CARD_FILE) -> list[Card]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cards = []
    for item in payload.get("cards", []):
        cards.append(
            Card(
                card_id=str(item["id"]),
                symbol=str(item["symbol"]),
                name=str(item["name"]),
                effect=str(item["effect"]),
                risk_delta=int(item.get("risk_delta", 0)),
                value_delta=int(item.get("value_delta", 0)),
                best_for=tuple(str(x) for x in item.get("best_for", [])),
            )
        )
    return cards


def load_lanes(path: Path | None) -> list[TaskLane]:
    if path is None:
        return [
            TaskLane("implementation", value=4, risk=2, context_noise=True),
            TaskLane("verification", value=5, risk=4, verified=False),
            TaskLane("docs", value=2, risk=1, verified=True),
            TaskLane("integration", value=5, risk=3, conflict=True),
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("lanes", payload if isinstance(payload, list) else [])
    return [
        TaskLane(
            lane_id=str(row.get("lane_id") or row.get("id")),
            value=int(row.get("value", 1)),
            risk=int(row.get("risk", 0)),
            verified=bool(row.get("verified", False)),
            blocked=bool(row.get("blocked", False)),
            context_noise=bool(row.get("context_noise", False)),
            conflict=bool(row.get("conflict", False)),
            stalled=bool(row.get("stalled", False)),
            owner=str(row.get("owner", "")),
        )
        for row in rows
    ]


def bitboards(lanes: list[TaskLane]) -> dict[str, int]:
    boards = {
        "high_value": 0,
        "high_risk": 0,
        "unverified": 0,
        "blocked": 0,
        "context_noise": 0,
        "conflict": 0,
        "stalled": 0,
        "owned": 0,
    }
    for idx, lane in enumerate(lanes):
        mask = 1 << idx
        if lane.value >= 4:
            boards["high_value"] |= mask
        if lane.risk >= 3:
            boards["high_risk"] |= mask
        if not lane.verified:
            boards["unverified"] |= mask
        if lane.blocked:
            boards["blocked"] |= mask
        if lane.context_noise:
            boards["context_noise"] |= mask
        if lane.conflict:
            boards["conflict"] |= mask
        if lane.stalled:
            boards["stalled"] |= mask
        if lane.owner:
            boards["owned"] |= mask
    return boards


def lane_tags(lane: TaskLane) -> set[str]:
    tags = set()
    if lane.value >= 4:
        tags.add("high_value")
    if lane.value <= 1:
        tags.add("low_value")
    if lane.risk >= 3:
        tags.add("high_risk")
    if lane.risk <= 1:
        tags.add("low_risk")
    if not lane.verified:
        tags.add("unverified")
    if lane.blocked:
        tags.add("needs_human")
    if lane.context_noise:
        tags.update({"context_noise", "repo_large"})
    if lane.conflict:
        tags.update({"file_conflict", "multi_agent", "go_influence"})
    if lane.stalled:
        tags.update({"stalled", "repeated_fail"})
    if lane.verified and lane.risk <= 1:
        tags.add("already_clean")
    return tags


def apply_card(lane: TaskLane, card: Card) -> TaskLane:
    risk = max(0, lane.risk + card.risk_delta)
    value = max(0, lane.value + card.value_delta)
    blocked = lane.blocked
    verified = lane.verified
    owner = lane.owner
    if card.card_id == "stand_hold":
        blocked = True
    elif card.card_id == "pass_continue":
        blocked = False
    elif card.card_id == "verify_minus_risk":
        verified = True
    elif card.card_id == "claim_territory" and not owner:
        owner = "assigned"
    elif card.card_id == "discard_branch":
        blocked = True
    return TaskLane(
        lane_id=lane.lane_id,
        value=value,
        risk=risk,
        verified=verified,
        blocked=blocked,
        context_noise=lane.context_noise,
        conflict=lane.conflict,
        stalled=lane.stalled,
        owner=owner,
    )


def score_card(lane: TaskLane, card: Card) -> tuple[float, str]:
    tags = lane_tags(lane)
    matches = sorted(tags.intersection(card.best_for))
    score = float(lane.value) - (0.75 * lane.risk)
    score += len(matches) * 2.0
    score += max(0, -card.risk_delta) * 1.25
    score += card.value_delta * 0.75
    if card.card_id == "double_team" and lane.risk >= 4:
        score -= 2.0
    if card.card_id == "discard_branch" and lane.value >= 4:
        score -= 4.0
    if card.card_id == "pass_continue" and not lane.verified:
        score -= 3.0
    reason = "matched " + ", ".join(matches) if matches else "general fit"
    return round(score, 3), reason


def recommend_moves(lanes: list[TaskLane], cards: list[Card], limit: int = 5) -> list[Move]:
    moves: list[Move] = []
    for lane in lanes:
        for card in cards:
            score, reason = score_card(lane, card)
            after = apply_card(lane, card)
            moves.append(
                Move(
                    lane_id=lane.lane_id,
                    card_id=card.card_id,
                    card_name=card.name,
                    symbol=card.symbol,
                    score=score,
                    reason=reason,
                    before=asdict(lane),
                    after=asdict(after),
                )
            )
    return sorted(moves, key=lambda move: (-move.score, move.lane_id, move.card_id))[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", type=Path, default=None, help="Optional JSON list or {'lanes': [...]} file.")
    parser.add_argument("--cards", type=Path, default=DEFAULT_CARD_FILE)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    lanes = load_lanes(args.lanes)
    cards = load_cards(args.cards)
    payload = {
        "schema": "scbe_agentic_pazaak_board_report_v1",
        "lane_count": len(lanes),
        "bitboards": bitboards(lanes),
        "moves": [asdict(move) for move in recommend_moves(lanes, cards, limit=args.limit)],
    }
    text = json.dumps(payload, indent=2, ensure_ascii=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
