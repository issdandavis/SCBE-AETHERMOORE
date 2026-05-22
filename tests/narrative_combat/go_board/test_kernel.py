"""The legality kernel is the truth layer: liberties, capture, superko, suicide, probe."""

from __future__ import annotations

import pytest

from src.narrative_combat.go_board.kernel import Board, IllegalMove


def test_single_stone_liberties_depend_on_position():
    board = Board(size=9)
    board.place(0, (4, 4))  # center
    assert board.liberties((4, 4)) == 4
    board.place(0, (0, 0))  # corner
    assert board.liberties((0, 0)) == 2
    board.place(0, (0, 4))  # edge
    assert board.liberties((0, 4)) == 3


def test_connected_group_shares_liberties():
    board = Board(size=9)
    board.place(0, (4, 4))
    board.place(0, (4, 5))
    group, libs = board.group_and_liberties((4, 4))
    assert group == {(4, 4), (4, 5)}
    assert len(libs) == 6  # two stones in open space: 3 liberties each, none shared


def test_placing_the_last_liberty_captures_the_enemy_stone():
    board = Board(size=9)
    board.place(0, (4, 4))  # lone black target
    board.place(1, (3, 4))
    board.place(1, (5, 4))
    board.place(1, (4, 3))
    assert board.at((4, 4)) == 0  # still there, one liberty left at (4, 5)
    result = board.place(1, (4, 5))  # remove the final liberty
    assert (4, 4) in result.captured
    assert board.at((4, 4)) is None


def test_suicide_is_illegal():
    board = Board(size=9)
    for pt in [(3, 4), (5, 4), (4, 3), (4, 5)]:  # white rings the center, no capture available
        board.place(1, pt)
    with pytest.raises(IllegalMove, match="suicide"):
        board.place(0, (4, 4))


def test_suicide_that_captures_is_legal():
    # A move with no liberties of its own is legal when it captures first (gains a liberty).
    board = Board.from_ascii("""
        .OX
        OXX
        XX.
        """)
    # Both white stones (0,1) and (1,0) sit in atari with their only liberty at (0,0).
    # Black plays (0,0): it captures them, so black (0,0) ends with liberties -> legal.
    result = board.place(0, (0, 0))
    assert (0, 1) in result.captured
    assert (1, 0) in result.captured
    assert board.at((0, 1)) is None


def test_positional_superko_forbids_immediate_recapture():
    # Textbook ko: white (1,1) sits in atari with its only liberty at (1,2).
    board = Board.from_ascii("""
        .XO.
        XO.O
        .XO.
        ....
        """)
    captured = board.place(0, (1, 2)).captured  # black captures white (1,1)
    assert (1, 1) in captured
    # White recapturing at (1,1) would recreate the prior whole-board position -> superko.
    with pytest.raises(IllegalMove, match="superko"):
        board.place(1, (1, 1))


def test_occupied_point_is_illegal():
    board = Board(size=9)
    board.place(0, (2, 2))
    with pytest.raises(IllegalMove, match="occupied"):
        board.place(1, (2, 2))


def test_probe_does_not_mutate_but_reports_capture():
    board = Board(size=9)
    board.place(0, (4, 4))
    board.place(1, (3, 4))
    board.place(1, (5, 4))
    board.place(1, (4, 3))
    snapshot = board.ascii()
    obs = board.probe(1, (4, 5))  # the capturing move, sampled only
    assert obs.legal
    assert (4, 4) in obs.would_capture
    assert board.ascii() == snapshot  # nothing committed
    assert board.at((4, 4)) == 0


def test_protected_stones_cannot_be_captured():
    board = Board(size=9)
    board.place(0, (4, 4))
    board.set_protected([(4, 4)])  # a treaty zone shields this stone
    board.place(1, (3, 4))
    board.place(1, (5, 4))
    board.place(1, (4, 3))
    obs = board.probe(1, (4, 5))
    assert obs.would_capture == ()  # protection prevents the capture
    board.place(1, (4, 5))
    assert board.at((4, 4)) == 0  # protected stone survives even at zero liberties


def test_score_counts_stones_and_single_owner_territory():
    board = Board(size=3)
    board.place(0, (1, 1))  # one black stone; all 8 empties border only black
    scores = board.score()
    assert scores[0] == 9  # 1 stone + 8 territory on a 3x3


def test_graph_view_lists_strings_with_liberties():
    board = Board(size=9)
    board.place(0, (4, 4))
    board.place(0, (4, 5))
    board.place(1, (0, 0))
    nodes = board.graph_view()
    assert {"player": 1, "stones": ((0, 0),), "liberties": 2} in nodes
    black = next(n for n in nodes if n["player"] == 0)
    assert black["stones"] == ((4, 4), (4, 5))
