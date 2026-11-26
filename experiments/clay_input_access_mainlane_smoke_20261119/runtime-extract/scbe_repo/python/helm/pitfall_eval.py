"""pitfall_eval: a held-out eval with HEADROOM for the pitfall classes better_corpus teaches.

Why this exists. The VTC "better data" lift trains on execution-verified pitfall->fix traces
(better_corpus) and then measures base-vs-trained on held-out MBPP. The problem: a strong coder base
already near-aces MBPP, so even a real improvement reads as ~0 lift -- the eval has no headroom for the
specific skill the corpus teaches. Growing the corpus cannot fix that; the eval has to be able to SEE the
skill.

This is the matched eval. Each item is a NEW problem (disjoint from every better_corpus training trace)
that is a different instance of a taught pitfall CLASS, chosen so it DISCRIMINATES: a model that makes the
pitfall FAILS it, a model that avoids the pitfall PASSES it. That discrimination is execution-verified
offline -- `discriminates()` runs the reference (must pass) AND a naive pitfall solution (must fail). So
before any GPU run we can prove the problem set has headroom for the taught skill.

HONEST SCOPE. Offline we prove only two things: (1) each problem discriminates (pitfall solution fails,
correct solution passes), and (2) the eval is disjoint from the training traces (no teaching-to-the-test).
Whether the *trained model* actually lifts on it is for the training run to measure -- a discriminating
eval is a necessary condition for a visible lift, not a guarantee of one.

    from python.helm.pitfall_eval import eval_problems, discriminating
    probs = eval_problems()          # [{task_id, text, test_list}] -- drop-in for the notebook's MBPP eval
    assert len(discriminating()) == len(EVAL)   # every item has headroom
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List

from . import public_bench as pb

# Each eval item: a NEW problem (NOT one of the better_corpus training traces) that is a different instance
# of a taught pitfall `cls`. `ref` is a correct solution (must PASS tests); `naive` is the pitfall solution
# (must FAIL tests). The naive-fails half is what proves the problem has headroom for the taught skill.
EVAL: List[Dict[str, Any]] = [
    {
        "name": "off_by_one_countdown",
        "cls": "off_by_one",
        "prompt": "Write countdown(n) returning the list of integers from n down to 1 INCLUSIVE.",
        "ref": "def countdown(n):\n    return list(range(n, 0, -1))",
        "naive": "def countdown(n):\n    return list(range(n, 1, -1))",
        "tests": ["assert countdown(3) == [3, 2, 1]", "assert countdown(1) == [1]"],
    },
    {
        "name": "mutable_default_tally",
        "cls": "mutable_default",
        "prompt": "Write tally(item, counts) that increments counts[item] by 1 and returns counts; counts "
        "defaults to an empty dict and must NOT persist across separate calls.",
        "ref": "def tally(item, counts=None):\n    if counts is None:\n        counts = {}\n"
        "    counts[item] = counts.get(item, 0) + 1\n    return counts",
        "naive": "def tally(item, counts={}):\n    counts[item] = counts.get(item, 0) + 1\n    return counts",
        "tests": ["assert tally('a') == {'a': 1}", "assert tally('b') == {'b': 1}"],
    },
    {
        "name": "int_div_ratio",
        "cls": "int_vs_float",
        "prompt": "Write ratio(a, b) returning a divided by b as a real number (may be fractional).",
        "ref": "def ratio(a, b):\n    return a / b",
        "naive": "def ratio(a, b):\n    return a // b",
        "tests": ["assert ratio(3, 2) == 1.5", "assert ratio(5, 4) == 1.25"],
    },
    {
        "name": "modify_iter_drop_negatives",
        "cls": "modify_while_iter",
        "prompt": "Write drop_negatives(xs) returning xs with every negative number removed.",
        "ref": "def drop_negatives(xs):\n    return [x for x in xs if x >= 0]",
        "naive": "def drop_negatives(xs):\n    for x in xs:\n        if x < 0:\n            xs.remove(x)\n"
        "    return xs",
        "tests": ["assert drop_negatives([1, -2, 3, -4]) == [1, 3]", "assert drop_negatives([-1, -2]) == []"],
    },
    {
        "name": "keyerror_count_of",
        "cls": "dict_keyerror",
        "prompt": "Write count_of(d, k) returning d[k], or 0 if k is not present.",
        "ref": "def count_of(d, k):\n    return d.get(k, 0)",
        "naive": "def count_of(d, k):\n    return d[k]",
        "tests": ["assert count_of({'x': 5}, 'x') == 5", "assert count_of({}, 'y') == 0"],
    },
    {
        "name": "empty_last_char",
        "cls": "empty_index",
        "prompt": "Write last_char(s) returning the last character of s, or '' if s is empty.",
        "ref": "def last_char(s):\n    return s[-1] if s else ''",
        "naive": "def last_char(s):\n    return s[-1]",
        "tests": ["assert last_char('hi') == 'i'", "assert last_char('') == ''"],
    },
    {
        "name": "float_eq_sums_point_three",
        "cls": "float_equality",
        "prompt": "Write sums_point_three(a, b) returning True iff a + b equals 0.3 (handle float rounding).",
        "ref": "def sums_point_three(a, b):\n    return abs((a + b) - 0.3) < 1e-9",
        "naive": "def sums_point_three(a, b):\n    return a + b == 0.3",
        "tests": ["assert sums_point_three(0.1, 0.2) == True", "assert sums_point_three(1.0, 1.0) == False"],
    },
    {
        "name": "alias_duplicate_rows",
        "cls": "shallow_copy",
        "prompt": "Write duplicate_rows(g) returning an INDEPENDENT copy of the 2D list g (mutating the copy "
        "must not change g).",
        "ref": "def duplicate_rows(g):\n    return [row[:] for row in g]",
        "naive": "def duplicate_rows(g):\n    return g[:]",
        "tests": ["g = [[1, 2], [3, 4]]\nc = duplicate_rows(g)\nc[0][0] = 9\nassert g == [[1, 2], [3, 4]]"],
    },
    {
        "name": "invariant_valid_brackets",
        "cls": "stack_invariant",
        "prompt": "Write valid_brackets(s) returning True iff the square brackets in s (chars [ and ] only) "
        "are balanced.",
        "ref": "def valid_brackets(s):\n    depth = 0\n    for c in s:\n        if c == '[':\n            depth += 1\n"
        "        else:\n            depth -= 1\n            if depth < 0:\n                return False\n"
        "    return depth == 0",
        "naive": "def valid_brackets(s):\n    depth = 0\n    for c in s:\n        if c == '[':\n"
        "            depth += 1\n        else:\n            depth -= 1\n    return depth == 0",
        "tests": ["assert valid_brackets('[[]]') == True", "assert valid_brackets('][') == False"],
    },
    {
        "name": "dp_min_coins_greedy_fails",
        "cls": "dp_vs_greedy",
        "prompt": "Write min_coins(coins, amount) returning the MINIMUM number of coins summing to exactly "
        "amount, or -1 if impossible.",
        "ref": "def min_coins(coins, amount):\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n"
        "    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a:\n"
        "                dp[a] = min(dp[a], dp[a - c] + 1)\n"
        "    return dp[amount] if dp[amount] != float('inf') else -1",
        "naive": "def min_coins(coins, amount):\n    coins = sorted(coins, reverse=True)\n    n = 0\n"
        "    for c in coins:\n        while amount >= c:\n            amount -= c\n            n += 1\n"
        "    return n if amount == 0 else -1",
        "tests": ["assert min_coins([1, 3, 4], 6) == 2", "assert min_coins([2], 3) == -1"],
    },
]


def _passes(code: str, tests: List[str]) -> bool:
    return pb._verify(code, [], tests, [])["hidden_passed"]


def discriminates(item: Dict[str, Any]) -> Dict[str, bool]:
    """A held-out eval item has headroom iff its reference PASSES and its naive pitfall solution FAILS --
    i.e. the problem genuinely separates a pitfall-maker from a pitfall-avoider. Both halves checked by
    execution."""
    return {"ref_passes": _passes(item["ref"], item["tests"]), "naive_fails": not _passes(item["naive"], item["tests"])}


def discriminating() -> List[Dict[str, Any]]:
    """Only the items that actually discriminate (so a broken eval item never silently enters the set)."""
    return [it for it in EVAL if all(discriminates(it).values())]


def eval_problems() -> List[Dict[str, Any]]:
    """The discriminating items in the MBPP problem shape {task_id, text, test_list} -- a drop-in for the
    VTC notebook's held-out eval, but one that HAS headroom for the taught pitfall classes."""
    return [
        {"task_id": "pitfalleval_" + it["name"], "text": it["prompt"], "test_list": list(it["tests"])}
        for it in discriminating()
    ]


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-pitfall-eval", description="held-out pitfall-class eval with headroom")
    ap.parse_args(list(argv) if argv is not None else None)
    disc = discriminating()
    print(
        "PITFALL EVAL  %d/%d held-out problems discriminate (ref passes + naive pitfall fails)" % (len(disc), len(EVAL))
    )
    for it in EVAL:
        d = discriminates(it)
        print(
            "  %-32s [%-16s] ref_passes=%-5s naive_fails=%s"
            % (it["name"], it["cls"], d["ref_passes"], d["naive_fails"])
        )
    print("\n  %d eval problems exported (drop-in for the VTC held-out eval; MBPP shape)." % len(eval_problems()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
