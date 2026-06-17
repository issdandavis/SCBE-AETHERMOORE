"""Toroidal braid substrate for reversible cube-board computation.

The model is deliberately small: a braid word is a sequence of neighbor
crossings on a cyclic strand ring.  The seam crossing wraps the final strand
back to zero, so the substrate is toroidal.  A crossing and its opposite
over/under orientation are exact inverses when the whole word is reversed.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable, List, Sequence


@dataclass(frozen=True, slots=True)
class Crossing:
    """One toroidal braid generator.

    ``index`` swaps strand positions ``index`` and ``index + 1`` modulo the
    strand count. ``over`` records the topological orientation. Over and under
    have the same endpoint permutation but opposite writhe, so the orientation
    is not decoration.
    """

    index: int
    over: bool = True


def apply_crossing(strands: List[int], crossing: Crossing) -> int:
    """Apply one crossing in place and return its writhe contribution."""

    if not strands:
        raise ValueError("at least one strand is required")
    i = crossing.index % len(strands)
    j = (i + 1) % len(strands)
    strands[i], strands[j] = strands[j], strands[i]
    return 1 if crossing.over else -1


def apply_word(strands: List[int], word: Iterable[Crossing]) -> int:
    """Apply a braid word in place and return total writhe."""

    return sum(apply_crossing(strands, crossing) for crossing in word)


def inverse_word(word: Sequence[Crossing]) -> List[Crossing]:
    """Exact inverse: reverse order and flip over/under orientation."""

    return [Crossing(crossing.index, not crossing.over) for crossing in reversed(word)]


def random_word(count: int, *, strands: int = 8, seed: int | None = None) -> List[Crossing]:
    """Deterministic random braid word for tests and demos."""

    rng = Random(seed)
    return [Crossing(rng.randrange(strands), rng.random() < 0.5) for _ in range(count)]


def cyclic_loop(strands: int, *, over: bool = True) -> List[Crossing]:
    """One crossing at every seam position around the toroidal ring."""

    if strands <= 0:
        raise ValueError("strands must be positive")
    return [Crossing(i, over) for i in range(strands)]


def braid_relation_holds(index: int = 2, *, strands: int = 8) -> bool:
    """Yang-Baxter relation: sigma_i sigma_j sigma_i == sigma_j sigma_i sigma_j."""

    if strands < 3:
        raise ValueError("at least three strands are required")
    i = index % strands
    j = (i + 1) % strands
    lhs = list(range(strands))
    rhs = list(range(strands))
    apply_word(lhs, [Crossing(i), Crossing(j), Crossing(i)])
    apply_word(rhs, [Crossing(j), Crossing(i), Crossing(j)])
    return lhs == rhs


def prove_bijective(samples: int = 2000, *, strands: int = 8, word_len: int = 60, seed: int = 11) -> dict:
    """Run random forward/backward braid proofs and return a compact receipt."""

    rng = Random(seed)
    ok = 0
    for _ in range(samples):
        state = list(range(strands))
        initial = list(state)
        word = [Crossing(rng.randrange(strands), rng.random() < 0.5) for _ in range(word_len)]
        writhe = apply_word(state, word)
        writhe += apply_word(state, inverse_word(word))
        ok += int(state == initial and writhe == 0)
    return {
        "schema": "scbe_toroidal_braid_proof_v1",
        "samples": samples,
        "passed": ok,
        "strands": strands,
        "word_len": word_len,
        "seed": seed,
        "bijective": ok == samples,
    }


def demo_receipt(strands: int = 8) -> dict:
    """Human-readable proof packet for the world-map doc and CLI experiments."""

    loop_state = list(range(strands))
    loop_writhe = apply_word(loop_state, cyclic_loop(strands))
    inverse_state = list(loop_state)
    apply_word(inverse_state, inverse_word(cyclic_loop(strands)))

    over_state = list(range(strands))
    under_state = list(range(strands))
    over_writhe = apply_word(over_state, [Crossing(2, True)])
    under_writhe = apply_word(under_state, [Crossing(2, False)])

    return {
        "proof": prove_bijective(strands=strands),
        "cyclic_loop": {
            "permutation": loop_state,
            "writhe": loop_writhe,
            "inverse_restores": inverse_state == list(range(strands)),
        },
        "over_under": {
            "same_permutation": over_state == under_state,
            "over_writhe": over_writhe,
            "under_writhe": under_writhe,
            "distinct_braids": over_writhe != under_writhe,
        },
        "braid_relation": braid_relation_holds(strands=strands),
    }


__all__ = [
    "Crossing",
    "apply_crossing",
    "apply_word",
    "braid_relation_holds",
    "cyclic_loop",
    "demo_receipt",
    "inverse_word",
    "prove_bijective",
    "random_word",
]
