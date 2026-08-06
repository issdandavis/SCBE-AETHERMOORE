#!/usr/bin/env python3
"""Back-propagating grammatical verifier.

`correctness_gate` in SCBE-AETHERMOORE/python/scbe/correctness_gate.py already does the
forward pass: `_grammar` builds an expression TREE, flattens it to both RPN and infix,
runs every language face, and returns SEAL / REJECT / FLAG. On REJECT it hands back the
whole failing input:

    {"verdict":"REJECT", "witness":{"input":[...40 tokens...], "python":..., "javascript":...}}

That names the disagreement but not its CAUSE. A 40-token expression that diverges tells
you nothing about which operator did it -- and the whole point of a grammar-generated
input is that its structure is KNOWN, so the blame is localisable.

This module propagates the verdict BACK DOWN the grammar. It returns the smallest
sub-expression that still makes the faces disagree.

Why RPN is the right carrier: in reverse-Polish, every well-formed subtree is a
CONTIGUOUS SLICE, and every subtree is itself a valid complete expression. So a subtree
can be re-tested directly, with no re-parsing or re-wrapping. Infix cannot do that
without parenthesisation, which would change the token stream you are trying to blame.

The shrinker is deliberately agnostic about HOW disagreement is detected -- it takes a
`disagrees(tokens) -> bool` callable. The gate decides what counts as divergence; this
decides where it lives. Keeping those separate is what lets the same shrinker serve the
verifier ladder, the perturbation gate, and the isomorphic-twin check without change.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

Token = object
Tree = Tuple  # ("n", value) | ("o", op, left, right)

BINARY_OPS = {"+", "-", "*", "/", "%", "**", "//"}


def parse_rpn(tokens: Sequence[Token]) -> Optional[Tree]:
    """RPN token list -> tree. None if the stream is not well-formed."""
    stack: List[Tree] = []
    for tok in tokens:
        if isinstance(tok, str) and tok in BINARY_OPS:
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            stack.append(("o", tok, left, right))
        else:
            stack.append(("n", tok))
    return stack[0] if len(stack) == 1 else None


def to_rpn(tree: Tree) -> List[Token]:
    if tree[0] == "n":
        return [tree[1]]
    return to_rpn(tree[2]) + to_rpn(tree[3]) + [tree[1]]


def subtrees(tree: Tree) -> List[Tree]:
    """Every subtree, LARGEST first. Order matters for the shrink loop below."""
    out = [tree]
    if tree[0] == "o":
        out.extend(subtrees(tree[2]))
        out.extend(subtrees(tree[3]))
    return out


def size(tree: Tree) -> int:
    return 1 if tree[0] == "n" else 1 + size(tree[2]) + size(tree[3])


def shrink_to_minimal_witness(
    tokens: Sequence[Token],
    disagrees: Callable[[Sequence[Token]], bool],
) -> dict:
    """Find the smallest sub-expression of `tokens` that still makes faces disagree.

    Returns a dict with the minimal token list, its tree, and an audit trail.

    Two failure modes are reported honestly rather than swallowed:

      - `not_reproducible`: the FULL input does not disagree when re-run. That means the
        divergence is not a function of the input alone -- nondeterminism, shared state,
        or a timeout. Shrinking such a case would "localise" onto whichever subtree
        happened to flake, which is worse than no answer. So it refuses.
      - `unparseable`: the stream is not well-formed RPN, so there is no grammar to
        propagate back through. Callers passing infix land here by construction.
    """
    if not disagrees(list(tokens)):
        return {
            "status": "not_reproducible",
            "reason": "full input does not disagree on re-run -- divergence is not "
            "input-determined (nondeterminism / shared state / timeout). "
            "Refusing to localise a flake.",
            "minimal": None,
        }

    tree = parse_rpn(tokens)
    if tree is None:
        return {
            "status": "unparseable",
            "reason": "token stream is not well-formed RPN; no grammar to descend. "
            "(infix inputs cannot be blamed without re-parenthesising, "
            "which would change the stream under test)",
            "minimal": None,
        }

    trail = []
    current = tree
    improved = True
    while improved:
        improved = False
        # Children before self, smaller before larger: take the biggest reduction that
        # still reproduces, then restart. Greedy descent, not exhaustive search -- the
        # result is a LOCAL minimum and is labelled as such below.
        cands = [t for t in subtrees(current) if t is not current]
        cands.sort(key=size)
        for cand in cands:
            cand_tokens = to_rpn(cand)
            if disagrees(cand_tokens):
                trail.append({"from_size": size(current), "to_size": size(cand), "tokens": cand_tokens})
                current = cand
                improved = True
                break

    minimal = to_rpn(current)
    return {
        "status": "localised",
        "minimal": minimal,
        "minimal_tree": current,
        "minimal_size": size(current),
        "original_size": size(tree),
        "reduction": "%d -> %d nodes" % (size(tree), size(current)),
        "blamed_op": current[1] if current[0] == "o" else None,
        "trail": trail,
        "note": "greedy descent -- this is a LOCAL minimum. No strictly smaller SUBTREE "
        "reproduces, but a non-subtree edit might. Do not report it as 'the "
        "unique minimal cause'.",
    }


# ---------------------------------------------------------------------------------
# Demo / self-test: a real, classic Python-vs-JavaScript divergence.
#
#   Python:      -7 %  3  ==  2      (result takes the SIGN OF THE DIVISOR)
#   JavaScript:  -7 %  3  == -1      (result takes the sign of the DIVIDEND)
#
# Both are "correct" for their language. That is exactly the kind of bug a
# cross-face gate exists to catch, and exactly the kind a 40-token witness hides.
# ---------------------------------------------------------------------------------
def _py_eval(tokens: Sequence[Token]) -> object:
    stack: List[object] = []
    for t in tokens:
        if isinstance(t, str) and t in BINARY_OPS:
            b = stack.pop()
            a = stack.pop()
            try:
                if t == "+":
                    stack.append(a + b)
                elif t == "-":
                    stack.append(a - b)
                elif t == "*":
                    stack.append(a * b)
                elif t == "/":
                    stack.append(a / b)
                elif t == "%":
                    stack.append(a % b)
                elif t == "**":
                    stack.append(a**b)
                elif t == "//":
                    stack.append(a // b)
            except ZeroDivisionError:
                return ("err", "ZeroDivisionError")
        else:
            stack.append(t)
    return ("ok", stack[0])


def _js_like_eval(tokens: Sequence[Token]) -> object:
    """JS semantics for the two places they differ from Python: % sign, and /0."""
    import math

    stack: List[object] = []
    for t in tokens:
        if isinstance(t, str) and t in BINARY_OPS:
            b = stack.pop()
            a = stack.pop()
            if t == "+":
                stack.append(a + b)
            elif t == "-":
                stack.append(a - b)
            elif t == "*":
                stack.append(a * b)
            elif t == "/":
                stack.append(math.inf if b == 0 else a / b)  # JS: no throw
            elif t == "%":
                stack.append(math.fmod(a, b) if b != 0 else math.nan)  # JS: sign of dividend
            elif t == "**":
                stack.append(a**b)
            elif t == "//":
                stack.append(math.floor(a / b) if b else math.inf)
        else:
            stack.append(t)
    return ("ok", stack[0])


def _demo_disagrees(tokens: Sequence[Token]) -> bool:
    p, j = _py_eval(tokens), _js_like_eval(tokens)
    if p[0] != j[0]:
        return True
    if p[0] == "err":
        return False
    try:
        return abs(float(p[1]) - float(j[1])) > 1e-9
    except (TypeError, ValueError, OverflowError):
        return p[1] != j[1]


if __name__ == "__main__":
    # A 13-node expression. Exactly one operator in it actually diverges.
    big = [8, 5, "+", 2, "*", -7, 3, "%", 4, "+", "-", 6, 2, "/", "+"]
    print("input        :", big)
    print("  python  ->", _py_eval(big))
    print("  js-like ->", _js_like_eval(big))
    print("  disagree?  ", _demo_disagrees(big))
    print()

    res = shrink_to_minimal_witness(big, _demo_disagrees)
    for k in ("status", "reduction", "minimal", "blamed_op"):
        print("%-14s: %s" % (k, res.get(k)))
    print("trail steps  :", len(res.get("trail") or []))
    for step in res.get("trail") or []:
        print("    %2d -> %2d nodes  %s" % (step["from_size"], step["to_size"], step["tokens"]))
    print()
    print(res["note"])

    # Guard: an expression with NO diverging operator must not be "localised".
    clean = [8, 5, "+", 2, "*", 6, 2, "/", "+"]
    print("\nclean input  :", clean, "-> disagrees?", _demo_disagrees(clean))
    print("shrink status:", shrink_to_minimal_witness(clean, _demo_disagrees)["status"])
