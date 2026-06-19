"""perturbed: the curriculum, twisted so a model can't win by RECALL -- to measure reasoning.

The first real small-model climb exposed the trap: qwen2.5-coder:1.5b "cleared" 13/15 of the
canonical ladder INCLUDING edit-distance + min-coins, yet its fizzbuzz was genuinely wrong (it
swapped Fizz/Buzz). The hard DP problems are the most-memorized code on the internet, so a high
climb there measures RECALL, not reasoning. Renaming the function and twisting the spec defeats
that: the memorized solution now fails its own hidden tests, so only a model that actually reads
the spec and reasons can clear it.

Each problem here is a deliberate variant of a canonical one (same tier/difficulty), with a fresh
name, a changed rule, and a CORRECT reference + hidden tests for the NEW spec:

  add -> weighted_sum (2a+3b)       fizzbuzz -> buzzfizz (Fizz/Buzz SWAPPED)
  maximum -> min_abs                vowel_count -> consonant_count
  is_prime -> is_perfect_square     nth_fibonacci -> tribonacci
  binary_search -> count_less       quicksort -> sort_by_abs
  is_balanced -> is_balanced_depth  lis -> longest_decreasing
  edit_distance -> weighted_edit    min_coins -> max_coins   regex -> is_subsequence

Same shape as `curriculum.CURRICULUM`, so it drops straight into `leveling.ride(curriculum=...)`
and the same hidden-test verification. The reference answer key must still clear every tier (the
problems are solvable) and the naive floor must clear none -- checked by `verify_buildable()`.

    python -m python.helm.perturbed --reference   # answer key clears all (the twists are solvable)
    python -m python.helm.perturbed --llm --model qwen2.5-coder:1.5b --curve gentle
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional, Sequence

from .curriculum import _p
from .leveling import CURVES, ride, render
from .public_bench import naive_generator, reference_generator, run_public_bench

PT1 = [  # elementary, but not the canonical one-liners
    _p(
        "p1_weighted_sum",
        "Write `weighted_sum(a, b)` returning 2*a + 3*b.",
        "def weighted_sum(a, b):\n    return 2 * a + 3 * b\n",
        ["assert weighted_sum(1, 1) == 5", "assert weighted_sum(2, 0) == 4", "assert weighted_sum(0, 1) == 3"],
    ),
    _p(
        "p1_min_abs",
        "Write `min_abs(xs)` returning the element of the non-empty list xs with the smallest absolute value.",
        "def min_abs(xs):\n    return min(xs, key=abs)\n",
        ["assert min_abs([4, -2, 7]) == -2", "assert min_abs([1, -5]) == 1", "assert min_abs([9]) == 9"],
    ),
    _p(
        "p1_count_odds",
        "Write `count_odds(xs)` returning how many integers in xs are odd.",
        "def count_odds(xs):\n    return sum(1 for x in xs if x % 2 != 0)\n",
        ["assert count_odds([1, 2, 3, 4]) == 2", "assert count_odds([2, 4]) == 0", "assert count_odds([1, 3, 5]) == 3"],
    ),
]

PT2 = [  # loops + strings, twisted
    _p(
        "p2_rotate_left",
        "Write `rotate_left(s, k)` returning string s rotated left by k positions (k may exceed len(s)).",
        "def rotate_left(s, k):\n    if not s:\n        return s\n    k %= len(s)\n    return s[k:] + s[:k]\n",
        [
            "assert rotate_left('abcd', 1) == 'bcda'",
            "assert rotate_left('abc', 3) == 'abc'",
            "assert rotate_left('', 2) == ''",
            "assert rotate_left('abcd', 5) == 'bcda'",
        ],
    ),
    _p(
        "p2_buzzfizz",
        "Write `buzzfizz(n)` returning a list for 1..n: 'Buzz' for multiples of 3, 'Fizz' for multiples of 5, "
        "'BuzzFizz' for multiples of 15, else the number as a string. (Note: Fizz/Buzz are SWAPPED from the usual.)",
        "def buzzfizz(n):\n    out = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n"
        "            out.append('BuzzFizz')\n        elif i % 3 == 0:\n            out.append('Buzz')\n"
        "        elif i % 5 == 0:\n            out.append('Fizz')\n        else:\n            out.append(str(i))\n"
        "    return out\n",
        [
            "assert buzzfizz(5) == ['1', '2', 'Buzz', '4', 'Fizz']",
            "assert buzzfizz(15)[-1] == 'BuzzFizz'",
            "assert buzzfizz(3) == ['1', '2', 'Buzz']",
        ],
    ),
    _p(
        "p2_consonant_count",
        "Write `consonant_count(s)` returning the number of lowercase consonants in s "
        "(lowercase letters a-z that are not vowels aeiou).",
        "def consonant_count(s):\n    return sum(1 for c in s if 'a' <= c <= 'z' and c not in 'aeiou')\n",
        [
            "assert consonant_count('hello') == 3",
            "assert consonant_count('aeiou') == 0",
            "assert consonant_count('xyz') == 3",
        ],
    ),
]

PT3 = [  # algorithms, twisted
    _p(
        "p3_is_perfect_square",
        "Write `is_perfect_square(n)` returning True iff n is a non-negative perfect square.",
        "def is_perfect_square(n):\n    from math import isqrt\n    return n >= 0 and isqrt(n) ** 2 == n\n",
        [
            "assert is_perfect_square(16) == True",
            "assert is_perfect_square(15) == False",
            "assert is_perfect_square(0) == True",
            "assert is_perfect_square(-4) == False",
        ],
    ),
    _p(
        "p3_tribonacci",
        "Write `tribonacci(n)` for the tribonacci sequence T0=0, T1=1, T2=1, T(n)=T(n-1)+T(n-2)+T(n-3).",
        "def tribonacci(n):\n    if n == 0:\n        return 0\n    if n in (1, 2):\n        return 1\n"
        "    a, b, c = 0, 1, 1\n    for _ in range(3, n + 1):\n        a, b, c = b, c, a + b + c\n    return c\n",
        [
            "assert tribonacci(0) == 0",
            "assert tribonacci(2) == 1",
            "assert tribonacci(3) == 2",
            "assert tribonacci(6) == 13",
        ],
    ),
    _p(
        "p3_count_less",
        "Write `count_less(xs, target)` returning how many elements of the sorted list xs are strictly less "
        "than target.",
        "def count_less(xs, target):\n    from bisect import bisect_left\n    return bisect_left(xs, target)\n",
        [
            "assert count_less([1, 3, 5, 7], 5) == 2",
            "assert count_less([1, 3, 5, 7], 4) == 2",
            "assert count_less([], 1) == 0",
            "assert count_less([2, 2, 2], 2) == 0",
        ],
    ),
]

PT4 = [  # data structures + DP, twisted
    _p(
        "p4_sort_by_abs",
        "Write `sort_by_abs(xs)` returning a new list of xs sorted by absolute value ascending (stable on ties).",
        "def sort_by_abs(xs):\n    return sorted(xs, key=abs)\n",
        [
            "assert sort_by_abs([-3, 1, 2]) == [1, 2, -3]",
            "assert sort_by_abs([]) == []",
            "assert sort_by_abs([3, -1, -2]) == [-1, -2, 3]",
        ],
    ),
    _p(
        "p4_balanced_depth",
        "Write `is_balanced_depth(s, maxd)` returning True iff the parentheses in s (only '(' and ')') are "
        "balanced AND the nesting depth never exceeds maxd.",
        "def is_balanced_depth(s, maxd):\n    d = 0\n    for ch in s:\n        if ch == '(':\n            d += 1\n"
        "            if d > maxd:\n                return False\n        elif ch == ')':\n            d -= 1\n"
        "            if d < 0:\n                return False\n    return d == 0\n",
        [
            "assert is_balanced_depth('(())', 2) == True",
            "assert is_balanced_depth('(())', 1) == False",
            "assert is_balanced_depth('(()', 5) == False",
            "assert is_balanced_depth('', 1) == True",
        ],
    ),
    _p(
        "p4_longest_decreasing",
        "Write `longest_decreasing(xs)` returning the length of the longest strictly DECREASING subsequence of xs.",
        "def longest_decreasing(xs):\n    from bisect import bisect_left\n    tails = []\n    for x in xs:\n"
        "        y = -x\n        i = bisect_left(tails, y)\n        if i == len(tails):\n            tails.append(y)\n"
        "        else:\n            tails[i] = y\n    return len(tails)\n",
        [
            "assert longest_decreasing([5, 3, 4, 1]) == 3",
            "assert longest_decreasing([1, 2, 3]) == 1",
            "assert longest_decreasing([]) == 0",
            "assert longest_decreasing([9, 8, 7]) == 3",
        ],
    ),
]

PT5 = [  # hard DP / strings, twisted
    _p(
        "p5_weighted_edit",
        "Write `weighted_edit(a, b)`: edit distance between strings a and b where insert and delete cost 1 but "
        "a SUBSTITUTION costs 2.",
        "def weighted_edit(a, b):\n    m, n = len(a), len(b)\n    dp = [[0] * (n + 1) for _ in range(m + 1)]\n"
        "    for i in range(m + 1):\n        dp[i][0] = i\n    for j in range(n + 1):\n        dp[0][j] = j\n"
        "    for i in range(1, m + 1):\n        for j in range(1, n + 1):\n            if a[i - 1] == b[j - 1]:\n"
        "                dp[i][j] = dp[i - 1][j - 1]\n            else:\n"
        "                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + 2)\n"
        "    return dp[m][n]\n",
        [
            "assert weighted_edit('abc', 'abc') == 0",
            "assert weighted_edit('a', 'b') == 2",
            "assert weighted_edit('', 'abc') == 3",
            "assert weighted_edit('cat', 'cut') == 2",
            "assert weighted_edit('ab', 'abc') == 1",
        ],
    ),
    _p(
        "p5_max_coins",
        "Write `max_coins(coins, amount)` returning the MOST coins (unlimited supply) summing exactly to amount, "
        "or -1 if impossible.",
        "def max_coins(coins, amount):\n    dp = [-1] * (amount + 1)\n    dp[0] = 0\n"
        "    for a in range(1, amount + 1):\n        best = -1\n        for c in coins:\n"
        "            if c <= a and dp[a - c] != -1:\n                best = max(best, dp[a - c] + 1)\n"
        "        dp[a] = best\n    return dp[amount]\n",
        [
            "assert max_coins([1, 2, 5], 11) == 11",
            "assert max_coins([2], 3) == -1",
            "assert max_coins([1], 0) == 0",
            "assert max_coins([2, 3], 12) == 6",
        ],
    ),
    _p(
        "p5_is_subsequence",
        "Write `is_subsequence(s, t)` returning True iff s is a subsequence of t (characters of s appear in t in "
        "order, not necessarily contiguous).",
        "def is_subsequence(s, t):\n    it = iter(t)\n    return all(c in it for c in s)\n",
        [
            "assert is_subsequence('abc', 'aXbXc') == True",
            "assert is_subsequence('axc', 'ahbgdc') == False",
            "assert is_subsequence('', 'abc') == True",
            "assert is_subsequence('abc', 'ab') == False",
        ],
    ),
]

PERTURBED_CURRICULUM: List[Dict[str, Any]] = [
    {"tier": 1, "grade": "elementary", "problems": PT1},
    {"tier": 2, "grade": "middle-school", "problems": PT2},
    {"tier": 3, "grade": "high-school", "problems": PT3},
    {"tier": 4, "grade": "undergrad", "problems": PT4},
    {"tier": 5, "grade": "grad/phd+", "problems": PT5},
]


def verify_buildable() -> Dict[str, int]:
    """The answer key must clear every problem (the twists are solvable) and naive must clear none."""
    probs = [p for t in PERTURBED_CURRICULUM for p in t["problems"]]
    ref = run_public_bench(probs, generator=reference_generator, public_k=1)
    naive = run_public_bench(probs, generator=naive_generator, public_k=1)
    return {"problems": len(probs), "reference_verified": ref["verified"], "naive_verified": naive["verified"]}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-perturbed", description="ride the RECALL-proofed (twisted) ladder")
    ap.add_argument("--reference", action="store_true", help="answer-key rider (proves the twists are solvable)")
    ap.add_argument("--naive", action="store_true", help="failing-stub rider (the floor)")
    ap.add_argument("--llm", action="store_true", help="a free local small model via helm.free_generator")
    ap.add_argument("--model", help="model id for --llm")
    ap.add_argument("--curve", choices=CURVES, default="gentle", help="the slope shape")
    ap.add_argument("--patience", type=int, default=3, help="consecutive crashes the rider survives")
    ap.add_argument("--check", action="store_true", help="just verify the ladder is buildable (ref clears, naive 0)")
    a = ap.parse_args(list(argv) if argv is not None else None)

    if a.check:
        print("PERTURBED buildable check:", verify_buildable())
        return 0
    if a.naive:
        gen = naive_generator
    elif a.llm:
        from .free_generator import make_generator

        gen = make_generator(model=a.model)
    else:
        gen = reference_generator
    r = ride(gen, curve=a.curve, patience=a.patience, curriculum=PERTURBED_CURRICULUM)
    print(render(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
