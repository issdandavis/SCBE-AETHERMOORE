"""The director drives the board and emits verifiable, deterministic, board-true turns."""

from __future__ import annotations

from src.narrative_combat.go_board.director import GoDirector
from src.narrative_combat.go_board.fixtures import boss_board_demo


def _fight(seed: int) -> dict:
    return GoDirector(boss_board_demo(seed=seed)).run()


def test_packet_shape_and_per_turn_fields():
    fight = _fight(1337)
    assert fight["schema"] == "scbe.narrative_combat.go_fight.v1"
    assert fight["board_size"] == 9
    assert fight["turns"]
    for turn in fight["turns"]:
        assert {"turn_id", "phase", "party", "board_event", "mechanical", "prose", "verifier"} <= set(turn)
        assert turn["prose"]
        assert turn["verifier"]["claim"]


def test_phase_sequence_follows_the_machine():
    fight = _fight(1337)
    phases = [t["phase"] for t in fight["turns"]]
    assert phases[0] == "opening"
    assert "cost_unavoidable" in phases
    assert phases[-1] == "understanding_wins"


def test_atari_turn_reports_a_single_remaining_liberty():
    fight = _fight(1337)
    atari = next(t for t in fight["turns"] if t["board_event"] == "atari")
    assert atari["mechanical"]["target_liberties"] == 1


def test_probe_turn_does_not_commit_but_shows_the_capture():
    fight = _fight(1337)
    probe = next(t for t in fight["turns"] if t["board_event"] == "probe")
    assert probe["mechanical"]["committed"] is False
    assert probe["mechanical"]["would_capture"] == [[2, 2]]


def test_qi_claim_and_study_are_present_and_audited():
    fight = _fight(1337)
    qi = next(t for t in fight["turns"] if t["board_event"] == "qi_claimed")
    assert qi["mechanical"]["qi_gained"] == 3
    study = next(t for t in fight["turns"] if t["board_event"] == "study_revealed")
    assert study["mechanical"]["committed"] is False
    assert fight["study_audit"] and fight["study_audit"][0]["decision"] == "allow"


def test_fight_is_deterministic_for_a_seed():
    assert _fight(1337) == _fight(1337)


def test_both_endings_are_reachable_and_truthful():
    endings = {}
    for seed in range(40):
        fight = _fight(seed)
        endings.setdefault(fight["aftermath"]["ending"], fight)
        if {"capture", "treaty"} <= set(endings):
            break
    assert {"capture", "treaty"} <= set(endings), "expected both a capture and a treaty across seeds"

    capture = endings["capture"]
    # the captured stone is actually gone from the final board (row 2 of a 9-wide board)
    assert capture["final_board"].splitlines()[2][2] == "."
    assert sum(capture["aftermath"]["captures"].values()) >= 1

    treaty = endings["treaty"]
    assert treaty["aftermath"]["treaty_zone"] is not None
    assert treaty["final_board"].splitlines()[2][2] != "."  # protected stone survives
