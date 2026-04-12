from __future__ import annotations

import math

import pytest

from src.ca_lexicon import LEXICON
from src.mempalace import (
    Room,
    build_palace,
    fold_walk,
    settle,
    walk_bfs,
    walk_dfs,
    zoom,
)


@pytest.fixture(scope="module")
def palace():
    return build_palace()


def test_sixty_four_rooms(palace):
    assert len(palace) == 64
    assert set(palace.keys()) == set(LEXICON.keys())


def test_four_wings(palace):
    wings = {room.wing for room in palace.values()}
    assert wings == {"ARITHMETIC", "LOGIC", "COMPARISON", "AGGREGATION"}


def test_band_chain_contiguous(palace):
    assert 0x01 in palace[0x00].corridors.get("band", [])
    assert 0x00 in palace[0x01].corridors.get("band", [])
    assert 0x0F not in palace[0x10].corridors.get("band", [])


def test_wing_gates(palace):
    assert 0x10 in palace[0x0F].corridors.get("gate", [])
    assert 0x0F in palace[0x10].corridors.get("gate", [])
    assert 0x20 in palace[0x1F].corridors.get("gate", [])
    assert 0x30 in palace[0x2F].corridors.get("gate", [])


def test_dfs_reaches_all(palace):
    visited = walk_dfs(palace, 0x00)
    assert len(visited) == 64


def test_bfs_reaches_all(palace):
    order = walk_bfs(palace, 0x00)
    assert len(order) == 64
    assert order[0] == 0x00
    assert set(order) == set(palace.keys())


def test_zoom_returns_root(palace):
    names = zoom(palace, 0x00, depth=3, fn=lambda r: r.name)
    assert len(names) > 0
    assert names[0] == palace[0x00].name


def test_zoom_depth_zero_is_singleton(palace):
    names = zoom(palace, 0x00, depth=0, fn=lambda r: r.name)
    assert names == [palace[0x00].name]


def test_settle_converges(palace):
    state = settle(palace, 0x00, iterations=1000, tol=1e-12)
    total = sum(state.values())
    assert math.isclose(total, 1.0, rel_tol=1e-6)
    assert all(v >= 0 for v in state.values())
    assert any(v > 0 for v in state.values())


def test_fold_walk_sums_chi(palace):
    total_chi = fold_walk(palace, 0x00, lambda acc, r: acc + r.entry.chi, 0.0)
    expected = sum(entry.chi for entry in LEXICON.values())
    assert math.isclose(total_chi, expected, rel_tol=1e-6)


def test_room_neighbors_excludes_self(palace):
    room = palace[0x00]
    n = room.neighbors()
    assert isinstance(n, set)
    assert 0x00 not in n
