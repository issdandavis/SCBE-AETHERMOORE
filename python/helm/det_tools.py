"""det_tools -- broad registry of DETERMINISTIC tools + charts (simple I/O), each self-tested.
These ARE the correct logic. The router routes a task's domain to the relevant tools so the
model calls them instead of reimplementing. Every tool is verified in __main__ on known values."""

from __future__ import annotations
import math
import re
import calendar as _cal
import statistics as _stats
from datetime import date
from collections import Counter
from typing import Any, Dict, List


# ---------- number theory ----------
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for p in range(2, int(n**0.5) + 1):
        if n % p == 0:
            return False
    return True


def primes_upto(n: int) -> List[int]:
    if n < 2:
        return []
    s = [True] * (n + 1)
    s[0] = s[1] = False
    for i in range(2, int(n**0.5) + 1):
        if s[i]:
            for j in range(i * i, n + 1, i):
                s[j] = False
    return [i for i, v in enumerate(s) if v]


def nth_prime(k: int) -> int:
    n = max(15, k * 20)
    while True:
        ps = primes_upto(n)
        if len(ps) >= k:
            return ps[k - 1]
        n *= 2


def factorize(n: int) -> List[int]:
    out = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def divisors(n: int) -> List[int]:
    return sorted(d for d in range(1, n + 1) if n % d == 0)


def gcd(a: int, b: int) -> int:
    return math.gcd(a, b)


def lcm(a: int, b: int) -> int:
    return abs(a * b) // math.gcd(a, b) if a and b else 0


def is_perfect(n: int) -> bool:
    return n > 0 and sum(d for d in divisors(n) if d != n) == n


def nth_fibonacci(k: int) -> int:
    a, b = 0, 1
    for _ in range(k):
        a, b = b, a + b
    return a


# ---------- arithmetic ----------
def digit_sum(n: int) -> int:
    return sum(int(c) for c in str(abs(n)))


def factorial(n: int) -> int:
    return math.factorial(n)


def ncr(n: int, r: int) -> int:
    return math.comb(n, r)


def npr(n: int, r: int) -> int:
    return math.perm(n, r)


# ---------- sort / order ----------
def kth_largest(xs: List, k: int):
    return sorted(xs, reverse=True)[k - 1]


def kth_smallest(xs: List, k: int):
    return sorted(xs)[k - 1]


def top_n(xs: List, n: int) -> List:
    return sorted(xs, reverse=True)[:n]


# ---------- lookup / map ----------
def frequency(xs: List) -> Dict:
    return dict(Counter(xs))


def most_common(xs: List, k: int = 1) -> List:
    return [v for v, _ in Counter(xs).most_common(k)]


def unique(xs: List) -> List:
    return list(dict.fromkeys(xs))


def group_by(xs: List, key) -> Dict:
    g: Dict[Any, List] = {}
    for x in xs:
        g.setdefault(key(x), []).append(x)
    return g


# ---------- string ----------
def is_palindrome(s: str) -> bool:
    return s == s[::-1]


def vowel_count(s: str) -> int:
    return sum(c in "aeiouAEIOU" for c in s)


def char_freq(s: str) -> Dict:
    return dict(Counter(s))


def reverse_words(s: str) -> str:
    return " ".join(s.split()[::-1])


# ---------- search ----------
def contains(seq, x) -> bool:
    return x in seq


def index_of(seq, x) -> int:
    return seq.index(x) if x in seq else -1


def find_all(seq, x) -> List[int]:
    return [i for i, v in enumerate(seq) if v == x]


# ---------- list / array ----------
def flatten(xss: List[List]) -> List:
    return [x for xs in xss for x in xs]


def chunk(xs: List, n: int) -> List[List]:
    return [xs[i : i + n] for i in range(0, len(xs), n)]


def dedup(xs: List) -> List:
    return list(dict.fromkeys(xs))


# ---------- calendar / dates ----------
def is_leap_year(y: int) -> bool:
    return _cal.isleap(y)


def days_in_month(y: int, m: int) -> int:
    return _cal.monthrange(y, m)[1]


def weekday_name(y: int, m: int, d: int) -> str:
    return _cal.day_name[date(y, m, d).weekday()]


def days_between(y1: int, m1: int, d1: int, y2: int, m2: int, d2: int) -> int:
    return abs((date(y2, m2, d2) - date(y1, m1, d1)).days)


# ---------- unit conversions ----------
def c_to_f(c: float) -> float:
    return round(c * 9 / 5 + 32, 4)


def f_to_c(f: float) -> float:
    return round((f - 32) * 5 / 9, 4)


def c_to_k(c: float) -> float:
    return round(c + 273.15, 4)


def km_to_miles(km: float) -> float:
    return round(km * 0.621371, 4)


def miles_to_km(mi: float) -> float:
    return round(mi / 0.621371, 4)


def kg_to_lb(kg: float) -> float:
    return round(kg * 2.20462, 4)


def lb_to_kg(lb: float) -> float:
    return round(lb / 2.20462, 4)


def m_to_ft(m: float) -> float:
    return round(m * 3.28084, 4)


def ft_to_m(ft: float) -> float:
    return round(ft / 3.28084, 4)


# ---------- base conversions ----------
def to_binary(n: int) -> str:
    return format(n, "b")


def to_hex(n: int) -> str:
    return format(n, "x")


def to_octal(n: int) -> str:
    return format(n, "o")


def from_base(s: str, b: int) -> int:
    return int(s, b)


# ---------- validation / patterns ----------
_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def is_valid_email(s: str) -> bool:
    return bool(_EMAIL.match(s.strip()))


def extract_numbers(s: str) -> List[int]:
    return [int(x) for x in re.findall(r"-?\d+", s)]


def extract_floats(s: str) -> List[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]


# ---------- statistics ----------
def mean(xs: List[float]) -> float:
    return round(_stats.mean(xs), 6)


def median(xs: List[float]) -> float:
    return _stats.median(xs)


def mode(xs: List):
    return _stats.mode(xs)


def stdev(xs: List[float]) -> float:
    return round(_stats.pstdev(xs), 6)


def variance(xs: List[float]) -> float:
    return round(_stats.pvariance(xs), 6)


def data_range(xs: List[float]):
    return max(xs) - min(xs)


def percentile(xs: List[float], q: float) -> float:
    if not xs:
        raise ValueError("percentile needs at least one value")
    if q < 0 or q > 100:
        raise ValueError("percentile q must be between 0 and 100")
    ordered = sorted(float(x) for x in xs)
    if len(ordered) == 1:
        return round(ordered[0], 6)
    pos = (len(ordered) - 1) * (q / 100.0)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return round(ordered[lo], 6)
    frac = pos - lo
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * frac, 6)


def weighted_mean(xs: List[float], weights: List[float]) -> float:
    if len(xs) != len(weights):
        raise ValueError("values and weights must have the same length")
    total = sum(float(w) for w in weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    return round(sum(float(x) * float(w) for x, w in zip(xs, weights)) / total, 6)


def correlation(xs: List[float], ys: List[float]):
    if len(xs) != len(ys):
        raise ValueError("series must have the same length")
    if len(xs) < 2:
        return None
    x = [float(v) for v in xs]
    y = [float(v) for v in ys]
    xm = sum(x) / len(x)
    ym = sum(y) / len(y)
    xd = [v - xm for v in x]
    yd = [v - ym for v in y]
    xv = sum(v * v for v in xd)
    yv = sum(v * v for v in yd)
    if xv <= 0 or yv <= 0:
        return None
    return round(sum(a * b for a, b in zip(xd, yd)) / math.sqrt(xv * yv), 6)


# ---------- geometry ----------
def area_circle(r: float) -> float:
    return round(math.pi * r * r, 6)


def area_rectangle(w: float, h: float) -> float:
    return w * h


def area_triangle(b: float, h: float) -> float:
    return 0.5 * b * h


def circumference(r: float) -> float:
    return round(2 * math.pi * r, 6)


def hypotenuse(a: float, b: float) -> float:
    return round(math.hypot(a, b), 6)


# ---------- matrix ----------
def transpose(m: List[List]) -> List[List]:
    return [list(row) for row in zip(*m)]


def matmul(a: List[List], b: List[List]) -> List[List]:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def identity(n: int) -> List[List[int]]:
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


# ---------- ascii / char ----------
def char_code(c: str) -> int:
    return ord(c)


def from_code(n: int) -> str:
    return chr(n)


# ---------- lookup CHARTS ----------
_ROMAN = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]


def int_to_roman(n: int) -> str:
    out = []
    for v, s in _ROMAN:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def roman_to_int(s: str) -> int:
    m = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for c in reversed(s):
        v = m[c]
        total += -v if v < prev else v
        prev = v
    return total


REGISTRY = {
    k: v for k, v in dict(globals()).items() if callable(v) and not k.startswith("_") and k not in ("annotations",)
}

BY_DOMAIN = {
    "number_theory": [
        "is_prime",
        "primes_upto",
        "nth_prime",
        "factorize",
        "divisors",
        "gcd",
        "lcm",
        "is_perfect",
        "nth_fibonacci",
    ],
    "arithmetic": ["digit_sum", "factorial", "ncr", "npr"],
    "sort_order": ["kth_largest", "kth_smallest", "top_n"],
    "lookup_map": ["frequency", "most_common", "unique", "group_by"],
    "string": ["is_palindrome", "vowel_count", "char_freq", "reverse_words"],
    "search": ["contains", "index_of", "find_all"],
    "list_array": ["flatten", "chunk", "dedup"],
    "calendar": ["is_leap_year", "days_in_month", "weekday_name", "days_between"],
    "conversion": [
        "c_to_f",
        "f_to_c",
        "c_to_k",
        "km_to_miles",
        "miles_to_km",
        "kg_to_lb",
        "lb_to_kg",
        "m_to_ft",
        "ft_to_m",
    ],
    "base": ["to_binary", "to_hex", "to_octal", "from_base"],
    "validate": ["is_valid_email", "extract_numbers", "extract_floats"],
    "statistics": [
        "mean",
        "median",
        "mode",
        "stdev",
        "variance",
        "data_range",
        "percentile",
        "weighted_mean",
        "correlation",
    ],
    "geometry": ["area_circle", "area_rectangle", "area_triangle", "circumference", "hypotenuse"],
    "matrix": ["transpose", "matmul", "identity"],
    "ascii": ["char_code", "from_code"],
    "chart": ["int_to_roman", "roman_to_int"],
}

if __name__ == "__main__":
    assert is_prime(97) and not is_prime(91)
    assert nth_prime(10) == 29 and primes_upto(10) == [2, 3, 5, 7]
    assert factorize(360) == [2, 2, 2, 3, 3, 5] and divisors(12) == [1, 2, 3, 4, 6, 12]
    assert gcd(54, 24) == 6 and lcm(4, 6) == 12 and is_perfect(28) and nth_fibonacci(10) == 55
    assert digit_sum(12345) == 15 and factorial(6) == 720 and ncr(5, 2) == 10 and npr(5, 2) == 20
    assert (
        kth_largest([3, 1, 4, 1, 5], 2) == 4
        and kth_smallest([3, 1, 4, 1, 5], 2) == 1
        and top_n([5, 1, 3, 9], 2) == [9, 5]
    )
    assert (
        frequency([1, 1, 2]) == {1: 2, 2: 1} and most_common([1, 1, 2, 2, 2]) == [2] and unique([1, 1, 2, 1]) == [1, 2]
    )
    assert group_by([1, 2, 3, 4], lambda x: x % 2) == {1: [1, 3], 0: [2, 4]}
    assert is_palindrome("racecar") and vowel_count("hello world") == 3 and reverse_words("a b c") == "c b a"
    assert contains([1, 2, 3], 2) and index_of([1, 2, 3], 3) == 2 and find_all([1, 0, 1, 0, 1], 1) == [0, 2, 4]
    assert (
        flatten([[1, 2], [3]]) == [1, 2, 3]
        and chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
        and dedup([1, 1, 2, 3, 3]) == [1, 2, 3]
    )
    # new domains
    assert is_leap_year(2024) and not is_leap_year(2023) and days_in_month(2024, 2) == 29
    assert weekday_name(2024, 1, 1) == "Monday" and days_between(2024, 1, 1, 2024, 1, 11) == 10
    assert c_to_f(100) == 212.0 and f_to_c(32) == 0.0 and c_to_k(0) == 273.15
    assert km_to_miles(1) == 0.6214 and miles_to_km(1) == 1.6093 and kg_to_lb(1) == 2.2046
    assert to_binary(10) == "1010" and to_hex(255) == "ff" and to_octal(8) == "10" and from_base("ff", 16) == 255
    assert is_valid_email("a@b.com") and not is_valid_email("a@b") and extract_numbers("got 3 of 10") == [3, 10]
    assert extract_floats("x=-1.5 y 2 z 3.25") == [-1.5, 2.0, 3.25]
    assert int_to_roman(1994) == "MCMXCIV" and roman_to_int("MCMXCIV") == 1994
    # statistics / geometry / matrix / ascii
    assert mean([1, 2, 3, 4]) == 2.5 and median([1, 3, 2]) == 2 and mode([1, 1, 2]) == 1 and data_range([1, 9, 3]) == 8
    assert stdev([2, 4, 4, 4, 5, 5, 7, 9]) == 2.0 and variance([2, 4, 4, 4, 5, 5, 7, 9]) == 4.0
    assert percentile([10, 20, 30, 40], 25) == 17.5 and weighted_mean([0, 1, 1], [3, 1, 1]) == 0.4
    assert correlation([1, 2, 3], [2, 4, 6]) == 1.0 and correlation([1, 1, 1], [2, 4, 6]) is None
    assert area_circle(1) == round(math.pi, 6) and area_rectangle(3, 4) == 12 and area_triangle(6, 8) == 24.0
    assert circumference(1) == round(2 * math.pi, 6) and hypotenuse(3, 4) == 5.0
    assert transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]] and matmul([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [
        [19, 22],
        [43, 50],
    ]
    assert identity(2) == [[1, 0], [0, 1]] and char_code("A") == 65 and from_code(97) == "a"
    print("det_tools self-test: ALL PASS (%d tools across %d domains)" % (len(REGISTRY), len(BY_DOMAIN)))
