"""Over-creation loop for cube programs.

Generate many stack-valid scalar programs, run bicameral cognition on each,
then keep the programs that are complete, bounded, and surprising. This is the
first local form of the agentic generation pipeline: create too much, score the
logic-vs-intuition gap, and return the candidates worth inspecting.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Dict, List, Sequence

from . import bicameral as B
from . import polyglot as P

UNARY_OPS = tuple(sorted(n for n in P.SCALAR_OPS if B.EXACT[n][0] == 1))
BINARY_OPS = tuple(sorted(n for n in P.SCALAR_OPS if B.EXACT[n][0] == 2))


@dataclass(frozen=True)
class Candidate:
    rank: int
    program: List[str]
    opcodes: List[str]
    logic: float
    intuition: float
    relation: str
    confidence: float
    abs_error: float
    rel_error: float
    normalized_gap: float
    surprise_score: float
    nonlinear_ops: List[str]
    interpretation: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "rank": self.rank,
            "program": self.program,
            "opcodes": self.opcodes,
            "logic": self.logic,
            "intuition": self.intuition,
            "relation": self.relation,
            "confidence": self.confidence,
            "abs_error": self.abs_error,
            "rel_error": self.rel_error,
            "normalized_gap": self.normalized_gap,
            "surprise_score": self.surprise_score,
            "nonlinear_ops": self.nonlinear_ops,
            "interpretation": self.interpretation,
        }


def generate_program(rng: random.Random, *, min_len: int = 1, max_len: int = 10) -> List[str]:
    """Generate one stack-valid program over the 3-value scalar stack."""
    if min_len < 1 or max_len < min_len:
        raise ValueError("expected 1 <= min_len <= max_len")
    depth = 3
    prog: List[str] = []
    for _ in range(rng.randint(min_len, max_len)):
        can_binary = depth >= 2
        if can_binary and rng.random() < 0.58:
            op = rng.choice(BINARY_OPS)
            depth -= 1
        else:
            op = rng.choice(UNARY_OPS)
        prog.append(op)
        depth = max(depth, 1)
    return prog


def _finite_number(value: object, *, max_abs_result: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value)) and abs(float(value)) <= max_abs_result


def score_program(names: Sequence[str], *, max_abs_result: float = 1_000_000.0) -> Dict[str, object] | None:
    """Return a scored candidate payload, or None if it is broken/unbounded/trivial."""
    prog = P.program_bytes(*names)
    thought = B.think(prog)
    logic = thought.get("logic")
    guess = thought.get("intuition")
    if not _finite_number(logic, max_abs_result=max_abs_result):
        return None
    if not _finite_number(guess, max_abs_result=max_abs_result):
        return None
    if thought.get("relation") == "incomplete":
        return None

    abs_error = float(thought.get("abs_error", 0.0))
    rel_error = float(thought.get("rel_error", 0.0))
    nonlinear = list(thought.get("nonlinear_ops", []))
    if abs_error <= 1e-9 and not nonlinear:
        return None

    normalized_gap = abs_error / (1.0 + abs(float(logic)) + abs(float(guess)))
    depth_bonus = 1.0 + 0.15 * len(names)
    nonlinear_bonus = 1.0 + 0.35 * len(nonlinear)
    score = (normalized_gap + math.log1p(abs_error)) * depth_bonus * nonlinear_bonus
    return {
        "program": list(names),
        "opcodes": [f"0x{b:02x}" for b in prog],
        "logic": float(logic),
        "intuition": float(guess),
        "relation": str(thought.get("relation")),
        "confidence": float(thought.get("confidence", 0.0)),
        "abs_error": abs_error,
        "rel_error": rel_error,
        "normalized_gap": normalized_gap,
        "surprise_score": score,
        "nonlinear_ops": nonlinear,
        "interpretation": str(thought.get("interpretation", "")),
    }


def run_loop(
    *,
    count: int = 256,
    seed: int = 0,
    top: int = 8,
    min_len: int = 1,
    max_len: int = 10,
    max_abs_result: float = 1_000_000.0,
) -> Dict[str, object]:
    """Run the over-creation loop and return a stable JSON-ready payload."""
    if count < 1:
        raise ValueError("count must be positive")
    if top < 1:
        raise ValueError("top must be positive")
    rng = random.Random(seed)
    scored: List[Dict[str, object]] = []
    seen = set()
    for _ in range(count):
        names = generate_program(rng, min_len=min_len, max_len=max_len)
        key = tuple(names)
        if key in seen:
            continue
        seen.add(key)
        candidate = score_program(names, max_abs_result=max_abs_result)
        if candidate is not None:
            scored.append(candidate)

    scored.sort(
        key=lambda c: (
            float(c["surprise_score"]),
            float(c["abs_error"]),
            len(c["program"]),
        ),
        reverse=True,
    )
    ranked = [Candidate(rank=i + 1, **candidate).as_dict() for i, candidate in enumerate(scored[:top])]
    return {
        "schema": "scbe_overcreation_v1",
        "seed": seed,
        "generated": count,
        "unique_programs": len(seen),
        "kept": len(scored),
        "top": ranked,
        "filters": {
            "stack": "valid 3-value scalar stack",
            "max_abs_result": max_abs_result,
            "reject": ["incomplete", "non-finite", "unbounded", "linear exact-match"],
        },
    }


def render(payload: Dict[str, object]) -> str:
    lines = ["over-created %(generated)s programs; %(kept)s survived (%(unique_programs)s unique)" % payload]
    top = payload.get("top", [])
    if not top:
        lines.append("  no bounded surprising candidates survived; raise --count or --max-abs-result")
        return "\n".join(lines)
    for row in top:
        assert isinstance(row, dict)
        lines.append(
            "#{rank:<2} score {surprise_score:>8.3f}  gap {abs_error:>9.3g}  "
            "{relation:<10}  {program}".format(
                rank=row["rank"],
                surprise_score=float(row["surprise_score"]),
                abs_error=float(row["abs_error"]),
                relation=str(row["relation"]),
                program=" ".join(row["program"]),
            )
        )
        lines.append(
            "    logic {logic:.6g} | intuition {intuition:.6g} | nonlinear {nonlinear}".format(
                logic=float(row["logic"]),
                intuition=float(row["intuition"]),
                nonlinear=", ".join(row["nonlinear_ops"]) or "-",
            )
        )
    return "\n".join(lines)
