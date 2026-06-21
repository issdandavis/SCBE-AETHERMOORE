"""dice: a die is a TYPED FINITE-DOMAIN CHOICE OPERATOR -- auditable, reproducible, constrained.

The frame (docs/research/dice_input_coding_systems_2026-05-31.md): "throwing dice into a coding system"
is not vague randomness. A code die is `1dN` where N is EXACTLY the number of legal choices at that point:

  1d2  -> a boolean branch     1dM -> one allowed tool call
  1dK  -> one legal rewrite    0   -> an EXPLICIT no-throw / pass / reroll / different-die (never silent failure)

The SCBE difference from a plain RNG: every throw is (a) TYPED + CONSTRAINED -- you can only land on a legal
side, an out-of-range value is rejected; (b) REPRODUCIBLE -- the same seed re-derives the same throw, so a
run replays exactly; (c) AUDITABLE -- each throw is a sealed receipt (scbe_dice_choice_v1), and a DiceLog is
a forward-chained, replayable CHOICE TRACE. This is the move-choice for [[board-game-thinking-surface]] /
game_task (roll among the legal moves) and for tool routing (roll among the allowed tools).

CLAIM BOUNDARY (verbatim from the doc -- do NOT overclaim): dice do NOT "make code intelligent." The claim
is only: SCBE can represent bounded code/tool/agent choices as reproducible finite-domain dice packets with
replayable receipts. That is real, testable, useful -- and nothing more.

    p = roll_legal(["safe_rewrite", "alt_rewrite", "ask_tool"], seed="run-1")   # 1d3 over legal options
    replay(p)                                                                    # True -- re-derives the throw
    route(["read_file", "list_files"], seed="run-1")                            # pick an allowed tool, sealed
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence

SCHEMA = "scbe_dice_choice_v1"
ZERO_POLICIES = ("no_throw", "pass", "reroll", "different_die")  # 0 is explicit, never a silent failure


def _hash_fraction(seed: str, salt: str) -> float:
    """A deterministic fraction in [0, 1) from (seed, salt) -- the reproducible 'throw'."""
    h = hashlib.sha256(("%s|%s" % (seed, salt)).encode("utf-8")).hexdigest()
    return int(h[:16], 16) / float(1 << 64)


def _choose(sides: int, fraction: float, weights: Optional[Sequence[float]]) -> int:
    """Map a [0,1) fraction to a side in 1..sides -- uniform, or by a weighted (non-uniform) distribution."""
    if weights:
        total = float(sum(weights)) or 1.0
        acc = 0.0
        for i, w in enumerate(weights, 1):
            acc += w / total
            if fraction < acc:
                return i
        return sides
    return min(sides, int(fraction * sides) + 1)


def _dice_seal(rec: Dict[str, Any]) -> str:
    """SHA-256 over the packet excluding its own receipt_hash -- the auditable, tamper-evident receipt."""
    body = {k: v for k, v in rec.items() if k != "receipt_hash"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def roll(
    sides: int,
    seed: str,
    labels: Optional[Sequence[str]] = None,
    weights: Optional[Sequence[float]] = None,
    role: str = "choice",
    die_id: Optional[str] = None,
    salt: str = "",
    constraints: Sequence[str] = (),
) -> Dict[str, Any]:
    """Throw a 1dN typed die. Returns a sealed scbe_dice_choice_v1 packet. `sides` is the legal-option count;
    `value` in 1..sides is the selected side; `side_label` binds it to a real operation. sides<=0 -> a zero
    event (an empty legal domain cannot be thrown)."""
    if sides <= 0:
        return zero_packet("no_throw", seed, role=role, die_id=die_id, salt=salt)
    frac = _hash_fraction(seed, "%s|%s" % (die_id or role, salt))
    value = _choose(sides, frac, weights)
    rec: Dict[str, Any] = {
        "schema_version": SCHEMA,
        "die_id": die_id or role,
        "dimension": 1,
        "sides": sides,
        "value": value,
        "side_label": labels[value - 1] if labels and value - 1 < len(labels) else str(value),
        "role": role,
        "seed": seed,
        "salt": salt,
        "weights": list(weights) if weights else None,
        "constraints": list(constraints),
        "zero_policy": None,
    }
    rec["receipt_hash"] = _dice_seal(rec)
    return rec


def zero_packet(
    policy: str, seed: str, role: str = "choice", die_id: Optional[str] = None, salt: str = ""
) -> Dict[str, Any]:
    """An EXPLICIT zero event: 0 is no-throw / pass / reroll / different_die -- recorded, never silent failure."""
    if policy not in ZERO_POLICIES:
        policy = "no_throw"
    rec: Dict[str, Any] = {
        "schema_version": SCHEMA,
        "die_id": die_id or role,
        "dimension": 1,
        "sides": 0,
        "value": 0,
        "side_label": policy,
        "role": role,
        "seed": seed,
        "salt": salt,
        "weights": None,
        "constraints": [],
        "zero_policy": policy,
    }
    rec["receipt_hash"] = _dice_seal(rec)
    return rec


def roll_legal(
    legal: Sequence[str],
    seed: str,
    weights: Optional[Sequence[float]] = None,
    zero_policy: str = "pass",
    role: str = "legal_move",
    die_id: Optional[str] = None,
    salt: str = "",
) -> Dict[str, Any]:
    """Roll ONLY among the legal options -- the typed die over the legal-options gate. sides = len(legal), so
    an illegal side is unreachable. An empty legal set -> the explicit zero event (not a silent failure)."""
    legal = list(legal)
    if not legal:
        return zero_packet(zero_policy, seed, role=role, die_id=die_id, salt=salt)
    return roll(
        len(legal),
        seed,
        labels=legal,
        weights=weights,
        role=role,
        die_id=die_id,
        salt=salt,
        constraints=("legal_only",),
    )


def route(
    allowed_tools: Sequence[str], seed: str, weights: Optional[Sequence[float]] = None, salt: str = ""
) -> Dict[str, Any]:
    """Tool routing: pick a tool only from the allowed sides (sealed). Keeps the model from inventing tools."""
    return roll_legal(allowed_tools, seed, weights=weights, role="tool_choice", salt=salt)


def is_valid_side(packet: Dict[str, Any]) -> bool:
    """A typed die can only land in 1..sides (or 0 for a zero event). Rejects a forged out-of-range value."""
    v, n = packet.get("value"), packet.get("sides")
    if packet.get("zero_policy"):
        return v == 0 and n == 0
    return isinstance(v, int) and isinstance(n, int) and 1 <= v <= n


def replay(packet: Dict[str, Any]) -> bool:
    """Re-derive the throw from its seed and confirm it matches AND the receipt is intact -- the audit. A
    forged value, an out-of-range side, or a tampered receipt all fail."""
    if not is_valid_side(packet):
        return False
    if packet.get("receipt_hash") != _dice_seal(packet):
        return False
    if packet.get("zero_policy"):
        return True  # a zero event has no random draw to re-derive; the receipt check is the audit
    frac = _hash_fraction(packet["seed"], "%s|%s" % (packet.get("die_id") or packet["role"], packet.get("salt", "")))
    return _choose(packet["sides"], frac, packet.get("weights")) == packet["value"]


class DiceLog:
    """A reproducible CHOICE TRACE: a forward-chained sequence of throws under one seed. Each throw's salt is
    its position, so the sequence varies yet replays exactly; `verify()` walks the chain + re-derives every
    throw. This is the replayable receipt stream the doc calls for -- a run's decisions, auditable end to end."""

    def __init__(self, seed: str) -> None:
        self.seed = seed
        self.throws: List[Dict[str, Any]] = []

    def roll_legal(self, legal: Sequence[str], weights: Optional[Sequence[float]] = None, **kw: Any) -> Dict[str, Any]:
        p = roll_legal(legal, self.seed, weights=weights, salt=str(len(self.throws)), **kw)
        self.throws.append(p)
        return p

    def labels(self) -> List[str]:
        return [t["side_label"] for t in self.throws]

    def verify(self) -> bool:
        """Every throw re-derives from the seed AND its receipt is intact -- the whole trace is replayable."""
        return all(replay(t) and t.get("salt") == str(i) for i, t in enumerate(self.throws))


def bench() -> Dict[str, Any]:
    """The doc's checks: deterministic replay, invalid-side rejection, explicit zero policy, weighted sanity."""
    a = roll_legal(["x", "y", "z"], seed="bench")
    b = roll_legal(["x", "y", "z"], seed="bench")
    deterministic = a["value"] == b["value"] and a["side_label"] == b["side_label"] and replay(a)

    forged = dict(a)
    forged["value"] = a["sides"] + 99  # claim an out-of-range side
    invalid_rejected = not is_valid_side(forged) and not replay(forged)

    z = roll_legal([], seed="bench", zero_policy="pass")
    zero_explicit = z["value"] == 0 and z["zero_policy"] == "pass" and z["side_label"] == "pass"

    # weighted: side 1 heavily favored -> it dominates a sweep of seeds (and every throw still replays)
    hits = 0
    n = 400
    for i in range(n):
        p = roll(2, "w-%d" % i, labels=["A", "B"], weights=[0.9, 0.1])
        hits += p["value"] == 1 and replay(p)
    weighted_sane = 0.80 <= hits / n <= 0.98

    return {
        "deterministic_replay": bool(deterministic),
        "invalid_side_rejected": bool(invalid_rejected),
        "zero_is_explicit": bool(zero_explicit),
        "weighted_distribution_sane": bool(weighted_sane),
        "favored_share": round(hits / n, 3),
    }


def demo() -> Dict[str, Any]:
    log = DiceLog(seed="agent-run-7")
    # an agent rolling among its LEGAL moves, then among ALLOWED tools -- a replayable decision trace
    log.roll_legal(["go_left", "go_right", "wait"])
    log.roll_legal(["read_file", "list_files", "run_test"], role="tool_choice")
    log.roll_legal([], zero_policy="pass")  # no legal move -> explicit pass, not a crash
    return {"trace": log.labels(), "trace_replays": log.verify(), "bench": bench()}


def main(argv: Optional[List[str]] = None) -> int:
    out = demo()
    print("DICE -- typed finite-domain choice (auditable, reproducible, constrained)")
    print("  a replayable choice trace: %s   (replays exactly: %s)" % (" -> ".join(out["trace"]), out["trace_replays"]))
    b = out["bench"]
    print("  deterministic replay : %s" % b["deterministic_replay"])
    print("  invalid side rejected: %s" % b["invalid_side_rejected"])
    print("  zero is explicit     : %s" % b["zero_is_explicit"])
    print(
        "  weighted sane        : %s  (favored side share %.0f%%)"
        % (b["weighted_distribution_sane"], 100 * b["favored_share"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
