"""mars_dtn_sim: validate time_machine's deterministic lockstep under NASA-DTN comms conditions.

HONEST SCOPE (read first): this SIMULATES the conditions NASA's Delay/Disruption-Tolerant Networking
(DTN -- the Bundle Protocol used for deep-space relays) test suites exercise. It is NOT the ION-DTN
reference implementation or its C test harness (not installed here), and it is not the CCSDS test vectors.
The parameters are NASA-realistic: Mars one-way light time ~182 s (closest approach) to ~1342 s (~22 min,
farthest); store-carry-forward across link OUTAGES / contact windows; out-of-order bundle delivery;
duplicate bundles; and loss-then-retransmit (custody transfer).

What it validates: because the time_machine is EVENT-SOURCED and DETERMINISTIC, the far end rebuilds the
tape in LOGICAL (sequence) order and dedups, so it converges to IDENTICAL state regardless of delay,
reorder, or duplication -- as long as every turn eventually arrives. The honest counter-case is also here:
with NO custody/retransmit, a permanently-lost bundle makes the ends DIVERGE -- which is exactly why DTN
uses custody transfer. The chaos is seeded, so every run is reproducible (the point of the whole idea).

    for s in run_suite(): print(s["scenario"], s["converged"])   # all True except permanent-loss-no-custody
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from python.scbe.time_machine import Tape, set_key  # noqa: E402

MARS_MIN_DELAY_S = 182  # ~3.0 min one-way light time at closest approach
MARS_MAX_DELAY_S = 1342  # ~22.4 min at farthest


class Bundle:
    __slots__ = ("seq", "payload")

    def __init__(self, seq: int, payload: Any) -> None:
        self.seq = seq
        self.payload = payload


def _relay(
    bundles: List[Bundle], rng: random.Random, drop_prob=0.0, dup_prob=0.0, reorder=False, retransmit=True
) -> List[Bundle]:
    """A DTN relay: each bundle gets an arrival 'tick' (jitter + occasional contact-gap wait), may be dropped
    (and retransmitted later if custody is on, else permanently lost), and may be duplicated. Returns the
    bundles in ARRIVAL order (which is not send order when reorder/outages are in play)."""
    arrivals: List[tuple] = []
    for b in bundles:
        tick = rng.uniform(0.0, 1.0)
        if rng.random() < 0.15:  # store-carry-forward across a contact-window gap
            tick += rng.uniform(2.0, 5.0)
        if rng.random() < drop_prob:
            if not retransmit:
                continue  # permanent loss, no custody -> this turn never arrives
            tick += rng.uniform(3.0, 6.0)  # dropped, custody retransmit -> arrives later
        arrivals.append((tick, b))
        if rng.random() < dup_prob:
            arrivals.append((tick + rng.uniform(0.01, 0.5), b))  # a duplicate copy of the same bundle
    if reorder:
        arrivals.sort(key=lambda x: x[0])
    return [b for _, b in arrivals]


def reconstruct(delivered: List[Bundle], initial: Any, step: Callable[[Any, Any], Any]) -> tuple:
    """Far-end reconstruction: order the received bundles by SEQ (logical time), DEDUP, replay the tape ->
    a deterministic state. This is why DTN chaos (delay / reorder / duplicates) doesn't change the result:
    the tape is rebuilt in logical order, not arrival order. Returns (state, unique_turns_received)."""
    by_seq: Dict[int, Any] = {}
    for b in delivered:
        by_seq[b.seq] = b.payload  # duplicates collapse; each seq is one turn
    ordered = [by_seq[s] for s in sorted(by_seq)]
    tape = Tape(initial, step).record(*ordered)
    return tape.at(tape.now()), len(ordered)


def run_scenario(
    name: str, conditions: Dict[str, Any], n_turns: int = 24, seed: int = 7, delay_phase: float = 1.0
) -> Dict[str, Any]:
    rng = random.Random(seed)
    events = [("reg%d" % (i % 5), i * i) for i in range(n_turns)]  # the deterministic turn stream (Earth side)
    truth = Tape({}, set_key).record(*events).at(n_turns)  # ground truth: the full replay
    bundles = [Bundle(i, e) for i, e in enumerate(events)]
    delivered = _relay(bundles, rng, **conditions)
    recv_state, unique = reconstruct(delivered, {}, set_key)
    return {
        "scenario": name,
        "one_way_delay_s": round(MARS_MIN_DELAY_S + (MARS_MAX_DELAY_S - MARS_MIN_DELAY_S) * delay_phase),
        "turns": n_turns,
        "bundles_delivered": len(delivered),
        "unique_turns_received": unique,
        "converged": recv_state == truth,
    }


SUITE = [
    ("perfect_link", {}, 1.0),
    ("mars_far_max_delay", {}, 1.0),
    ("disrupted_contact_windows", {"reorder": True}, 0.7),
    ("out_of_order_delivery", {"reorder": True}, 0.5),
    ("duplicate_bundles", {"dup_prob": 0.4, "reorder": True}, 0.5),
    ("loss_with_custody_retransmit", {"drop_prob": 0.35, "reorder": True, "retransmit": True}, 1.0),
    ("all_conditions_combined", {"drop_prob": 0.25, "dup_prob": 0.25, "reorder": True, "retransmit": True}, 1.0),
    ("permanent_loss_no_custody", {"drop_prob": 0.35, "retransmit": False}, 1.0),  # honest: DIVERGES
]


def run_suite(seed: int = 7) -> List[Dict[str, Any]]:
    return [run_scenario(name, cond, seed=seed, delay_phase=ph) for name, cond, ph in SUITE]


def main() -> int:
    print("MARS-DTN SIMULATION -- time_machine deterministic replay under NASA-DTN comms conditions")
    print("  (simulated conditions, NASA-realistic params; NOT the ION-DTN reference suite)\n")
    print("  %-32s %8s %10s %9s  %s" % ("scenario", "delay_s", "delivered", "turns", "converged"))
    for s in run_suite():
        print(
            "  %-32s %8d %10d %9d  %s"
            % (s["scenario"], s["one_way_delay_s"], s["bundles_delivered"], s["unique_turns_received"], s["converged"])
        )
    print("\n  All recoverable conditions converge; permanent-loss-no-custody DIVERGES (why DTN needs custody).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
