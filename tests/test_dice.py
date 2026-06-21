"""dice: a die as a typed finite-domain choice operator -- auditable, reproducible, constrained.

These pin the doc's claims (and only those, per its claim boundary): a throw lands ONLY on a legal side,
the same seed replays the same throw, a forged/out-of-range value or tampered receipt is rejected, 0 is an
EXPLICIT zero event (never silent failure), weighting biases the draw, and a DiceLog is a replayable trace.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.dice import (  # noqa: E402
    DiceLog,
    bench,
    is_valid_side,
    replay,
    roll,
    roll_legal,
    route,
    zero_packet,
)


def test_roll_lands_only_on_a_legal_side():
    p = roll_legal(["a", "b", "c"], seed="s")
    assert p["sides"] == 3 and 1 <= p["value"] <= 3
    assert p["side_label"] in ("a", "b", "c") and is_valid_side(p)


def test_same_seed_replays_the_same_throw():
    a = roll_legal(["a", "b", "c", "d"], seed="run-1")
    b = roll_legal(["a", "b", "c", "d"], seed="run-1")
    assert a["value"] == b["value"] and a["side_label"] == b["side_label"]
    assert replay(a) is True  # re-derived from the seed + receipt intact


def test_different_seed_can_differ():
    seen = {roll_legal(["a", "b", "c", "d", "e", "f"], seed="seed-%d" % i)["value"] for i in range(12)}
    assert len(seen) > 1  # not a constant -- the seed actually drives the choice


def test_forged_out_of_range_side_is_rejected():
    p = roll_legal(["a", "b"], seed="s")
    p["value"] = 99  # claim a side that does not exist
    assert is_valid_side(p) is False and replay(p) is False


def test_tampered_receipt_is_rejected():
    p = roll_legal(["a", "b", "c"], seed="s")
    p["side_label"] = "z"  # tamper after issuance without re-sealing
    assert replay(p) is False


def test_zero_is_an_explicit_event_not_silent_failure():
    z = roll_legal([], seed="s", zero_policy="pass")  # empty legal domain
    assert z["value"] == 0 and z["zero_policy"] == "pass" and z["side_label"] == "pass"
    assert replay(z) is True  # a zero event is itself a valid, audited packet
    assert zero_packet("different_die", "s")["zero_policy"] == "different_die"


def test_route_picks_only_an_allowed_tool():
    p = route(["read_file", "list_files"], seed="s")
    assert p["role"] == "tool_choice" and p["side_label"] in ("read_file", "list_files")
    assert "legal_only" in p["constraints"]


def test_dicelog_is_a_replayable_chained_trace():
    log = DiceLog(seed="trace-1")
    log.roll_legal(["x", "y", "z"])
    log.roll_legal(["read", "write"], role="tool_choice")
    assert len(log.throws) == 2 and log.verify() is True
    log.throws[0]["value"] = 99  # break one throw
    assert log.verify() is False


def test_bench_passes_all_the_docs_checks():
    b = bench()
    assert b["deterministic_replay"] is True
    assert b["invalid_side_rejected"] is True
    assert b["zero_is_explicit"] is True
    assert b["weighted_distribution_sane"] is True
