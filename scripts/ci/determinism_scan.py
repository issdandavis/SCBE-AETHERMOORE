#!/usr/bin/env python3
"""determinism_scan: static audit of the code-gen path for the 6 sources of non-determinism.

The runtime benchmark (scripts/bench/codegen_determinism.py) proved the emitters are byte-reproducible on
their current inputs. This is the complementary STATIC check: it scans the source for LATENT risks the
current inputs may not trigger -- the 6 classic sources (unseeded RNG, wall-clock in logic, threads,
external I/O, global mutable state, unordered-collection iteration).

It is a HEURISTIC review aid, not a prover. It classifies each hit RISK vs BENIGN (injected `rng` param,
perf_counter timing, code inside a demo/main/bench function, I/O confined to a boundary module). The CORE
code-gen modules (the emitters + the all-at-once substrate) MUST be RISK-clean -- a RISK there fails the
scan (exit 1). Risks elsewhere are reported as informational (the correct architecture puts I/O, threads,
and audit timestamps at the BOUNDARY, determinism in the core).

    PYTHONPATH=. python scripts/ci/determinism_scan.py    # exit 1 if a core code generator has a risk
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

REPO = Path(__file__).resolve().parents[2]

# the modules that MUST be deterministic (emitters + the all-at-once coding substrate)
CORE_CODEGEN = {
    "polyglot.py",
    "loomfn.py",
    "loomflow.py",
    "instrument.py",
    "tongue_isa.py",
    "bicameral.py",
    "coding_board.py",
    "coding_board_gates.py",
    "coding_squad.py",
    "observer_dynamics.py",
    "allatonce_observer.py",
    "reversible_circuit.py",
    "elastic_bijective_hash.py",
}
SCAN_DIRS = [REPO / "python" / "scbe", REPO / "python" / "helm"]

_RNG = "|".join(["random", "randint", "randrange", "choice", "choices", "shuffle", "sample", "uniform", "getrandbits"])
CHECKS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("unseeded-RNG", re.compile(r"\brandom\.(%s)\b|\brandom\.Random\(\s*\)|\bnp\.random\.(?!seed\b)\w+" % _RNG)),
    ("wall-clock", re.compile(r"\b(datetime\.now\(|datetime\.utcnow\(|time\.time\(|date\.today\()")),
    (
        "concurrency",
        re.compile(r"\b(threading\.|multiprocessing\.|concurrent\.futures|asyncio\.gather)|[^.\w]Thread\("),
    ),
    ("external-I/O", re.compile(r"\b(requests\.(get|post|put|delete)|urllib\.request|socket\.socket|http\.client)\b")),
    ("global-mutable", re.compile(r"^\s*global\s+[A-Za-z_]\w*(\s*,\s*[A-Za-z_]\w*)*\s*(#.*)?$")),
    ("unordered-iter", re.compile(r"for\s+\w+\s+in\s+set\(|for\s+\w+\s+in\s+\{[^}]+\}")),
]

_DEMOISH = ("demo", "main", "bench", "example", "_test", "selftest", "self_test")
# modules whose JOB is the boundary -- I/O / threads / timestamps there are correct, not a code-gen bug
_BOUNDARY = {
    "free_generator.py",
    "host_capability.py",
    "public_bench.py",
    "geometric_scheduler.py",
    "ask.py",
    "encode_corpus.py",
    "ingestion_rights.py",
    "reaction_state.py",
    "semantic_gate.py",
    "phdm_embedding.py",
}


def benign_reason(category: str, line: str, path: Path, func: str) -> str:
    """Non-empty reason if this hit is mitigated/irrelevant; else '' (a real risk to review)."""
    in_bench = "bench" in str(path).lower() or "scripts" in path.parts
    demoish = any(d in func.lower() for d in _DEMOISH)
    if category == "wall-clock":
        if "perf_counter" in line or "monotonic" in line:
            return "perf timing"
        if in_bench or demoish:
            return "timing in demo/bench"
        if path.name in _BOUNDARY:
            return "audit timestamp at a boundary module"
    if category == "unseeded-RNG":
        if re.search(r"random\.Random\(\s*[^)\s]", line) or ".seed(" in line or "default_rng(" in line:
            return "seeded RNG"
        if in_bench or demoish:
            return "demo/bench data generation"
    if category in ("concurrency", "external-I/O"):
        if in_bench or demoish:
            return "in demo/bench"
        if path.name in _BOUNDARY:
            return "confined to a boundary module"
    return ""


def scan() -> int:
    findings = []  # (path, lineno, category, text, benign_reason)
    for d in SCAN_DIRS:
        for f in sorted(d.rglob("*.py")):
            if "__pycache__" in str(f) or f.name.startswith("test_"):
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            func = ""
            for i, line in enumerate(lines, 1):
                m = re.match(r"^\s*def\s+(\w+)", line)
                if m:
                    func = m.group(1)
                if line.lstrip().startswith("#"):
                    continue
                for category, pat in CHECKS:
                    if pat.search(line):
                        findings.append((f, i, category, line.strip()[:90], benign_reason(category, line, f, func)))

    risks = [x for x in findings if not x[4]]
    benign = [x for x in findings if x[4]]
    core_risks = [x for x in risks if x[0].name in CORE_CODEGEN]

    print("DETERMINISM SCAN -- code-gen path (python/scbe, python/helm)\n")
    print("  total hits: %d  (RISK-to-review: %d, benign/mitigated: %d)\n" % (len(findings), len(risks), len(benign)))

    print("  == RISK (review) -- non-determinism the architecture should keep at the boundary ==")
    for path, ln, cat, text, _ in risks:
        tag = "  <CORE!>" if path.name in CORE_CODEGEN else ""
        print("    [%-13s]%s %s:%d  %s" % (cat, tag, path.relative_to(REPO), ln, text))
    if not risks:
        print("    (none)")

    print("\n  == benign / mitigated (informational) ==")
    by_cat: dict = {}
    for _p, _l, cat, _t, reason in benign:
        by_cat.setdefault(cat, {})
        by_cat[cat][reason] = by_cat[cat].get(reason, 0) + 1
    for cat, reasons in sorted(by_cat.items()):
        print("    %-13s %s" % (cat, ", ".join("%dx %s" % (n, r) for r, n in reasons.items())))

    print("\n  == CORE code-gen modules (MUST be RISK-clean) ==")
    if core_risks:
        print("    FAIL -- %d latent non-determinism risk(s) in core code generators:" % len(core_risks))
        for path, ln, cat, text, _ in core_risks:
            print("      %s:%d [%s] %s" % (path.name, ln, cat, text))
        return 1
    print("    PASS -- no latent non-determinism source in the core code generators.")
    print("    (runtime benchmark already proved them byte-reproducible; this confirms no source-level risk)")
    return 0


if __name__ == "__main__":
    raise SystemExit(scan())
