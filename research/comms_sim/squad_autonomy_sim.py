"""squad_autonomy_sim: the coding role-squad as a LONG-RANGE-AUTONOMOUS multi-agent mechanism.

Convergence of three lanes built this session:
  * coding_squad        -- the clone-trooper role squad that solves a coding_board (CSP)
  * mars_dtn_sim        -- NASA Delay/Disruption-Tolerant-Networking conditions (Mars one-way light time
                           ~182-1342 s, store-carry-forward across outages, reorder, duplicates, loss)
  * observer_dynamics   -- the all-at-once CBJ jump-back (a late-arriving decision repairs an earlier one)

THE MECHANISM. An autonomous squad on Mars solves the board LOCALLY (no live Earth control -- the round
trip is up to ~22 min). Each committed decision is emitted as a DTN bundle stamped with its LOGICAL
sequence. Bundles cross the link under delay / reorder / duplication / loss. The far end (mission control,
or a peer squad) REBUILDS the solved board by ordering on sequence, de-duplicating, and replaying.

WHY IT CONVERGES. The squad's solve is deterministic and EVENT-SOURCED (the decision records ARE the
events -- verified byte-reproducible by the determinism benchmark + scan). So the far end reconstructs the
IDENTICAL board regardless of comms chaos, as long as every bundle eventually arrives. A late corrective
decision (the CBJ jump-back / uncompute repairing a conflict that only surfaced after delay) simply carries
a higher sequence number, so replay lands on the repaired state -- autonomy + delayed repair, no live
coordination needed.

HONEST COUNTER-CASE (kept, not hidden): with permanent bundle loss and NO custody/retransmit, a lost
decision can never be replayed, so the ends DIVERGE -- which is exactly why DTN uses custody transfer. The
chaos is seeded, so every run is reproducible.

GROUNDED IN ISSAC'S DOCS (MarsProfile below; honest sourcing): the Mars one-way light time (14 min) and the
42-min-3-round-trip vs 0-min pre-synchronized handshake come from demo/mars-communication.html; the NASA
182-1342 s OWLT range from research/comms_sim/mars_dtn_sim.py. A doc sweep found the other Mars docs
(GEOSEAL mission compass, nested-drone spec, offline bundle profiles) are vision/qualitative with NO
numeric DTN parameters -- so link loss / reorder / contact-window rates honestly stay sim defaults, not
fabricated doc numbers (see DOC_SOURCES). The documented autonomy payoff: a pre-synchronized squad's
time-to-first-decision is 0 min vs 42 min for a round-trip-dependent protocol.

    PYTHONPATH=. python research/comms_sim/squad_autonomy_sim.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (str(_REPO), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import mars_dtn_sim as dtn  # noqa: E402  (sibling: the DTN relay model)

from python.scbe.coding_board import Board, Operator, region_must_agree  # noqa: E402
from python.scbe.coding_board_gates import TRANSFORM, gate_names  # noqa: E402
from python.scbe.coding_squad import solve_with_squad  # noqa: E402

Decision = Tuple[str, str]  # (operator_id, operation)


@dataclass(frozen=True)
class MarsProfile:
    """Mars-delay parameters GROUNDED in Issac's own docs (honest per-field sourcing). A doc-grounding
    sweep over config/offline_bundle_profiles.json, docs/specs/GEOSEAL_MARS_MISSION_COMPASS_v1.md, and
    docs/research/mars_nested_drone_architecture_spec.md found those are vision/qualitative with NO numeric
    DTN parameters; the only documented numbers come from demo/mars-communication.html and the existing
    mars_dtn_sim. HONEST GAP: link loss / duplicate / reorder / contact-window rates are in NO doc, so the
    scenarios keep mars_dtn_sim's sim defaults for those (flagged in DOC_SOURCES below)."""

    owlt_typical_s: float = 14 * 60  # demo/mars-communication.html: 14 min one-way light delay
    owlt_min_s: float = 182  # mars_dtn_sim (NASA): closest approach (~3.0 min)
    owlt_max_s: float = 1342  # mars_dtn_sim (NASA): farthest (~22.4 min)
    handshake_round_trips: int = 3  # demo: TLS needs 3 round trips before it can encrypt
    squad_handshake_minutes: float = 0.0  # demo: SCBE pre-synchronized vocabulary -> 0 round trips
    presync_codebook: str = "6 tongues x 256 tokens"  # demo: the pre-shared vocabulary that removes handshake


MARS = MarsProfile()
DOC_SOURCES = {
    "owlt_typical_s": "demo/mars-communication.html (14 min OWLT)",
    "owlt_min_s / owlt_max_s": "research/comms_sim/mars_dtn_sim.py (NASA 182/1342 s)",
    "handshake_round_trips / squad_handshake": "demo/mars-communication.html (42 min 3-RT vs 0 min pre-sync)",
    "loss / dup / reorder / contact_gap rates": "NOT IN ANY DOC -> mars_dtn_sim sim defaults (honest gap)",
}


def time_to_first_decision_min(pre_synchronized: bool, profile: MarsProfile = MARS) -> float:
    """The autonomy payoff, grounded in the demo's documented handshake numbers: a round-trip-dependent
    protocol cannot even START encrypting/acting for handshake_round_trips x OWLT (=42 min at 14-min OWLT);
    a PRE-SYNCHRONIZED squad (shared board + role gate-alphabet, like the demo's pre-shared vocabulary)
    starts at 0 -- it solves locally now and ships the result. This is the documented autonomy advantage."""
    if pre_synchronized:
        return profile.squad_handshake_minutes
    return profile.handshake_round_trips * (profile.owlt_typical_s / 60.0)


def _pipeline_board(n: int = 6) -> Board:
    """A coding 'pipeline' the squad must solve: two interface regions whose members must agree."""
    ops = []
    for i in range(n):
        region = "iface_a" if i % 2 == 0 else "iface_b"
        ops.append(Operator("slot%d" % i, gate_names(TRANSFORM), region=region))
    return Board(ops, [region_must_agree])


def squad_decisions(board: Board) -> Tuple[List[Tuple[int, Decision]], Dict[str, str]]:
    """Solve the board with the squad LOCALLY; emit each committed (operator -> operation) as a logical-seq
    event. The squad's repair (CBJ jump-back) is already applied, so these are the FINAL decisions."""
    res = solve_with_squad(board)
    events = [(i, (op.id, res.assignment[op.id])) for i, op in enumerate(board.operators) if op.id in res.assignment]
    return events, dict(res.assignment)


def reconstruct_assignment(delivered: List["dtn.Bundle"]) -> Dict[str, str]:
    """Far-end rebuild: order received bundles by SEQ (logical time), de-dup, replay -> the assignment.
    A later-seq corrective decision overwrites an earlier one (delayed repair lands correctly)."""
    out: Dict[str, str] = {}
    for b in sorted(delivered, key=lambda x: x.seq):
        op_id, operation = b.payload
        out[op_id] = operation  # higher seq seen later overwrites; dedup is implicit (same seq, same value)
    return out


def run_link(
    board: Board, conditions: Dict[str, Any], *, seed: int = 7, extra: List[Tuple[int, Decision]] = None
) -> Dict[str, Any]:
    """Solve locally, ship the decisions over a DTN link under `conditions`, rebuild at the far end, and
    report whether the far end CONVERGED to the locally-solved board. `extra` injects late corrective
    bundles (e.g. a CBJ repair that surfaced after delay)."""
    events, local = squad_decisions(board)
    for ev in extra or []:
        events.append(ev)
        local[ev[1][0]] = ev[1][1]  # the corrective decision is the intended final state
    bundles = [dtn.Bundle(seq, ev) for seq, ev in events]
    delivered = dtn._relay(bundles, random.Random(seed), **conditions)
    recon = reconstruct_assignment(delivered)
    return {
        "converged": recon == local,
        "sent": len(bundles),
        "delivered": len(delivered),
        "local": local,
        "recon": recon,
    }


# scenario -> DTN conditions; expected convergence
SCENARIOS: List[Tuple[str, Dict[str, Any], bool]] = [
    ("instant_link", {}, True),
    ("mars_far_delay+reorder", {"reorder": True}, True),
    ("duplicate_bundles", {"dup_prob": 0.4}, True),
    ("loss_WITH_custody", {"drop_prob": 0.4, "retransmit": True}, True),
    ("permanent_loss_NO_custody", {"drop_prob": 0.5, "retransmit": False}, False),
]


def run_suite(board: Board = None, seed: int = 7) -> List[Dict[str, Any]]:
    board = board or _pipeline_board()
    out = []
    for name, cond, expect in SCENARIOS:
        r = run_link(board, cond, seed=seed)
        out.append(
            {
                "scenario": name,
                "converged": r["converged"],
                "expected": expect,
                "delivered": r["delivered"],
                "sent": r["sent"],
            }
        )
    return out


def main() -> int:
    print("SQUAD CODING under LONG-RANGE AUTONOMY (Mars-DTN multi-agent mechanism)\n")
    board = _pipeline_board()
    sub = solve_with_squad(board)
    print("  squad solved the board locally: %s (energy 0)" % ("yes" if sub.solved else "NO"))
    print(
        "  grounded Mars OWLT: %.0f min [demo/mars-communication.html]; NASA range %.0f-%.0f s [mars_dtn_sim]"
        % (MARS.owlt_typical_s / 60, MARS.owlt_min_s, MARS.owlt_max_s)
    )
    print(
        "  time-to-first-decision: pre-synced squad=%.0f min vs round-trip protocol=%.0f min [demo handshake]\n"
        % (time_to_first_decision_min(True), time_to_first_decision_min(False))
    )
    ok = True
    for s in run_suite(board):
        flag = "converged" if s["converged"] else "DIVERGED"
        match = "" if s["converged"] == s["expected"] else "  <-- UNEXPECTED"
        print("  %-28s %-10s (%d/%d bundles)%s" % (s["scenario"], flag, s["delivered"], s["sent"], match))
        ok &= s["converged"] == s["expected"]

    # delayed repair: a CBJ correction for slot0 arrives LATE (higher seq); the far end still lands on it
    repaired = run_link(board, {"reorder": True}, extra=[(999, ("slot0", "id"))])
    print(
        "\n  delayed CBJ repair (late corrective bundle): %s"
        % ("converged to repaired state" if repaired["converged"] and repaired["recon"]["slot0"] == "id" else "FAILED")
    )
    print(
        "\n  %s"
        % (
            "ALL scenarios as expected (autonomy holds; only permanent-loss-no-custody diverges)"
            if ok
            else "a scenario behaved unexpectedly"
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
