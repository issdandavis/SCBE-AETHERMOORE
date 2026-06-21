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

    PYTHONPATH=. python research/comms_sim/squad_autonomy_sim.py
"""

from __future__ import annotations

import random
import sys
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
    print("  squad solved the board locally: %s (energy 0)\n" % ("yes" if sub.solved else "NO"))
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
