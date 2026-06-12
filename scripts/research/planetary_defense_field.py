#!/usr/bin/env python3
"""planetary_defense_field — the solar system as a defense-in-depth graph.

The user's model: security can't hide in the math (once they learn the system
they abuse it), so you build a planet — hard core of primitives/crypto, a molten
mantle of functional math, hot magma of cost/pressure — and you want to SEE the
invader "entering the solar system," far from the core, not feel them at the
center.

This builds that as a graph FIELD and asks the real questions:
  - which shells actually absorb the threats (Sun, gas giants, inner planets,
    Moon, magnetosphere, atmosphere)?
  - "from the other side": does a shell cover all approach vectors or only the
    solid angle it happens to occupy?
  - at what RATE does each shell absorb, by threat class?

The numbers are order-of-magnitude, grounded in real astronomy and labelled as
estimates — the POINT is the structure, and the structure carries a lesson that
inverts the intuition. Then it maps each cosmic shell onto a security shell so
the real "greatest system ever made" gives the architecture its alignment.

No dependencies. Run:  python scripts/research/planetary_defense_field.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

# Threat classes — different sizes die at different shells. This is the crux:
# no single shell handles all of them.
THREAT_CLASSES = ("radiation", "dust", "small", "medium", "catastrophic")
THREAT_DESC = {
    "radiation": "charged particles / solar wind / CME / cosmic rays",
    "dust": "micrometeoroids, < ~1 m — ablate to nothing",
    "small": "meteorites ~1 m – 25 m — mostly burn, rare ground hit",
    "medium": "~25 m – 1 km — regional devastation (Tunguska, Chelyabinsk)",
    "catastrophic": "> ~1 km asteroids / long-period comets — global",
}
# Rough relative INCOMING flux by count entering Earth's neighbourhood (a power
# law: tiny things are overwhelmingly common). Normalised, by count.
INCOMING_FLUX = {
    "radiation": 1.0,  # treated separately (continuous, not a "count")
    "dust": 1.0,  # ~10^8/day class events dominate by count
    "small": 1e-4,
    "medium": 1e-8,
    "catastrophic": 1e-12,
}


@dataclass
class Shell:
    """One orbital shell. coverage = fraction of approach solid angle it guards
    (1.0 = omnidirectional; small = a directional body that only blocks the
    sliver of sky it occupies). absorb = fraction of the threats THAT HIT IT
    which it stops, per class. effective stop = coverage * absorb."""

    name: str
    kind: str  # "field" | "body" | "shell"
    coverage: float
    absorb: dict = field(default_factory=dict)
    note: str = ""

    def stop_fraction(self, threat: str) -> float:
        return self.coverage * self.absorb.get(threat, 0.0)


# Outer -> inner. Honest astronomy: the dramatic outer bodies are MODEST or
# mythical at the population level; the thin, close, omnidirectional atmosphere
# is the real workhorse.
SHELLS = [
    Shell(
        "sun_gravity_well",
        "field",
        coverage=1.0,
        absorb={"catastrophic": 0.30, "medium": 0.05},
        note="omnidirectional gravitational sink: ejects/captures bodies over long times, "
        "removes sungrazers. Shapes every trajectory — it is the FIELD, not a wall.",
    ),
    Shell(
        "gas_giants",  # Jupiter + Saturn
        "body",
        coverage=0.02,
        absorb={"catastrophic": 0.50},
        note="the 'cosmic vacuum cleaner' — DEBATED: deflects some long-period comets "
        "(SL-9 took a hit 1994) but also injects some inward. Modest, directional, tail-only.",
    ),
    Shell(
        "inner_planets",  # Venus, Mercury between a given threat and Earth
        "body",
        coverage=0.001,
        absorb={"catastrophic": 0.5, "medium": 0.5, "small": 0.5},
        note="negligible as shields — tiny solid angle, rarely between Earth and a threat. "
        "~0 population-level protection. The 'planets between us' intuition is basically empty.",
    ),
    Shell(
        "moon",
        "body",
        coverage=0.0074,  # cross-section ratio (R_moon/R_earth)^2, and only its sliver of sky
        absorb={"catastrophic": 1.0, "medium": 1.0, "small": 1.0, "dust": 1.0},
        note="WITNESS, not shield: cratered face proves it takes hits, but it guards <1% of "
        "Earth-bound flux (small cross-section, far away, one direction). Myth-buster.",
    ),
    Shell(
        "magnetosphere",
        "shell",
        coverage=0.95,
        absorb={"radiation": 0.99},
        note="omnidirectional (bar polar cusps): deflects charged particles / solar wind / CME. "
        "Handles a WHOLE THREAT CLASS the rock-shields cannot touch. Different class, own shell.",
    ),
    Shell(
        "atmosphere",
        "shell",
        coverage=1.0,
        absorb={"dust": 0.99999, "small": 0.999, "medium": 0.30, "radiation": 0.5},
        note="THE WORKHORSE: thin, close, omnidirectional. Ablates ~all dust and small bodies "
        "(>99.9% by count). Cheapest layer, kills the overwhelming majority. Punched through only "
        "by the rare medium/catastrophic class.",
    ),
]

# Cosmic shell -> security shell. The alignment the user asked for.
SECURITY_ALIGNMENT = [
    (
        "sun_gravity_well",
        "the cost FIELD itself — the harmonic wall H(d)=exp(d^2). "
        "Omnidirectional pressure that bends every trajectory; not a gate, the shape of space.",
    ),
    (
        "gas_giants",
        "rare-catastrophic interceptor — governance escalation / big-model / human "
        "review. Expensive, occasional, reserved for the civilization-ender tail. Don't fire it on dust.",
    ),
    (
        "inner_planets",
        "incidental third-party defenses you cannot count on (a vendor WAF, luck). "
        "Real but ~0 at population scale — never architect on them.",
    ),
    (
        "moon",
        "a SIGNATURE for one known attack: covers only the vector it occupies. A witness/"
        "tripwire, not a shield. Useful as a sensor, fatal as a primary defense.",
    ),
    (
        "magnetosphere",
        "the always-on filter for one pervasive class (prompt-injection / encoding "
        "tampering) — omnidirectional, cheap, handles a class the others can't see.",
    ),
    (
        "atmosphere",
        "the cheap omnidirectional INPUT FILTER: sanitize/validate every input regardless "
        "of attack shape. Kills 99.9% at the perimeter for almost no cost. INVEST HERE FIRST.",
    ),
]

LESSONS = [
    "Omnidirectional shells (atmosphere, magnetosphere, the gravity field) beat directional bodies "
    "(planets, Moon) — a defense you can only point one way leaves an undefended hemisphere. "
    "'From the other side' is exactly where directional shields fail.",
    "Most threats die cheap and close, not dramatic and far: the thin atmosphere stops >99.9% by "
    "count; Jupiter and the Moon are modest or mythical. Don't over-build the glamorous perimeter "
    "and assume it caught everything — instrument the cheap inner filter and measure where threats "
    "actually die.",
    "One shell per threat CLASS. No single layer covers radiation AND dust AND km-comets. Match the "
    "layer to the class; the gravity field shapes all, the atmosphere eats the many small, the "
    "giant catches the rare large.",
    "The math is public (gravity, ablation are textbook) and the planet is still safe — because "
    "safety is layered COST + omnidirectional coverage + early sight, not a secret formula. "
    "Kerckhoffs at planetary scale.",
]


def run() -> dict:
    rows = []
    # cascade: a threat of each class runs the gauntlet outer->inner; track survival
    survival = {t: 1.0 for t in THREAT_CLASSES}
    per_shell = {}
    for shell in SHELLS:
        stopped_here = {}
        for t in THREAT_CLASSES:
            before = survival[t]
            killed = before * shell.stop_fraction(t)
            survival[t] = before - killed
            stopped_here[t] = killed
        per_shell[shell.name] = {
            "kind": shell.kind,
            "coverage": shell.coverage,
            "omnidirectional": shell.coverage >= 0.9,
            "stopped": stopped_here,
            "note": shell.note,
        }
        rows.append((shell.name, stopped_here))

    # who does the most work, weighted by incoming flux (by count)
    work = {}
    for name, stopped in rows:
        w = sum(stopped[t] * INCOMING_FLUX[t] for t in THREAT_CLASSES if t != "radiation")
        work[name] = w
    total_work = sum(work.values()) or 1.0
    work_share = {k: v / total_work for k, v in work.items()}

    return {
        "schema": "planetary_defense_field_v1",
        "threat_classes": {t: THREAT_DESC[t] for t in THREAT_CLASSES},
        "per_shell": per_shell,
        "residual_reaching_core": survival,
        "work_share_by_count": work_share,
        "security_alignment": [{"shell": s, "maps_to": m} for s, m in SECURITY_ALIGNMENT],
        "lessons": LESSONS,
    }


def _bar(frac: float, width: int = 28) -> str:
    n = int(round(frac * width))
    return "#" * n + "-" * (width - n)


def print_human(r: dict) -> None:
    print("=== planetary defense field — solar system as defense-in-depth ===\n")
    print("threat classes (by incoming count, tiny things vastly more common):")
    for t, d in r["threat_classes"].items():
        print(f"  {t:13s} {d}")
    print("\nshells, outer -> inner  (coverage = fraction of approach sky guarded):")
    for name, info in r["per_shell"].items():
        tag = "OMNI" if info["omnidirectional"] else f"dir {info['coverage']*100:5.2f}% sky"
        print(f"\n  [{tag:13s}] {name}  ({info['kind']})")
        print(f"     {info['note']}")
    print("\n--- who actually does the work (share of threats stopped, weighted by count) ---")
    for name, share in sorted(r["work_share_by_count"].items(), key=lambda kv: -kv[1]):
        print(f"  {name:18s} |{_bar(share)}| {share*100:5.1f}%")
    print("\n--- residual reaching the surface/core, per class (1.0 = nothing stopped it) ---")
    for t, s in r["residual_reaching_core"].items():
        print(f"  {t:13s} {s:.6f}  {'<- punches through' if s > 0.5 else ''}")
    print("\n--- alignment: cosmic shell -> security shell ---")
    for a in r["security_alignment"]:
        print(f"  {a['shell']:18s} -> {a['maps_to']}")
    print("\n--- lessons (the alignment) ---")
    for i, line in enumerate(r["lessons"], 1):
        print(f"  {i}. {line}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="planetary_defense_field")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = run()
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print_human(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
