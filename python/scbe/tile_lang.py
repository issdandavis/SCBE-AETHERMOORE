"""2D tile grid → Sacred Tongue lane (Python parity for ``packages/kernel/src/tileLang.ts``)."""

from __future__ import annotations

from .atomic_tokenization import TONGUES

TileCoord = tuple[int, int]


def tile_key(row: int, col: int) -> str:
    """Canonical string id for logs (matches TS ``tileKey``)."""
    return f"tile:{row}:{col}"


def parse_tile_key(key: str) -> TileCoord | None:
    """Parse ``tile:r:c``; return ``None`` if malformed."""
    parts = key.strip().split(":")
    if len(parts) != 3 or parts[0] != "tile":
        return None
    try:
        return (int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def lang_at_tile(row: int, col: int) -> str:
    """Diagonal striping; same mapping as TS ``langAtTile``."""
    n = len(TONGUES)
    r = row % n
    c = col % n
    return TONGUES[(r + c) % n]


def tile_to_voxel6(row: int, col: int, layer: int = 0) -> tuple[int, int, int, int, int, int]:
    """Lift tile coordinates into the first three axes of a 6D voxel."""
    return (row, col, layer, 0, 0, 0)
