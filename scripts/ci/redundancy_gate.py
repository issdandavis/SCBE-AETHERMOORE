"""redundancy_gate: surface conceptually-redundant work BEFORE it lands.

Execution and cross-face agreement catch BROKEN code. They are blind to code that is correct but
REDUNDANT -- two parallel sessions implementing the same idea in different words (the #2422/#2423
near-collision: two "strings for loomfn" designs that almost stacked on each other). This is the
second immune system: every module declares the ONE LINE OF MATH it implements (scripts/ci/
math_claims.txt); before new work lands you check its claim against the registry and review
anything that overlaps.

    python scripts/ci/redundancy_gate.py --claim "a string is an array of character codes"
    python scripts/ci/redundancy_gate.py --audit        # find overlaps already on main

HONEST: this SURFACES likely overlaps for a human to judge -- recall over precision. It does not
decide redundancy and does not block by default. It is keyword (Jaccard) overlap on normalized
claims, so it MISSES synonyms: a claim about "text" will not match one about "strings". Keep claims
in shared vocabulary. It is a checklist with teeth, not an oracle.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Sequence, Set, Tuple

_STOP = {
    "a",
    "an",
    "the",
    "of",
    "in",
    "to",
    "is",
    "are",
    "and",
    "or",
    "with",
    "over",
    "via",
    "by",
    "for",
    "as",
    "that",
    "each",
    "its",
    "into",
    "on",
    "at",
    "be",
    "use",
    "using",
    "from",
    "it",
}


def normalize(claim: str) -> Set[str]:
    """Claim text -> the set of load-bearing keyword tokens (lowercased, stopworded, de-pluralized)."""
    out: Set[str] = set()
    for tok in re.findall(r"[a-z0-9]+", claim.lower()):
        if tok in _STOP or len(tok) <= 1:
            continue
        if len(tok) > 3 and tok.endswith("s"):  # crude singularize: strings->string, arrays->array
            tok = tok[:-1]
        out.add(tok)
    return out


def overlap(a: str, b: str) -> float:
    """Jaccard overlap of two claims' keyword sets (0.0 disjoint .. 1.0 identical)."""
    ta, tb = normalize(a), normalize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_registry(path: Path) -> List[Tuple[str, str]]:
    """Parse `<path> :: <claim>` lines (ignoring # comments and blanks)."""
    entries: List[Tuple[str, str]] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "::" not in line:
            continue
        mod, claim = line.split("::", 1)
        entries.append((mod.strip(), claim.strip()))
    return entries


def check(claim: str, registry: Sequence[Tuple[str, str]], threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """Existing claims that overlap `claim` at or above threshold, most-similar first."""
    scored = [(mod, c, overlap(claim, c)) for mod, c in registry]
    return sorted((s for s in scored if s[2] >= threshold), key=lambda s: -s[2])


def audit(registry: Sequence[Tuple[str, str]], threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """All pairs of registered claims that overlap at or above threshold (find existing redundancy)."""
    hits: List[Tuple[str, str, float]] = []
    for i in range(len(registry)):
        for j in range(i + 1, len(registry)):
            s = overlap(registry[i][1], registry[j][1])
            if s >= threshold:
                hits.append((registry[i][0], registry[j][0], s))
    return sorted(hits, key=lambda h: -h[2])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="redundancy-gate", description="surface conceptually-redundant work before it lands"
    )
    ap.add_argument("--claim", help="the one-line math claim of the work you are about to build")
    ap.add_argument("--audit", action="store_true", help="list overlapping claim pairs already on main")
    ap.add_argument("--registry", default=str(Path(__file__).with_name("math_claims.txt")))
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--strict", action="store_true", help="exit nonzero when overlaps are found (CI blocking)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    reg = load_registry(Path(a.registry))

    if a.audit:
        hits = audit(reg, a.threshold)
        for m1, m2, s in hits:
            print("  OVERLAP %.2f   %s  <->  %s" % (s, m1, m2))
        print("%d overlapping pair(s) on main (>= %.2f)" % (len(hits), a.threshold))
        return 1 if (hits and a.strict) else 0

    if a.claim:
        hits = check(a.claim, reg, a.threshold)
        if not hits:
            print("no claim on main overlaps >= %.2f -- looks new, clear to build" % a.threshold)
            return 0
        print("REVIEW -- this overlaps existing work (might be redundant before you write a line):")
        for mod, c, s in hits:
            print('  %.2f  %s\n        "%s"' % (s, mod, c))
        return 1 if a.strict else 0

    ap.error('give --claim "<one-line math>" or --audit')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
