"""curriculum: a graded coding ladder (elementary -> PhD+) for measuring whether ANY ai can
climb it -- the smallest local model, a sub-agent, or a frontier model -- through the SAME
hidden-test verification used by the forge loop.

The idea (Issac's framing): the substrate is a board where every move is legal-by-construction;
the open question is whether grouping models against *real graded goals* shows the mapping helps.
You can't answer that with one benchmark at one difficulty -- you need a ladder, run the same way
from grade-school to research-hard, so "how far did it climb" becomes a number you can compare
across models and across substrates.

This is the measuring stick, not the climber. A climber is any `generator(problem) -> source`
(public_bench.Generator): the dataset answer-key (proves the ladder is solvable + the hidden tests
are real), the naive stub (the floor -- should clear nothing), a free local model via
helm.free_generator, or a sub-agent. Plug it into the same slot; the ladder doesn't change.

Each problem ships its own asserts; public_bench splits them into one PUBLIC example (the climber
may see it) and HIDDEN checks (held out), run in a sandboxed subprocess. A tier is "cleared" only
if every problem in it passes hidden checks, and the climb is the highest *contiguous* tier cleared
from the bottom -- you don't get a PhD by acing the PhD test while failing 3rd-grade arithmetic.

    python -m python.helm.curriculum --reference   # answer key: clears every tier (ladder is real)
    python -m python.helm.curriculum --naive        # the floor: clears nothing
    python -m python.helm.curriculum --llm           # a free local model (helm.free_generator)
"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Optional, Sequence

from .public_bench import Generator, naive_generator, reference_generator, run_public_bench


def _p(task_id: str, prompt: str, code: str, tests: Sequence[str]) -> Dict[str, Any]:
    return {"task_id": task_id, "prompt": prompt, "code": code, "test_list": list(tests), "test_imports": []}


# --- the ladder: 5 tiers, each 3 problems with a correct reference + real hidden tests ----------
# Reference solutions are deliberately complete (they ARE the answer key); the asserts are what
# define behaviour for any other climber.

TIER_1 = [  # elementary: arithmetic / one-liners
    _p(
        "t1_add",
        "Write a function `add(a, b)` that returns the sum of a and b.",
        "def add(a, b):\n    return a + b\n",
        ["assert add(2, 3) == 5", "assert add(-1, 1) == 0", "assert add(0, 0) == 0"],
    ),
    _p(
        "t1_maximum",
        "Write a function `maximum(xs)` that returns the largest number in the non-empty list xs.",
        "def maximum(xs):\n    m = xs[0]\n    for x in xs:\n        if x > m:\n            m = x\n    return m\n",
        ["assert maximum([1, 2, 3]) == 3", "assert maximum([5]) == 5", "assert maximum([-3, -1, -2]) == -1"],
    ),
    _p(
        "t1_count_evens",
        "Write a function `count_evens(xs)` that returns how many integers in xs are even.",
        "def count_evens(xs):\n    return sum(1 for x in xs if x % 2 == 0)\n",
        [
            "assert count_evens([1, 2, 3, 4]) == 2",
            "assert count_evens([2, 4, 6]) == 3",
            "assert count_evens([1, 3, 5]) == 0",
        ],
    ),
]

TIER_2 = [  # middle school: loops + strings
    _p(
        "t2_reverse",
        "Write a function `reverse_string(s)` that returns s reversed.",
        "def reverse_string(s):\n    return s[::-1]\n",
        [
            "assert reverse_string('abc') == 'cba'",
            "assert reverse_string('') == ''",
            "assert reverse_string('a') == 'a'",
        ],
    ),
    _p(
        "t2_fizzbuzz",
        "Write a function `fizzbuzz(n)` returning a list for 1..n: 'Fizz' for multiples of 3, 'Buzz' for 5, "
        "'FizzBuzz' for 15, else the number as a string.",
        "def fizzbuzz(n):\n    out = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n"
        "            out.append('FizzBuzz')\n        elif i % 3 == 0:\n            out.append('Fizz')\n"
        "        elif i % 5 == 0:\n            out.append('Buzz')\n        else:\n            out.append(str(i))\n"
        "    return out\n",
        [
            "assert fizzbuzz(5) == ['1', '2', 'Fizz', '4', 'Buzz']",
            "assert fizzbuzz(15)[-1] == 'FizzBuzz'",
            "assert fizzbuzz(3) == ['1', '2', 'Fizz']",
        ],
    ),
    _p(
        "t2_vowels",
        "Write a function `vowel_count(s)` that returns the number of lowercase vowels (aeiou) in s.",
        "def vowel_count(s):\n    return sum(1 for c in s if c in 'aeiou')\n",
        ["assert vowel_count('hello') == 2", "assert vowel_count('xyz') == 0", "assert vowel_count('aeiou') == 5"],
    ),
]

TIER_3 = [  # high school: classic algorithms
    _p(
        "t3_is_prime",
        "Write a function `is_prime(n)` returning True iff n is a prime number.",
        "def is_prime(n):\n    if n < 2:\n        return False\n    i = 2\n    while i * i <= n:\n"
        "        if n % i == 0:\n            return False\n        i += 1\n    return True\n",
        [
            "assert is_prime(2) == True",
            "assert is_prime(15) == False",
            "assert is_prime(13) == True",
            "assert is_prime(1) == False",
        ],
    ),
    _p(
        "t3_fib",
        "Write a function `nth_fibonacci(n)` returning the n-th Fibonacci number (0-indexed: 0, 1, 1, 2, ...).",
        "def nth_fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
        [
            "assert nth_fibonacci(0) == 0",
            "assert nth_fibonacci(1) == 1",
            "assert nth_fibonacci(10) == 55",
            "assert nth_fibonacci(7) == 13",
        ],
    ),
    _p(
        "t3_bsearch",
        "Write a function `binary_search(xs, target)` returning the index of target in the sorted list xs, or -1.",
        "def binary_search(xs, target):\n    lo, hi = 0, len(xs) - 1\n    while lo <= hi:\n"
        "        mid = (lo + hi) // 2\n        if xs[mid] == target:\n            return mid\n"
        "        if xs[mid] < target:\n            lo = mid + 1\n"
        "        else:\n            hi = mid - 1\n    return -1\n",
        [
            "assert binary_search([1, 3, 5, 7], 5) == 2",
            "assert binary_search([1, 3, 5, 7], 4) == -1",
            "assert binary_search([], 1) == -1",
            "assert binary_search([2], 2) == 0",
        ],
    ),
]

TIER_4 = [  # undergrad: data structures + DP
    _p(
        "t4_quicksort",
        "Write a function `quicksort(xs)` that returns a new sorted list (ascending) from xs.",
        "def quicksort(xs):\n    if len(xs) <= 1:\n        return list(xs)\n    p = xs[len(xs) // 2]\n"
        "    less = [x for x in xs if x < p]\n    eq = [x for x in xs if x == p]\n    gr = [x for x in xs if x > p]\n"
        "    return quicksort(less) + eq + quicksort(gr)\n",
        [
            "assert quicksort([3, 1, 2]) == [1, 2, 3]",
            "assert quicksort([]) == []",
            "assert quicksort([5, 5, 1]) == [1, 5, 5]",
            "assert quicksort([9, -1, 4, 4, 2]) == [-1, 2, 4, 4, 9]",
        ],
    ),
    _p(
        "t4_balanced",
        "Write a function `is_balanced(s)` returning True iff the brackets in s (only ()[]{}) are balanced.",
        "def is_balanced(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    st = []\n    for ch in s:\n"
        "        if ch in '([{':\n            st.append(ch)\n        elif ch in pairs:\n"
        "            if not st or st.pop() != pairs[ch]:\n                return False\n    return not st\n",
        [
            "assert is_balanced('()[]{}') == True",
            "assert is_balanced('(]') == False",
            "assert is_balanced('([{}])') == True",
            "assert is_balanced('(') == False",
            "assert is_balanced('') == True",
        ],
    ),
    _p(
        "t4_lis",
        "Write a function `lis_length(xs)` returning the length of the longest strictly increasing subsequence.",
        "def lis_length(xs):\n    import bisect\n    tails = []\n"
        "    for x in xs:\n        i = bisect.bisect_left(tails, x)\n"
        "        if i == len(tails):\n            tails.append(x)\n        else:\n            tails[i] = x\n"
        "    return len(tails)\n",
        [
            "assert lis_length([10, 9, 2, 5, 3, 7, 101, 18]) == 4",
            "assert lis_length([0, 1, 0, 3, 2, 3]) == 4",
            "assert lis_length([7, 7, 7]) == 1",
            "assert lis_length([]) == 0",
        ],
    ),
]

TIER_5 = [  # grad / PhD+: harder DP + recursion
    _p(
        "t5_edit_distance",
        "Write a function `edit_distance(a, b)` returning the Levenshtein edit distance between strings a and b.",
        "def edit_distance(a, b):\n    m, n = len(a), len(b)\n    dp = list(range(n + 1))\n"
        "    for i in range(1, m + 1):\n        prev = dp[0]\n        dp[0] = i\n        for j in range(1, n + 1):\n"
        "            cur = dp[j]\n            if a[i - 1] == b[j - 1]:\n                dp[j] = prev\n"
        "            else:\n                dp[j] = 1 + min(prev, dp[j], dp[j - 1])\n"
        "            prev = cur\n    return dp[n]\n",
        [
            "assert edit_distance('kitten', 'sitting') == 3",
            "assert edit_distance('', 'abc') == 3",
            "assert edit_distance('abc', 'abc') == 0",
            "assert edit_distance('horse', 'ros') == 3",
        ],
    ),
    _p(
        "t5_min_coins",
        "Write a function `min_coins(coins, amount)` returning the fewest coins summing to amount, "
        "or -1 if impossible.",
        "def min_coins(coins, amount):\n    INF = float('inf')\n    dp = [0] + [INF] * amount\n"
        "    for a in range(1, amount + 1):\n        for c in coins:\n"
        "            if c <= a and dp[a - c] + 1 < dp[a]:\n"
        "                dp[a] = dp[a - c] + 1\n    return dp[amount] if dp[amount] != INF else -1\n",
        [
            "assert min_coins([1, 2, 5], 11) == 3",
            "assert min_coins([2], 3) == -1",
            "assert min_coins([1], 0) == 0",
            "assert min_coins([1, 5, 10, 25], 30) == 2",
        ],
    ),
    _p(
        "t5_regex",
        "Write a function `is_match(s, p)` for regex matching where '.' matches any char and '*' matches zero or "
        "more of the preceding element. The match must cover the ENTIRE string s.",
        "def is_match(s, p):\n    from functools import lru_cache\n\n    @lru_cache(None)\n    def dp(i, j):\n"
        "        if j == len(p):\n            return i == len(s)\n        first = i < len(s) and p[j] in (s[i], '.')\n"
        "        if j + 1 < len(p) and p[j + 1] == '*':\n            return dp(i, j + 2) or (first and dp(i + 1, j))\n"
        "        return first and dp(i + 1, j + 1)\n\n    return dp(0, 0)\n",
        [
            "assert is_match('aa', 'a') == False",
            "assert is_match('aa', 'a*') == True",
            "assert is_match('ab', '.*') == True",
            "assert is_match('mississippi', 'mis*is*p*.') == False",
            "assert is_match('aab', 'c*a*b') == True",
        ],
    ),
]

CURRICULUM = [
    {"tier": 1, "grade": "elementary", "problems": TIER_1},
    {"tier": 2, "grade": "middle-school", "problems": TIER_2},
    {"tier": 3, "grade": "high-school", "problems": TIER_3},
    {"tier": 4, "grade": "undergrad", "problems": TIER_4},
    {"tier": 5, "grade": "grad/phd+", "problems": TIER_5},
]


def run_curriculum(
    generator: Generator = reference_generator,
    public_k: int = 1,
    tiers: Sequence[Dict[str, Any]] = CURRICULUM,
) -> Dict[str, Any]:
    """Run a climber up the ladder. A tier is cleared only if every problem passes hidden checks;
    the climb is the highest CONTIGUOUS tier cleared from the bottom."""
    per_tier: List[Dict[str, Any]] = []
    for t in tiers:
        s = run_public_bench(t["problems"], generator=generator, public_k=public_k)
        per_tier.append(
            {
                "tier": t["tier"],
                "grade": t["grade"],
                "attempted": s["attempted"],
                "verified": s["verified"],
                "overfit_caught": s["overfit_caught"],
                "cleared": s["attempted"] > 0 and s["verified"] == s["attempted"],
                "pass_rate": s["pass_rate"],
            }
        )
    climb = 0
    for r in per_tier:
        if r["cleared"]:
            climb = r["tier"]
        else:
            break
    cleared_grade = next((r["grade"] for r in per_tier if r["tier"] == climb), "none")
    return {
        "generator": generator.__name__,
        "public_k": public_k,
        "highest_tier_cleared": climb,
        "highest_grade_cleared": cleared_grade,
        "total_verified": sum(r["verified"] for r in per_tier),
        "total_problems": sum(r["attempted"] for r in per_tier),
        "tiers": per_tier,
    }


def render(summary: Dict[str, Any]) -> str:
    lines = [
        "CURRICULUM CLIMB  (graded ladder, hidden-test verified)",
        f"  climber: {summary['generator']}   public_k: {summary['public_k']}",
    ]
    for r in summary["tiers"]:
        bar = "#" * r["verified"] + "." * (r["attempted"] - r["verified"])
        mark = "PASS" if r["cleared"] else ""
        of = f"  overfit:{r['overfit_caught']}" if r["overfit_caught"] else ""
        lines.append(
            "  T%d %-13s %d/%d  %-6s %-4s%s" % (r["tier"], r["grade"], r["verified"], r["attempted"], bar, mark, of)
        )
    lines.append(
        "  --> cleared through T%d (%s);  total solved %d/%d"
        % (
            summary["highest_tier_cleared"],
            summary["highest_grade_cleared"],
            summary["total_verified"],
            summary["total_problems"],
        )
    )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-curriculum", description="grade a code climber on the difficulty ladder")
    ap.add_argument("--reference", action="store_true", help="answer-key climber (proves the ladder is solvable)")
    ap.add_argument("--naive", action="store_true", help="failing-stub climber (the floor)")
    ap.add_argument("--llm", action="store_true", help="a free OpenAI-compatible model via helm.free_generator")
    ap.add_argument("--public-k", type=int, default=1, help="asserts shown to the climber (rest hidden)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    if a.naive:
        gen = naive_generator
    elif a.llm:
        from .free_generator import make_generator

        gen = make_generator()
    else:
        gen = reference_generator
    print(render(run_curriculum(generator=gen, public_k=a.public_k)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
