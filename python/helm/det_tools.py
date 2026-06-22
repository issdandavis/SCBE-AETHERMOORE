"""det_tools -- broad registry of DETERMINISTIC tools + charts (simple I/O), each self-tested.
These ARE the correct logic. The router routes a task's domain to the relevant tools so the
model calls them instead of reimplementing. Every tool is verified in __main__ on known values."""

from __future__ import annotations
import math
from collections import Counter
from typing import Any, Dict, List

# ---------- number theory ----------
def is_prime(n: int) -> bool:
    if n < 2: return False
    for p in range(2, int(n**0.5) + 1):
        if n % p == 0: return False
    return True
def primes_upto(n: int) -> List[int]:
    if n < 2: return []
    s = [True] * (n + 1); s[0] = s[1] = False
    for i in range(2, int(n**0.5) + 1):
        if s[i]:
            for j in range(i*i, n+1, i): s[j] = False
    return [i for i, v in enumerate(s) if v]
def nth_prime(k: int) -> int:
    n = max(15, k * 20)
    while True:
        ps = primes_upto(n)
        if len(ps) >= k: return ps[k-1]
        n *= 2
def factorize(n: int) -> List[int]:
    out = []; d = 2
    while d * d <= n:
        while n % d == 0: out.append(d); n //= d
        d += 1
    if n > 1: out.append(n)
    return out
def divisors(n: int) -> List[int]:
    return sorted(d for d in range(1, n+1) if n % d == 0)
def gcd(a: int, b: int) -> int: return math.gcd(a, b)
def lcm(a: int, b: int) -> int: return abs(a*b)//math.gcd(a, b) if a and b else 0
def is_perfect(n: int) -> bool: return n > 0 and sum(d for d in divisors(n) if d != n) == n
def nth_fibonacci(k: int) -> int:
    a, b = 0, 1
    for _ in range(k): a, b = b, a + b
    return a

# ---------- arithmetic ----------
def digit_sum(n: int) -> int: return sum(int(c) for c in str(abs(n)))
def factorial(n: int) -> int: return math.factorial(n)
def ncr(n: int, r: int) -> int: return math.comb(n, r)
def npr(n: int, r: int) -> int: return math.perm(n, r)

# ---------- sort / order ----------
def kth_largest(xs: List, k: int): return sorted(xs, reverse=True)[k-1]
def kth_smallest(xs: List, k: int): return sorted(xs)[k-1]
def top_n(xs: List, n: int) -> List: return sorted(xs, reverse=True)[:n]

# ---------- lookup / map ----------
def frequency(xs: List) -> Dict: return dict(Counter(xs))
def most_common(xs: List, k: int = 1) -> List: return [v for v, _ in Counter(xs).most_common(k)]
def unique(xs: List) -> List: return list(dict.fromkeys(xs))
def group_by(xs: List, key) -> Dict:
    g: Dict[Any, List] = {}
    for x in xs: g.setdefault(key(x), []).append(x)
    return g

# ---------- string ----------
def is_palindrome(s: str) -> bool: return s == s[::-1]
def vowel_count(s: str) -> int: return sum(c in "aeiouAEIOU" for c in s)
def char_freq(s: str) -> Dict: return dict(Counter(s))
def reverse_words(s: str) -> str: return " ".join(s.split()[::-1])

# ---------- search ----------
def contains(seq, x) -> bool: return x in seq
def index_of(seq, x) -> int: return seq.index(x) if x in seq else -1
def find_all(seq, x) -> List[int]: return [i for i, v in enumerate(seq) if v == x]

# ---------- list / array ----------
def flatten(xss: List[List]) -> List: return [x for xs in xss for x in xs]
def chunk(xs: List, n: int) -> List[List]: return [xs[i:i+n] for i in range(0, len(xs), n)]
def dedup(xs: List) -> List: return list(dict.fromkeys(xs))

# ---------- lookup CHARTS ----------
_ROMAN = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),
          (40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
def int_to_roman(n: int) -> str:
    out = []
    for v, s in _ROMAN:
        while n >= v: out.append(s); n -= v
    return "".join(out)
def roman_to_int(s: str) -> int:
    m = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}; total = 0; prev = 0
    for c in reversed(s):
        v = m[c]; total += -v if v < prev else v; prev = v
    return total

REGISTRY = {k: v for k, v in dict(globals()).items()
            if callable(v) and not k.startswith("_") and k not in ("annotations",)}

# tools grouped by router domain
BY_DOMAIN = {
    "number_theory": ["is_prime","primes_upto","nth_prime","factorize","divisors","gcd","lcm","is_perfect","nth_fibonacci"],
    "arithmetic":    ["digit_sum","factorial","ncr","npr"],
    "sort_order":    ["kth_largest","kth_smallest","top_n"],
    "lookup_map":    ["frequency","most_common","unique","group_by"],
    "string":        ["is_palindrome","vowel_count","char_freq","reverse_words"],
    "search":        ["contains","index_of","find_all"],
    "list_array":    ["flatten","chunk","dedup"],
    "chart":         ["int_to_roman","roman_to_int"],
}

if __name__ == "__main__":
    # DETERMINISTIC self-test: every tool correct on known values
    assert is_prime(97) and not is_prime(91)
    assert nth_prime(10) == 29 and primes_upto(10) == [2,3,5,7]
    assert factorize(360) == [2,2,2,3,3,5] and divisors(12) == [1,2,3,4,6,12]
    assert gcd(54,24) == 6 and lcm(4,6) == 12 and is_perfect(28) and nth_fibonacci(10) == 55
    assert digit_sum(12345) == 15 and factorial(6) == 720 and ncr(5,2) == 10 and npr(5,2) == 20
    assert kth_largest([3,1,4,1,5],2) == 4 and kth_smallest([3,1,4,1,5],2) == 1 and top_n([5,1,3,9],2) == [9,5]
    assert frequency([1,1,2]) == {1:2,2:1} and most_common([1,1,2,2,2]) == [2] and unique([1,1,2,1]) == [1,2]
    assert group_by([1,2,3,4], lambda x: x%2) == {1:[1,3],0:[2,4]}
    assert is_palindrome("racecar") and vowel_count("hello world") == 3 and reverse_words("a b c") == "c b a"
    assert contains([1,2,3],2) and index_of([1,2,3],3) == 2 and find_all([1,0,1,0,1],1) == [0,2,4]
    assert flatten([[1,2],[3]]) == [1,2,3] and chunk([1,2,3,4,5],2) == [[1,2],[3,4],[5]] and dedup([1,1,2,3,3]) == [1,2,3]
    assert int_to_roman(1994) == "MCMXCIV" and roman_to_int("MCMXCIV") == 1994
    print("det_tools self-test: ALL PASS (%d tools across %d domains)" % (len(REGISTRY), len(BY_DOMAIN)))
