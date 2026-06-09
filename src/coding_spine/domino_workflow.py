"""Deterministic domino workflow mechanics for agent lanes.

This module gives the CLI a token-free planning primitive: tiles connect when
one output contract touches the next input contract. On contact, dot pressure is
balanced across the touching faces. Agents can use the resulting chain as a
mechanical workflow skeleton before spending model calls.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_DOTS = {
    "intent": 1,
    "evidence": 2,
    "plan": 3,
    "patch": 4,
    "test": 5,
    "verified": 6,
    "report": 2,
    "deploy": 5,
    "sell": 6,
}


@dataclass(frozen=True)
class DominoTile:
    tile_id: str
    left: str
    right: str
    left_dots: int
    right_dots: int
    payload: str = ""
    rotated: bool = False

    def rotate(self) -> "DominoTile":
        return DominoTile(
            tile_id=self.tile_id,
            left=self.right,
            right=self.left,
            left_dots=self.right_dots,
            right_dots=self.left_dots,
            payload=self.payload,
            rotated=not self.rotated,
        )


def _default_dots(label: str) -> int:
    normalized = label.strip().lower()
    if normalized in DEFAULT_DOTS:
        return DEFAULT_DOTS[normalized]
    return max(0, min(6, (sum(ord(ch) for ch in normalized) % 7)))


def parse_tile(spec: str, index: int = 0) -> DominoTile:
    """Parse `id:left|right:2/4` or `left|right` into a tile."""
    raw = spec.strip()
    if not raw:
        raise ValueError("empty domino tile spec")
    name_part = f"tile-{index + 1}"
    body = raw
    if ":" in raw and "|" in raw.split(":", 1)[1]:
        name_part, body = raw.split(":", 1)
    elif raw.count(":") >= 2:
        name_part, body = raw.split(":", 1)

    dots_part = ""
    if ":" in body:
        body, dots_part = body.rsplit(":", 1)
    if "|" not in body:
        raise ValueError(f"domino tile must use left|right contract shape: {spec!r}")
    left, right = [part.strip().lower() for part in body.split("|", 1)]
    if not left or not right:
        raise ValueError(f"domino tile has blank side: {spec!r}")
    if dots_part:
        if "/" not in dots_part:
            raise ValueError(f"domino dots must use left/right shape: {spec!r}")
        left_raw, right_raw = dots_part.split("/", 1)
        left_dots = int(left_raw)
        right_dots = int(right_raw)
    else:
        left_dots = _default_dots(left)
        right_dots = _default_dots(right)
    return DominoTile(
        tile_id=name_part.strip() or f"tile-{index + 1}",
        left=left,
        right=right,
        left_dots=max(0, min(12, left_dots)),
        right_dots=max(0, min(12, right_dots)),
    )


def parse_tiles(specs: list[str]) -> list[DominoTile]:
    return [parse_tile(spec, index) for index, spec in enumerate(specs)]


def _balance_contact(upstream: DominoTile, downstream: DominoTile) -> tuple[DominoTile, DominoTile, dict[str, Any]]:
    if upstream.right != downstream.left:
        raise ValueError("cannot balance non-contacting domino faces")
    total = upstream.right_dots + downstream.left_dots
    new_upstream_right = (total + 1) // 2
    new_downstream_left = total // 2
    transfer = downstream.left_dots - new_downstream_left
    balanced_upstream = DominoTile(
        **{
            **asdict(upstream),
            "right_dots": new_upstream_right,
        }
    )
    balanced_downstream = DominoTile(
        **{
            **asdict(downstream),
            "left_dots": new_downstream_left,
        }
    )
    return (
        balanced_upstream,
        balanced_downstream,
        {
            "from": upstream.tile_id,
            "to": downstream.tile_id,
            "contract": upstream.right,
            "total_contact_dots": total,
            "transfer_direction": (
                "downstream_to_upstream" if transfer > 0 else "upstream_to_downstream" if transfer < 0 else "balanced"
            ),
            "transfer_amount": abs(transfer),
            "upstream_right_dots": new_upstream_right,
            "downstream_left_dots": new_downstream_left,
        },
    )


def _find_next_tile(
    current_right: str, remaining: list[DominoTile], *, allow_rotation: bool
) -> tuple[int, DominoTile] | None:
    for index, tile in enumerate(remaining):
        if tile.left == current_right:
            return index, tile
    if allow_rotation:
        for index, tile in enumerate(remaining):
            rotated = tile.rotate()
            if rotated.left == current_right:
                return index, rotated
    return None


def build_domino_workflow(
    tiles: list[DominoTile],
    *,
    start: str | None = None,
    allow_rotation: bool = True,
) -> dict[str, Any]:
    """Auto-arrange tiles into one workflow chain and report contact transfers."""
    if not tiles:
        return {
            "schema": "scbe_domino_workflow_v1",
            "chain": [],
            "contacts": [],
            "blocked": [],
            "branches": [],
            "mechanics": {
                "allow_rotation": allow_rotation,
                "dot_transfer": "balanced_contact_faces",
            },
        }
    remaining = list(tiles)
    start_index = 0
    if start:
        for index, tile in enumerate(remaining):
            if tile.tile_id == start or tile.left == start:
                start_index = index
                break
    chain = [remaining.pop(start_index)]
    contacts: list[dict[str, Any]] = []
    while remaining:
        match = _find_next_tile(chain[-1].right, remaining, allow_rotation=allow_rotation)
        if match is None:
            break
        index, next_tile = match
        remaining.pop(index)
        balanced_prev, balanced_next, contact = _balance_contact(chain[-1], next_tile)
        chain[-1] = balanced_prev
        chain.append(balanced_next)
        contacts.append(contact)

    branch_contracts: dict[str, list[str]] = {}
    for tile in tiles:
        if tile.left == tile.right:
            branch_contracts.setdefault(tile.left, []).append(tile.tile_id)
    return {
        "schema": "scbe_domino_workflow_v1",
        "chain": [asdict(tile) for tile in chain],
        "contacts": contacts,
        "blocked": [asdict(tile) for tile in remaining],
        "branches": [
            {"contract": contract, "tile_ids": tile_ids, "branch_type": "double"}
            for contract, tile_ids in sorted(branch_contracts.items())
        ],
        "mechanics": {
            "allow_rotation": allow_rotation,
            "dot_transfer": "balanced_contact_faces",
            "auto_rearrangement": "greedy_left_to_right_contract_match",
            "production_gate": "advisory_workflow_skeleton_only",
        },
        "summary": {
            "tiles": len(tiles),
            "chain_length": len(chain),
            "contacts": len(contacts),
            "blocked": len(remaining),
            "complete": len(remaining) == 0,
        },
    }


def build_domino_workflow_from_specs(
    specs: list[str],
    *,
    start: str | None = None,
    allow_rotation: bool = True,
) -> dict[str, Any]:
    return build_domino_workflow(parse_tiles(specs), start=start, allow_rotation=allow_rotation)
