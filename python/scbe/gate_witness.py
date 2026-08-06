#!/usr/bin/env python3
"""Localise a correctness_gate REJECT to the sub-expression that caused it.

`correctness_gate` returns, on disagreement:

    {"verdict":"REJECT", "witness":{"input":[...], "python":..., "javascript":...}}

`grammar_backprop.shrink_to_minimal_witness` can shrink a token stream to the smallest
sub-expression that still diverges -- but the gate's inputs are TUPLES OF ARGUMENTS, and
only some of those args are grammar-generated token lists (see `_grammar`, which rewrites
one argument slot and leaves the rest of the base tuple alone). This module bridges the
two: it finds the token-list arg, shrinks it while holding every other arg fixed, and
returns the reduced witness.

Two things this is careful about, because both would silently produce a confident wrong
answer:

  - BUDGET. Each `_run` spawns a subprocess with an 8 s timeout, so a naive
    one-probe-per-candidate loop is O(nodes x faces) processes. `_run` accepts a LIST of
    inputs and returns a list, so an entire shrink round is batched into ONE subprocess
    per face. The probe budget is still capped, and when the cap binds it is REPORTED
    (`budget_exhausted`) rather than silently returning whatever it reached -- a
    truncated search that reads as "this is minimal" is worse than no answer.

  - AMBIGUITY. If several args look like token lists, each is tried; the first that
    reproduces alone is blamed. If none reproduces alone the disagreement is a joint
    property of multiple args, and that is reported as `not_isolated` rather than
    forcing a single culprit.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from .grammar_backprop import BINARY_OPS, parse_rpn, shrink_to_minimal_witness

# A generous default: a 15-node tree needs well under this, and the cap exists to stop a
# pathological input from spawning processes for minutes, not to bound normal work.
DEFAULT_MAX_PROBES = 400


def _looks_like_tokens(value: Any) -> bool:
    """A grammar-generated arg: a list carrying at least one binary operator token.

    Requiring an OPERATOR (not merely 'is a list') matters -- `_battery` also mutates
    plain list args (reversed, truncated, emptied), and those carry no grammar to
    descend into. Blaming one of those would be a category error.
    """
    if not isinstance(value, list) or len(value) < 3:
        return False
    return any(isinstance(v, str) and v in BINARY_OPS for v in value)


def localise_reject(
    faces: dict,
    entry: str,
    failing_input: Sequence[Any],
    disagree_batch: Callable[[list], list],
    max_probes: int = DEFAULT_MAX_PROBES,
) -> dict:
    """Reduce `failing_input` to the smallest sub-expression that still disagrees.

    `disagree_batch(inputs) -> [bool]` must judge a LIST of full argument tuples in one
    call. Batching is the whole point: it turns a shrink round into one subprocess per
    face instead of one per candidate.
    """
    base = list(failing_input)
    slots = [i for i, v in enumerate(base) if _looks_like_tokens(v)]
    if not slots:
        return {
            "status": "no_grammar_arg",
            "reason": "no argument is a token list containing an operator, so there is "
            "no grammar to descend. This input was not produced by _grammar "
            "(likely an edge-case or resample mutation from _battery).",
        }

    probes = {"n": 0}
    exhausted = {"hit": False}

    def _mk_predicate(slot: int):
        """Single-token-list predicate for the shrinker, backed by a batching cache."""

        def disagrees(tokens: Sequence[Any]) -> bool:
            if probes["n"] >= max_probes:
                exhausted["hit"] = True
                return False
            probes["n"] += 1
            cand = list(base)
            cand[slot] = list(tokens)
            return bool(disagree_batch([tuple(cand)])[0])

        return disagrees

    attempts = []
    for slot in slots:
        tokens = base[slot]
        if parse_rpn(tokens) is None:
            attempts.append({"slot": slot, "status": "unparseable"})
            continue
        res = shrink_to_minimal_witness(tokens, _mk_predicate(slot))
        attempts.append({"slot": slot, "status": res["status"], "result": res})
        if res["status"] == "localised":
            out = dict(res)
            out["slot"] = slot
            out["probes"] = probes["n"]
            out["full_input"] = list(base)
            reduced = list(base)
            reduced[slot] = res["minimal"]
            out["minimal_input"] = tuple(reduced)
            if exhausted["hit"]:
                out["status"] = "budget_exhausted"
                out["reason"] = (
                    "hit max_probes=%d during descent; the reported sub-expression "
                    "reproduces but is NOT established as minimal." % max_probes
                )
            return out

    return {
        "status": "budget_exhausted" if exhausted["hit"] else "not_isolated",
        "reason": (
            ("probe budget %d exhausted before any single argument reproduced alone" % max_probes)
            if exhausted["hit"]
            else (
                "no single token-list argument reproduces the disagreement on its own, so "
                "it is a JOINT property of several arguments. Reporting one of them would "
                "be wrong."
            )
        ),
        "attempts": attempts,
        "probes": probes["n"],
    }
