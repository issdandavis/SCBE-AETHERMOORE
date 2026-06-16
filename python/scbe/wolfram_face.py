"""
Wolfram face — every token is also an elementary cellular automaton.
=====================================================================

Stephen Wolfram studied the 256 *elementary cellular automata* (ECA): 1-D,
2-state, nearest-neighbour rules. Each rule is named by an 8-bit "Wolfram code"
0..255 — the output bit for each of the 2^3 = 8 neighbourhoods. So there are
exactly 256 of them, the same size as one Sacred-Tongue token grid (16x16 = 256).

That gives the cube a new face. A token's byte value `b` (0..255) IS Wolfram
Rule `b`. Rotating a token to its **Wolfram face** yields the rule, its
complexity class, and whether it is computationally universal — so each token
carries a *dynamics signature* alongside its tongue / chem / governance faces.

Wolfram's four classes (A New Kind of Science; MathWorld):
  * Class I   — evolution dies to a single homogeneous state (order)
  * Class II  — settles into stable or periodic structures (repetition)
  * Class III — chaotic / pseudo-random (e.g. Rule 30, used as a PRNG)
  * Class IV  — localized structures that interact in complex ways; the
                "edge of chaos". Rule 110 is Class IV and PROVEN Turing-complete.
Wolfram's Principle of Computational Equivalence: almost any rule whose behaviour
is not obviously simple is computationally as powerful as anything else — so a
Class III/IV token is, in principle, a universal little computer.

Classes here are derived by *simulating* each rule (deterministic, reproducible),
with the canonical complex/universal rules pinned as anchors — because the
Class III/IV boundary is qualitative in Wolfram's own work, not a clean formula.
"""

from __future__ import annotations

import sys
from typing import Dict, List

CLASS_NAME = {
    "I": "homogeneous (order)",
    "II": "periodic (repetition)",
    "III": "chaotic (pseudo-random)",
    "IV": "complex (edge of chaos)",
}

# Rule 110 and its left-right / black-white equivalents are the proven
# Turing-complete ECAs. (110, 124, 137, 193 are the same automaton under the
# symmetry group.) These are the universal Class IV anchors.
UNIVERSAL_RULES = frozenset({110, 124, 137, 193})

# Canonical Class IV (complex / localized) rules from NKS, beyond the universal
# family: 54 and its mirror 147. Kept as anchors; the rest are simulated.
CLASS4_RULES = UNIVERSAL_RULES | frozenset({54, 147})


def step(state: List[int], rule: int) -> List[int]:
    """One ECA update on a periodic (wrap-around) 1-D lattice."""
    n = len(state)
    out = [0] * n
    for i in range(n):
        nbhd = (state[(i - 1) % n] << 2) | (state[i] << 1) | state[(i + 1) % n]
        out[i] = (rule >> nbhd) & 1
    return out


def _seed(width: int, kind: str, rule: int) -> List[int]:
    """A single-cell seed, or a deterministic pseudo-random seed (no RNG)."""
    if kind == "single":
        s = [0] * width
        s[width // 2] = 1
        return s
    # deterministic: derived from the rule so runs are reproducible across machines
    return [((rule * 2654435761 + i * 40503) >> (i % 16)) & 1 for i in range(width)]


def evolve(rule: int, width: int = 64, steps: int = 160, kind: str = "single") -> List[List[int]]:
    """Return the space-time rows (steps+1 x width) for `rule`."""
    state = _seed(width, kind, rule)
    rows = [state]
    for _ in range(steps):
        state = step(state, rule)
        rows.append(state)
    return rows


def classify(rule: int) -> str:
    """Assign a Wolfram class by simulation, with the complex rules pinned.

    Random seed on an ODD-width ring (101): Wolfram's classes describe typical
    behaviour from generic initial conditions, and a power-of-two width makes
    additive rules (90, 150) collapse to zero — an artifact that mislabels them.

    Every finite ring is eventually periodic, so the cycle is the separator:
      * homogeneous final state            -> Class I  (order)
      * settles into a SHORT cycle         -> Class II (periodic / repetition)
      * no short cycle within the run      -> Class III (chaotic)
      * canonical complex/universal rules  -> Class IV (pinned)
    """
    if rule in CLASS4_RULES:
        return "IV"

    width, steps = 63, 600
    rows = evolve(rule, width=width, steps=steps, kind="random")

    # Class I — a random configuration dies to one homogeneous value and stays.
    if all(all(v == rows[-1][0] for v in r) for r in rows[-15:]):
        return "I"

    # First repeated whole-lattice state -> the cycle this trajectory fell into.
    seen: Dict[tuple, int] = {}
    period = None
    for t, row in enumerate(rows):
        key = tuple(row)
        if key in seen:
            period = t - seen[key]
            break
        seen[key] = t

    # Settles into a cycle within the run = simple/periodic (Class II); never
    # repeats within 600 steps on a 2^63 state space = chaotic (Class III).
    if period is not None:
        return "II"
    return "III"


def token_rule(index: int) -> Dict[str, object]:
    """The Wolfram face of token `index` (0..255): its ECA rule + complexity."""
    if not 0 <= index <= 255:
        raise ValueError("token index must be 0..255 (one 16x16 tongue grid)")
    cls = classify(index)
    return {
        "token_index": index,
        "rule": index,  # byte value IS the Wolfram code
        "class": cls,
        "class_name": CLASS_NAME[cls],
        "universal": index in UNIVERSAL_RULES,
        "wolfram_code_bits": format(index, "08b"),
    }


def full_map() -> List[Dict[str, object]]:
    """The Wolfram face for all 256 tokens."""
    return [token_rule(i) for i in range(256)]


def render(rule: int, width: int = 63, steps: int = 24, kind: str = "single") -> str:
    """ASCII space-time diagram for a rule (handy for eyeballing a token)."""
    rows = evolve(rule, width=width, steps=steps, kind=kind)
    return "\n".join("".join("█" if c else " " for c in r) for r in rows)


def _demo() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # render block/dash glyphs on cp1252 consoles
    except (AttributeError, ValueError):
        pass
    rules = full_map()
    counts: Dict[str, int] = {"I": 0, "II": 0, "III": 0, "IV": 0}
    for r in rules:
        counts[r["class"]] += 1  # type: ignore[index]

    print("Wolfram face — 256 tokens mapped to the 256 elementary CA rules\n")
    print("class distribution across the 256-token grid:")
    for c in ("I", "II", "III", "IV"):
        print(f"  Class {c:<3} {CLASS_NAME[c]:<26} {counts[c]:>3} tokens")
    print(f"  universal (Turing-complete) tokens: {sorted(UNIVERSAL_RULES)}")

    print("\nnotable tokens:")
    for idx, label in [
        (0, "blank"),
        (30, "Rule 30 — chaos / PRNG"),
        (90, "Rule 90 — Sierpinski"),
        (110, "Rule 110 — UNIVERSAL"),
        (184, "Rule 184 — traffic"),
        (255, "fill"),
    ]:
        t = token_rule(idx)
        print(f"  token {idx:>3} [{t['wolfram_code_bits']}]  Class {t['class']:<3} {t['class_name']}")

    print("\ntoken 110 (Rule 110 — the universal one) space-time from a single seed:")
    print(render(110, width=63, steps=20))


if __name__ == "__main__":
    _demo()
