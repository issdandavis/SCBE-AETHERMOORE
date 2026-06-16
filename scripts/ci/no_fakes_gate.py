#!/usr/bin/env python3
"""No-new-fakes gate.

Fails CI when stub / fake / placeholder code appears in the real product path
*outside the recorded baseline*. The point is a ratchet: the existing known
fakes are recorded once in ``no_fakes_baseline.txt`` so the gate fails only on
NEW ones. As real fixes land (Wave 1/2), delete the corresponding baseline
lines so the allowance shrinks toward zero — and the system can never quietly
regrow a stub.

Usage:
    python scripts/ci/no_fakes_gate.py                 # gate (exit 1 on new fakes)
    python scripts/ci/no_fakes_gate.py --update-baseline   # re-record the baseline

What it flags (high-signal tells the system-reality audit actually found):
    - "not for production" / "use liboqs" / "in production, use ..." IOUs
    - "simplified for demo" / "for demo, create" placeholders
    - "development stub" / "dev placeholder for ML-DSA/ML-KEM"
    - "pseudo-code", "always returns true" (fake verify), fake/stub/dummy crypto
    - raise NotImplementedError on a reachable path
    - TODO/FIXME that defer real crypto/impl

It is deliberately comment/marker oriented: the cheapest, highest-signal tell of
a fake is the apologetic comment the author left next to it. Genuine cases can be
allow-listed by adding their key to the baseline with a justification.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Real product code only. Tests/demos/examples are excluded — a fake there is a
# fixture, not a shipped lie.
SCAN_DIRS = ["src", "python", "agents", "hydra", "packages", "scbe.py"]
EXCLUDE_PARTS = {
    "node_modules", "dist", "build", "__pycache__", ".git", ".venv", "venv",
    "tests", "test", "__tests__", "demos", "examples", "scbe-aethermoore",
    "fixtures", "mocks", "__mocks__", "vendor",
}
EXTS = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"}

PATTERNS = [
    ("not_for_production", re.compile(r"not\s+for\s+production", re.I)),
    ("use_liboqs", re.compile(r"\buse\s+liboqs\b", re.I)),
    ("in_prod_use", re.compile(r"in\s+production[,:\s].{0,40}\b(use|replace|swap|switch)\b", re.I)),
    ("simplified_demo", re.compile(r"simplified\s+(for\s+demo|encryption|version|implementation)", re.I)),
    ("for_demo", re.compile(r"\bfor\s+demo\b|\bdemo[,:]\s*(create|use|return|only)", re.I)),
    ("dev_stub", re.compile(r"development\s+stub|dev\s+placeholder|placeholder\s+for\s+(ml-dsa|ml-kem|kyber|dilithium)", re.I)),
    ("pseudo", re.compile(r"pseudo-?code", re.I)),
    ("always_true", re.compile(r"always\s+(returns?\s+)?true", re.I)),
    ("not_implemented", re.compile(r"\braise\s+NotImplementedError\b")),
    ("todo_impl", re.compile(r"#.{0,4}(TODO|FIXME).{0,50}\b(implement|real|crypto|sign|encrypt|verify|liboqs|kyber|dilithium)\b", re.I)),
    ("fake_marker", re.compile(r"\b(fake|stub|mock|dummy)\b.{0,30}\b(crypto|sign|encrypt|verif|key|impl|aead|kem|dsa)", re.I)),
]


def iter_files():
    for top in SCAN_DIRS:
        p = REPO / top
        if p.is_file() and p.suffix in EXTS:
            yield p
            continue
        if not p.is_dir():
            continue
        for f in p.rglob("*"):
            if f.suffix not in EXTS:
                continue
            if any(part in EXCLUDE_PARTS for part in f.relative_to(REPO).parts):
                continue
            yield f


def scan() -> dict:
    """Return {stable_key: 'path:line [id] text'} for every tell found."""
    hits: dict = {}
    for f in iter_files():
        rel = f.relative_to(REPO).as_posix()
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for pid, rx in PATTERNS:
                if rx.search(line):
                    norm = re.sub(r"\s+", " ", line.strip())[:200]
                    digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
                    # key is line-position independent (path + pattern + content hash)
                    key = f"{rel}::{pid}::{digest}"
                    hits[key] = f"{rel}:{lineno} [{pid}] {norm}"
    return hits


def load_baseline(path: Path) -> set:
    if not path.exists():
        return set()
    keys = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        keys.add(ln.split("  #", 1)[0].strip())
    return keys


def write_baseline(path: Path, hits: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# no-fakes baseline — known existing fakes/stubs in the real product path.",
        "# The gate fails on any tell NOT listed here, so new fakes cannot land.",
        "# RATCHET: when you make one of these real (or fail-closed), DELETE its line.",
        "# Regenerate with: python scripts/ci/no_fakes_gate.py --update-baseline",
        "",
    ]
    body = [f"{k}  # {v}" for k, v in sorted(hits.items())]
    path.write_text("\n".join(header + body) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="No-new-fakes gate.")
    ap.add_argument("--update-baseline", action="store_true", help="re-record the baseline from the current tree")
    ap.add_argument("--baseline", default=str(REPO / "scripts" / "ci" / "no_fakes_baseline.txt"))
    args = ap.parse_args()
    bpath = Path(args.baseline)

    hits = scan()
    if args.update_baseline:
        write_baseline(bpath, hits)
        print(f"baseline written: {len(hits)} known tells -> {bpath.relative_to(REPO).as_posix()}")
        return 0

    baseline = load_baseline(bpath)
    new = {k: v for k, v in hits.items() if k not in baseline}
    cleared = baseline - set(hits)

    if new:
        print(f"NO-FAKES GATE FAILED — {len(new)} new stub/fake tell(s) not in the baseline:\n")
        for k in sorted(new):
            print("  + " + hits[k])
        print(
            "\nMake it real, or fail closed (raise instead of returning a plausible value).\n"
            "If this is genuinely legitimate, add the key to scripts/ci/no_fakes_baseline.txt\n"
            "with a one-line justification comment."
        )
        return 1

    print(f"no-fakes gate: OK — {len(hits)} known tells, all baselined; {len(cleared)} previously-baselined now removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
