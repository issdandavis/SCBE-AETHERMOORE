"""Parity tests for python/scbe/tile_lang.py."""

from __future__ import annotations

from python.scbe.atomic_tokenization import TONGUES
from python.scbe.tile_lang import lang_at_tile, parse_tile_key, tile_key, tile_to_voxel6


def test_tile_key_roundtrip() -> None:
    assert parse_tile_key(tile_key(3, -2)) == (3, -2)
    assert parse_tile_key("nope") is None


def test_lang_at_tile_stripes() -> None:
    assert lang_at_tile(0, 0) == TONGUES[0]
    assert lang_at_tile(6, 6) == lang_at_tile(0, 0)


def test_tile_to_voxel6() -> None:
    assert tile_to_voxel6(7, 8, 2) == (7, 8, 2, 0, 0, 0)
