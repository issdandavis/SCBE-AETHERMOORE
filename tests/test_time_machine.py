"""time_machine: two ways to scrub a process in time -- (a) reversible (bijective, no log) and
(b) event-sourced (tape replay, any step). These pin the load-bearing properties: reversible time travel is
LOSSLESS (forward then rewind == the exact start), event-sourced replay is DETERMINISTIC and recovers a past
state even when the step is irreversible, and a deterministic-lockstep relay reconstructs identical state.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.time_machine import (  # noqa: E402
    Reversible,
    Tape,
    bijective_clock,
    lockstep,
    set_key,
)


def test_reversible_round_trip_is_lossless_no_log():
    # the literal "bijectivity simulates time": advance n, rewind n, land EXACTLY back -- no log kept
    for seed in (1, 42, 2**40 + 7):  # nonzero: 0 is a fixed point (see the next test)
        for n in (1, 3, 9, 25):
            clk = bijective_clock(seed=seed)
            clk.forward(n)
            assert clk.state != seed  # it actually moved
            clk.rewind(n)
            assert clk.state == seed and clk.t == 0  # exactly back, losslessly


def test_zero_is_a_fixed_point_of_the_bijective_clock():
    # an honest property of this bijection: splitmix64(0) == 0, so at seed 0 the clock is FROZEN -- forward
    # and rewind both stay at 0. Still perfectly lossless, just a point where logical time does not advance.
    clk = bijective_clock(seed=0)
    clk.forward(10)
    assert clk.state == 0
    clk.rewind(10)
    assert clk.state == 0


def test_reversible_scrub_to_any_T_is_consistent():
    clk = bijective_clock(seed=7)
    at5 = clk.to(5)
    clk.to(2)
    assert clk.to(5) == at5  # scrubbing away and back to T=5 returns the same state ("your T time")


def test_reversible_works_for_a_plain_increment():
    r = Reversible(0, lambda s: s + 1, lambda s: s - 1)
    r.forward(10)
    assert r.state == 10 and r.t == 10
    r.rewind(4)
    assert r.state == 6 and r.t == 6


def test_event_sourced_recovers_a_past_state_through_an_overwrite():
    # set_key OVERWRITES (irreversible) -> you cannot run it backward, but replay recovers any past T
    tape = Tape({}, set_key).record(("a", 1), ("b", 2), ("a", 9))
    assert tape.at(2) == {"a": 1, "b": 2}  # before 'a' was overwritten
    assert tape.at(3) == {"a": 9, "b": 2}  # after
    assert tape.at(0) == {}  # the start


def test_event_sourced_replay_is_deterministic():
    tape = Tape({}, set_key).record(("a", 1), ("a", 2), ("a", 3))
    assert tape.at(2) == tape.at(2) == {"a": 2}  # identical every replay
    assert tape.at(99) == {"a": 3}  # clamps to the end


def test_mars_deterministic_lockstep_both_ends_agree():
    out = lockstep([("x", i) for i in range(10)], {}, set_key, turns_per_frame=4)
    assert out["agree"] is True  # both ends reconstruct identical state from the same tape -- no real-time sync
    assert out["frames"] == 3 and out["turns"] == 10  # 10 turns batched into 3 frames of <=4


def test_demo_both_options_and_mars():
    from python.scbe.time_machine import demo

    d = demo()
    assert d["reversible_lossless"] is True
    assert d["event_sourced_recovers_past"] is True
    assert d["mars_lockstep_agrees"] is True
