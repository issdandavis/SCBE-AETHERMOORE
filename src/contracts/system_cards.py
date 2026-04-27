"""Bounded system-card deck helpers for GeoSeal runtime routes."""

from __future__ import annotations

from typing import Any


def build_system_deck(
    resolution: dict[str, Any],
    *,
    source_text: str | None = None,
    source_name: str | None = None,
    include_extended: bool | None = None,
    deck_size: int | None = None,
    max_cards: int | None = None,
) -> dict[str, Any]:
    runtime_packet = resolution["runtime_packet"]
    limit = max(1, min(int(deck_size or max_cards or 10), 32))
    cards = [
        {
            "card_id": f"anchor:{runtime_packet['command_key']}",
            "kind": "anchor",
            "title": f"Route {runtime_packet['command_key']} through {runtime_packet['route_tongue']}",
            "route_tongue": runtime_packet["route_tongue"],
            "command_key": runtime_packet["command_key"],
        },
        {
            "card_id": "verify:tokenizer",
            "kind": "verification",
            "title": "Verify tokenizer and runtime packet boundaries",
            "route_tongue": runtime_packet["route_tongue"],
            "command_key": runtime_packet["command_key"],
        },
        {
            "card_id": "execute:route",
            "kind": "execution",
            "title": "Execute route under GeoSeal gate",
            "route_tongue": runtime_packet["route_tongue"],
            "command_key": runtime_packet["command_key"],
        },
    ][:limit]
    return {
        "schema_version": "geoseal-system-deck-v1",
        "resolution": resolution,
        "source_name": source_name or runtime_packet.get("source_name", "<memory>"),
        "source_preview": (source_text or "")[:240],
        "cards": cards,
        "include_extended": bool(include_extended if include_extended is not None else resolution.get("include_extended")),
    }


def play_system_card(deck: dict[str, Any], card: str) -> dict[str, Any]:
    for item in deck.get("cards", []):
        if item.get("card_id") == card or item.get("kind") == card or item.get("command_key") == card:
            return {"ok": True, "card": item}
    raise ValueError(f"unknown system card: {card}")
