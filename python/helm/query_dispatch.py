"""query_dispatch -- route a tool-shaped question STRAIGHT to a deterministic tool.
No model guessing: parse the query -> match a rule -> call the det_tools function ->
return the answer. The strong lever (use the source directly). Falls through to None
when no rule matches (then the model/router handles it). Nesting: a result can feed
cond()/if-then for simple chained queries."""

from __future__ import annotations
import re
from typing import Any, Dict, Optional
try:
    from . import det_tools as T
except ImportError:  # run as a script
    import det_tools as T

# (regex, tool_name, args-from-match) -- the input->tool map with simple I/O
_RULES = [
    (r"\bis\s+(\d+)\s+(?:a\s+)?prime\b",                 "is_prime",       lambda m: (int(m[1]),)),
    (r"\b(\d+)\s*(?:st|nd|rd|th)\s+prime\b",             "nth_prime",      lambda m: (int(m[1]),)),
    (r"\bprimes?\s+(?:up\s*to|below|under|less than)\s+(\d+)", "primes_upto", lambda m: (int(m[1]),)),
    (r"\b(?:prime\s+)?factor(?:ize|s|ization)?\s+(?:of\s+)?(\d+)", "factorize", lambda m: (int(m[1]),)),
    (r"\bdivisors?\s+of\s+(\d+)\b",                      "divisors",       lambda m: (int(m[1]),)),
    (r"\bgcd\s+of\s+(\d+)\s+and\s+(\d+)",                "gcd",            lambda m: (int(m[1]), int(m[2]))),
    (r"\blcm\s+of\s+(\d+)\s+and\s+(\d+)",                "lcm",            lambda m: (int(m[1]), int(m[2]))),
    (r"\bis\s+(\d+)\s+(?:a\s+)?perfect\b",               "is_perfect",     lambda m: (int(m[1]),)),
    (r"\b(\d+)\s*(?:st|nd|rd|th)?\s+fibonacci\b",        "nth_fibonacci",  lambda m: (int(m[1]),)),
    (r"\bfactorial\s+of\s+(\d+)",                        "factorial",      lambda m: (int(m[1]),)),
    (r"\b(\d+)\s+choose\s+(\d+)\b",                      "ncr",            lambda m: (int(m[1]), int(m[2]))),
    (r"\bdigit\s+sum\s+of\s+(\d+)",                      "digit_sum",      lambda m: (int(m[1]),)),
    (r"\broman\s+(?:numeral\s+)?(?:of|for)\s+(\d+)",     "int_to_roman",   lambda m: (int(m[1]),)),
    (r"\b([IVXLCDM]+)\s+(?:in|to|as)\s+(?:a\s+)?(?:number|integer|arabic|decimal)", "roman_to_int", lambda m: (m[1].upper(),)),
    (r"\bis\s+['\"]?(\w+)['\"]?\s+a\s+palindrome",       "is_palindrome",  lambda m: (m[1],)),
    (r"\bvowels?\s+(?:count\s+)?(?:in|of)\s+['\"]?([\w ]+)['\"]?", "vowel_count", lambda m: (m[1].strip(),)),
    (r"\bis\s+(\d{3,4})\s+a\s+leap\s+year",              "is_leap_year",   lambda m: (int(m[1]),)),
    (r"\b(-?\d+(?:\.\d+)?)\s*(?:degrees?\s*)?c(?:elsius)?\s+(?:to|in)\s+f", "c_to_f", lambda m: (float(m[1]),)),
    (r"\b(-?\d+(?:\.\d+)?)\s*(?:degrees?\s*)?f(?:ahrenheit)?\s+(?:to|in)\s+c", "f_to_c", lambda m: (float(m[1]),)),
    (r"\b(-?\d+(?:\.\d+)?)\s*km\s+(?:to|in)\s+miles?",   "km_to_miles",    lambda m: (float(m[1]),)),
    (r"\b(-?\d+(?:\.\d+)?)\s*miles?\s+(?:to|in)\s+km",   "miles_to_km",    lambda m: (float(m[1]),)),
    (r"\bbinary\s+(?:of|for)\s+(\d+)",                   "to_binary",      lambda m: (int(m[1]),)),
    (r"\b(\d+)\s+(?:to|in)\s+binary",                    "to_binary",      lambda m: (int(m[1]),)),
    (r"\bhex(?:adecimal)?\s+(?:of|for)\s+(\d+)",         "to_hex",         lambda m: (int(m[1]),)),
    (r"\b(\d+)\s+(?:to|in)\s+hex(?:adecimal)?",          "to_hex",         lambda m: (int(m[1]),)),
    (r"\b(\d+)\s+(?:to|in)\s+octal",                     "to_octal",       lambda m: (int(m[1]),)),
]


def dispatch(query: str) -> Optional[Dict[str, Any]]:
    """Return {answer, tool, args, deterministic:True} if a tool answers the query, else None."""
    for pat, tool, argf in _RULES:
        m = re.search(pat, query, re.I)
        if m:
            try:
                args = argf(m)
                ans = T.REGISTRY[tool](*args)
                return {"answer": ans, "tool": tool, "args": args, "deterministic": True}
            except Exception:
                continue
    return None  # no tool fits -> fall through to model/router


if __name__ == "__main__":
    cases = [
        ("what is the 10th prime?", 29),
        ("is 97 prime", True),
        ("primes up to 10", [2, 3, 5, 7]),
        ("gcd of 54 and 24", 6),
        ("lcm of 4 and 6", 12),
        ("divisors of 12", [1, 2, 3, 4, 6, 12]),
        ("is 28 a perfect number", True),
        ("the 10th fibonacci", 55),
        ("factorial of 6", 720),
        ("5 choose 2", 10),
        ("digit sum of 12345", 15),
        ("roman numeral for 1994", "MCMXCIV"),
        ("MCMXCIV to a number", 1994),
        ("is 'racecar' a palindrome", True),
        ("vowels in 'hello world'", 3),
        ("is 2024 a leap year", True),
        ("100 c to f", 212.0),
        ("32 f to c", 0.0),
        ("5 km to miles", 3.1069),
        ("binary of 10", "1010"),
        ("255 to hex", "ff"),
        ("8 in octal", "10"),
    ]
    ok = 0
    for q, exp in cases:
        r = dispatch(q)
        got = r["answer"] if r else None
        if got == exp:
            ok += 1
        else:
            print("MISS:", q, "-> got", got, "want", exp, "(tool=%s)" % (r and r.get("tool")))
    print("query_dispatch self-test: %d/%d routed straight to a tool, no model" % (ok, len(cases)))
    print("falls through to model on a non-tool task:", dispatch("write a function that reverses a linked list") is None)
