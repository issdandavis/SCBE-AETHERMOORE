"""Governed cognition syscall for cube programs.

The bicameral core tells us how logic and intuition relate. This adapter turns
that relation into the L13 decision vocabulary an AI-OS can route on.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Sequence

from . import bicameral as B
from . import frontdoor as F
from . import polyglot as P

SCHEMA = "scbe_cognition_syscall_v1"
RELATION_TO_DECISION = {
    "exact match": "ALLOW",
    "close": "QUARANTINE",
    "diverged": "ESCALATE",
    "sign flip": "ESCALATE",
    "incomplete": "DENY",
}
DECISION_TO_ACTION = {
    "ALLOW": "execute",
    "QUARANTINE": "hold_for_review",
    "ESCALATE": "route_to_verifier",
    "DENY": "reject",
}


def decision_for_thought(thought: Dict[str, object]) -> str:
    """Map a bicameral reconciliation to the L13 decision ladder."""
    relation = str(thought.get("relation", "incomplete"))
    return RELATION_TO_DECISION.get(relation, "ESCALATE")


def _receipt_id(program: Sequence[str], thought: Dict[str, object], decision: str) -> str:
    body = "|".join(
        [
            " ".join(program),
            str(thought.get("logic")),
            str(thought.get("intuition")),
            str(thought.get("relation")),
            decision,
        ]
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]


def receipt_from_program(program: Sequence[str]) -> Dict[str, object]:
    """Run a program through bicameral cognition and emit a governance receipt."""
    names = list(program)
    opcodes = P.program_bytes(*names)
    thought = B.think(opcodes)
    decision = decision_for_thought(thought)
    confidence = float(thought.get("confidence", 0.0))
    return {
        "schema": SCHEMA,
        "receipt_id": _receipt_id(names, thought, decision),
        "layer": "L13",
        "decision": decision,
        "action": DECISION_TO_ACTION[decision],
        "confidence": confidence,
        "program": names,
        "opcodes": [f"0x{b:02x}" for b in opcodes],
        "thought": thought,
        "policy": {
            "exact match": "ALLOW",
            "close": "QUARANTINE",
            "diverged": "ESCALATE",
            "sign flip": "ESCALATE",
            "incomplete": "DENY",
        },
    }


def receipt_from_text(text: str, *, tongue: str | None = None) -> Dict[str, object]:
    names, _opcodes = F.tokens_to_program(text, tongue=tongue)
    return receipt_from_program(names)


def govern_archive(archive: Dict[object, dict]) -> Dict[str, object]:
    """Summarize illuminate() elites through the same syscall ladder."""
    receipts: List[Dict[str, object]] = []
    counts = {"ALLOW": 0, "QUARANTINE": 0, "ESCALATE": 0, "DENY": 0}
    for elite in archive.values():
        receipt = receipt_from_program(elite["ops"])
        receipts.append(receipt)
        counts[str(receipt["decision"])] += 1
    receipts.sort(key=lambda r: (str(r["decision"]), " ".join(r["program"])))
    return {
        "schema": "scbe_cognition_archive_governance_v1",
        "niches": len(archive),
        "counts": counts,
        "receipts": receipts,
    }


def render_receipt(receipt: Dict[str, object]) -> str:
    thought = receipt["thought"]
    lines = [
        "%s %s  action=%s  confidence=%.0f%%"
        % (
            receipt["receipt_id"],
            receipt["decision"],
            receipt["action"],
            100 * float(receipt["confidence"]),
        ),
        "  program   %s" % " ".join(receipt["program"]),
        "  logic     %s" % B._fmt(thought["logic"]),
        "  intuition %s" % B._fmt(thought["intuition"]),
        "  relation  %s" % thought["relation"],
        "  why       %s" % thought["interpretation"],
    ]
    return "\n".join(lines)


def render_archive_governance(payload: Dict[str, object]) -> str:
    counts = payload["counts"]
    return (
        "cognition syscall archive: %(niches)s niches\n"
        "  ALLOW %(ALLOW)s | QUARANTINE %(QUARANTINE)s | ESCALATE %(ESCALATE)s | DENY %(DENY)s"
        % {"niches": payload["niches"], **counts}
    )
