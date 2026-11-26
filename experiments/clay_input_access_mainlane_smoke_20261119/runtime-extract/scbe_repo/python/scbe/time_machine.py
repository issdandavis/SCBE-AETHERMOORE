"""time_machine: scrub a process in time, two ways -- "bijectivity simulates time" (Issac's idea).

If a process loses no information you can rewind it and re-forward it -- "your T time" for niche ops, and
for long-form / high-latency work (Mars relays) you run deterministic turn cycles and exchange only the
log, never real-time state. Two OPTIONS, and the honest split between them:

  (a) REVERSIBLE -- every step is a bijection with an inverse, so rewind = apply the inverse. NO log
      needed; true bidirectional time. The step here is literally the bijective hash
      (splitmix64 <-> splitmix64_inverse). LIMIT: only works if every step is reversible -- no overwrite /
      many-to-one ops, which destroy the information you'd need to run backward.
  (b) EVENT-SOURCED -- keep the initial state + a log (tape) of events. at(T) replays the tape to logical
      time T; rewind = replay to an earlier T, re-forward = replay to a later one. Works for ANY process,
      even irreversible steps. LIMIT: you must store the tape.

Mars / long-form: because both are DETERMINISTIC, you don't need real-time round-trips at 3-22 min latency.
Each side runs the same turn engine, accrues a bounded number of turns per time-frame (the "time cycle"),
and exchanges only the tape -- both ends reconstruct identical state (deterministic lockstep; the latency is
absorbed into turn-batching). Same seeded-determinism as DiceLog / game_task's sealed record / board.py's
reversible stone-record.

    clk = bijective_clock(seed=42); clk.forward(5); clk.rewind(5)   # (a) back to 42, NO log -- lossless
    tape = Tape({}, set_key).record(("a", 1), ("a", 9)); tape.at(1)  # (b) {"a": 1} -- the state before the overwrite
"""

from __future__ import annotations

from typing import Any, Callable, List, Tuple

from .elastic_bijective_hash import splitmix64, splitmix64_inverse

# --- (a) REVERSIBLE: bijective steps, rewind by inverse, NO log -------------------------------------


class Reversible:
    """A process whose step is a bijection (forward) with a known inverse (backward). You can move freely in
    time -- forward(n), rewind(n), or to(T) -- because no information is lost. No log is kept."""

    def __init__(self, state: Any, forward: Callable[[Any], Any], backward: Callable[[Any], Any]) -> None:
        self.state = state
        self._fwd = forward
        self._bwd = backward
        self.t = 0

    def forward(self, n: int = 1) -> Any:
        for _ in range(n):
            self.state = self._fwd(self.state)
            self.t += 1
        return self.state

    def rewind(self, n: int = 1) -> Any:
        for _ in range(n):
            self.state = self._bwd(self.state)
            self.t -= 1
        return self.state

    def to(self, target_t: int) -> Any:
        """Scrub to logical time `target_t` -- forward or back as needed. 'Your T time.'"""
        while self.t < target_t:
            self.forward()
        while self.t > target_t:
            self.rewind()
        return self.state


def bijective_clock(seed: int = 0) -> Reversible:
    """A Reversible driven by the bijective hash itself: forward = splitmix64, backward = its inverse. The
    literal 'bijectivity simulates time' -- step forward and back along the same orbit, losslessly."""
    return Reversible(seed, splitmix64, splitmix64_inverse)


# --- (b) EVENT-SOURCED: a tape you replay to any T, works for ANY step (even irreversible) ----------


def _copy(s: Any) -> Any:
    if isinstance(s, dict):
        return dict(s)
    if isinstance(s, list):
        return list(s)
    return s


class Tape:
    """A process as initial-state + a recorded LOG of events. at(T) deterministically replays the log to
    logical time T -- so you can rewind (replay to an earlier T) and re-forward (a later T) even when the
    step is IRREVERSIBLE (an overwrite, a set), because you always rebuild from the start."""

    def __init__(self, initial: Any, step: Callable[[Any, Any], Any]) -> None:
        self.initial = initial
        self.step = step
        self.events: List[Any] = []

    def record(self, *events: Any) -> "Tape":
        self.events.extend(events)
        return self

    def now(self) -> int:
        return len(self.events)

    def at(self, t: int) -> Any:
        """The exact state at logical time t (deterministic; identical every call)."""
        t = max(0, min(t, len(self.events)))
        s = _copy(self.initial)
        for e in self.events[:t]:
            s = self.step(s, e)
        return s

    def rewind_to(self, t: int) -> Any:
        return self.at(t)

    def reforward_to(self, t: int) -> Any:
        return self.at(t)


def set_key(state: dict, event: Tuple[Any, Any]) -> dict:
    """An IRREVERSIBLE step (overwrites a key) -- the case that proves (b) needs the log: you cannot run it
    backward, but you can replay to recover any past state."""
    out = dict(state)
    out[event[0]] = event[1]
    return out


# --- Mars / long-form: deterministic lockstep over a relay ------------------------------------------


def lockstep(events: List[Any], initial: Any, step: Callable[[Any, Any], Any], turns_per_frame: int = 4) -> dict:
    """Both ends of a high-latency relay reconstruct IDENTICAL state from the same tape -- no real-time sync.
    Events are batched into frames of <= turns_per_frame (the 'time cycle' / turn budget). Each end just
    replays the tape; you exchange the tape (small), not the state. Returns the agreed state + frame count."""
    end_a = Tape(_copy(initial), step).record(*events)
    end_b = Tape(_copy(initial), step).record(*events)  # the other end received the same tape across the relay
    frames = [events[i : i + turns_per_frame] for i in range(0, len(events), turns_per_frame)]
    sa, sb = end_a.at(end_a.now()), end_b.at(end_b.now())
    return {"agree": sa == sb, "state": sa, "frames": len(frames), "turns": len(events)}


def demo() -> dict:
    # (a) reversible: the bijective hash as a clock -- advance 5, rewind 5, land EXACTLY back (no log)
    clk = bijective_clock(seed=42)
    start = clk.state
    clk.forward(5)
    advanced = clk.state
    clk.rewind(5)
    reversible_lossless = clk.state == start and advanced != start

    # (b) event-sourced: a key-value store with an OVERWRITE (irreversible) -- replay recovers the past
    tape = Tape({}, set_key).record(("a", 1), ("b", 2), ("a", 9))
    before_overwrite = tape.at(2) == {"a": 1, "b": 2}  # the state before 'a' was overwritten to 9
    after = tape.at(3) == {"a": 9, "b": 2}
    deterministic = tape.at(2) == tape.at(2)  # identical every replay

    # Mars: two ends reconstruct identical state from the same tape, batched into time-frames
    mars = lockstep([("x", i) for i in range(10)], {}, set_key, turns_per_frame=4)

    return {
        "reversible_lossless": reversible_lossless,
        "event_sourced_recovers_past": before_overwrite and after and deterministic,
        "mars_lockstep_agrees": mars["agree"],
        "mars_frames": mars["frames"],
    }


def main() -> int:
    d = demo()
    print("TIME MACHINE -- two ways to scrub a process in time")
    print("  (a) reversible (bijective hash, NO log): forward 5, rewind 5, lossless == %s" % d["reversible_lossless"])
    print(
        "  (b) event-sourced (tape replay, any step): recovers pre-overwrite past == %s"
        % d["event_sourced_recovers_past"]
    )
    print(
        "  Mars deterministic lockstep: both ends agree from the tape == %s  (%d frames)"
        % (d["mars_lockstep_agrees"], d["mars_frames"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
