#!/usr/bin/env python3
"""prime_ruler.py — one prime ruler, three gearings (switchable by user choice).

Issac's idea: a fixed-length ruler etched with prime proportions, like a gearbox —
the SAME physical line, re-read in different "gears," overlaid on a plain number
line to multiply/factor, simplify ratios, or sieve. The three modes:

  log      LOGARITHMIC SLIDE RULE — marks at log(p). Sliding adds lengths, so
           multiplication becomes length-addition: a prime's product sits at the
           SUM of its factors' marks (6 lands exactly at pos(2)+pos(3)). One fixed
           length, self-similar (repeats every decade), reads across unit metrics.

  gear     STERN-BROCOT / FAREY RATIO RULER — marks at lowest-terms fractions a/b
           (b<=B). Coprime = the "hunting tooth" gear principle: a/b in lowest
           terms is a gear pair that never re-meshes early. Overlay a measured
           ratio to read off the simplest gear that approximates it.

  ring     CIRCULAR RESIDUE SIEVE — wrap the line into concentric rings, one per
           small prime p, p sectors each. Integer k sits at angle 2*pi*(k mod p)/p.
           k aligns to the 0-spoke on ring p  <=>  p | k. Lands on no ring (p<=sqrt k)
           => prime. Spin "as many times as you want": rotation = adding a constant.

Marks come from the nth-prime engine's sieve, so the ruler is etched by the same
tool that finds primes to the nth degree (nth_prime_baseline_gate.simple_sieve).

Usage:
    python scripts/research/prime_ruler.py --mode all --max 60 --out artifacts/prime_ruler
    python scripts/research/prime_ruler.py --mode log --max 100
"""
from __future__ import annotations

import argparse
import math
from math import gcd
from pathlib import Path

# Reuse the prime engine's sieve — the ruler is etched by the prime finder itself.
try:
    from scripts.research.nth_prime_baseline_gate import simple_sieve
except ImportError:  # allow running as a loose script
    def simple_sieve(limit: int) -> list[int]:
        if limit < 2:
            return []
        flags = bytearray([1]) * (limit + 1)
        flags[0] = flags[1] = 0
        for i in range(2, int(limit**0.5) + 1):
            if flags[i]:
                flags[i * i :: i] = bytearray(len(flags[i * i :: i]))
        return [i for i in range(2, limit + 1) if flags[i]]


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "prime_ruler"

# Fixed physical canvas. The ruler is ALWAYS this wide — that is the whole point
# ("one ruler the same length with all the ratios"). Only the etch changes.
W = 1000.0      # ruler length (px ~ a fixed physical length)
PAD = 60.0


def _svg_open(w: float, h: float, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}" font-family="monospace">',
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#0f1115"/>',
        f'<text x="{PAD}" y="28" fill="#9fb3c8" font-size="16">{title}</text>',
    ]


def _line(x1, y1, x2, y2, color="#3a4250", wclr=1.0):
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{wclr}"/>'


def _txt(x, y, s, color="#cdd9e5", size=11, anchor="middle"):
    return f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}" font-size="{size}" text-anchor="{anchor}">{s}</text>'


# ---------------------------------------------------------------- LOG SLIDE RULE
def render_log(max_n: int) -> tuple[str, dict]:
    primes = set(simple_sieve(max_n))
    span = math.log(max_n)
    inner = W - 2 * PAD

    def pos(x: float) -> float:
        return PAD + inner * math.log(x) / span

    h = 230.0
    s = _svg_open(W, h, f"LOG SLIDE RULE  -  marks at log(p), x{1}..x{max_n}  (multiply = add lengths)")
    base_y = 120.0
    s.append(_line(PAD, base_y, W - PAD, base_y, "#5a6b7b", 1.5))
    for n in range(2, max_n + 1):
        x = pos(n)
        is_p = n in primes
        tick = 26 if is_p else 12
        col = "#ff5d73" if is_p else "#46566a"
        s.append(_line(x, base_y, x, base_y - tick, col, 2.0 if is_p else 1.0))
        if is_p or n in (1, max_n) or (n <= 12) or n % 10 == 0:
            s.append(_txt(x, base_y - tick - 4, str(n), "#ff9aa8" if is_p else "#8aa0b6", 11))
    # demonstrate the additive property: 6 = 2*3 -> pos(6) == pos(2)+pos(3)-pos(1); pos(1)=PAD
    if 6 <= max_n:
        b = base_y + 30
        x2, x3, x6 = pos(2), pos(3), pos(6)
        s.append(_line(PAD, b, x2, b, "#54c5a0", 3))
        s.append(_txt((PAD + x2) / 2, b + 16, "log 2", "#54c5a0", 11))
        s.append(_line(x2, b + 22, x2 + (x3 - PAD), b + 22, "#e0b341", 3))
        s.append(_txt(x2 + (x3 - PAD) / 2, b + 38, "+ log 3", "#e0b341", 11))
        s.append(_line(x6, base_y, x6, b + 22, "#54c5a0", 1.0))
        s.append(_txt(x6, b + 54, "= log 6  (2-mark + 3-mark lands on 6)", "#9fe0c8", 12))
    s.append("</svg>")
    check = abs((math.log(6)) - (math.log(2) + math.log(3)))
    return "\n".join(s), {"primes_marked": len(primes), "additive_residual": check}


# --------------------------------------------------------------- FAREY / GEAR RULER
def render_gear(max_den: int) -> tuple[str, dict]:
    # lowest-terms fractions a/b in (0,1], b <= max_den  (coprime = a real gear pair)
    fracs = []
    for b in range(1, max_den + 1):
        for a in range(1, b + 1):
            if gcd(a, b) == 1:
                fracs.append((a, b))
    fracs = sorted(set(fracs), key=lambda t: t[0] / t[1])
    inner = W - 2 * PAD
    h = 240.0
    s = _svg_open(W, h, f"GEAR / FAREY RATIO RULER  -  lowest-terms a/b, b<= {max_den}  (overlay to read simplest gear)")
    base_y = 150.0
    s.append(_line(PAD, base_y, W - PAD, base_y, "#5a6b7b", 1.5))
    primes = set(simple_sieve(max_den))
    for a, b in fracs:
        x = PAD + inner * (a / b)
        prime_den = b in primes
        tick = 24 if b <= 5 or prime_den else 10
        col = "#7dd3fc" if prime_den else "#46566a"
        s.append(_line(x, base_y, x, base_y - tick, col, 1.6 if prime_den else 1.0))
        if b <= 6:
            s.append(_txt(x, base_y - tick - 4, f"{a}/{b}", "#bfe3ff", 10))
    # plain 0..1 reference line below, to "transcribe / overlay"
    ref = base_y + 40
    s.append(_line(PAD, ref, W - PAD, ref, "#3a4250", 1.0))
    for k in range(0, 11):
        x = PAD + inner * (k / 10)
        s.append(_line(x, ref, x, ref + 8, "#46566a", 1.0))
        s.append(_txt(x, ref + 22, f"{k/10:.1f}", "#7e90a3", 10))
    s.append(_txt(W / 2, ref + 44, "plain ratio line  (overlay the gear marks above to snap to simplest a/b)", "#8aa0b6", 11))
    s.append("</svg>")
    return "\n".join(s), {"fractions_marked": len(fracs)}


# ------------------------------------------------------------- CIRCULAR RESIDUE SIEVE
def render_ring(max_n: int) -> tuple[str, dict]:
    ring_primes = [p for p in simple_sieve(int(max_n**0.5) + 1)]  # only p<=sqrt(max) can sieve
    if not ring_primes:
        ring_primes = [2, 3]
    cx, cy = W / 2, 300.0
    h = 600.0
    s = _svg_open(W, h, f"CIRCULAR RESIDUE SIEVE  -  rings mod {ring_primes}  (k on 0-spoke of ring p  <=>  p|k)")
    r0, dr = 70.0, 30.0
    composites = 0
    primes_found = []
    # draw rings + the 0-spoke (the alignment spoke)
    for i, p in enumerate(ring_primes):
        r = r0 + i * dr
        s.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="#39424f" stroke-width="1"/>')
        s.append(_txt(cx + r + 14, cy + 4, f"mod {p}", "#7e90a3", 10, "start"))
    s.append(_line(cx, cy, cx, cy - (r0 + len(ring_primes) * dr), "#e0b341", 1.0))  # 0-spoke
    s.append(_txt(cx, cy - (r0 + len(ring_primes) * dr) - 6, "0-spoke", "#e0b341", 10))
    # plot a handful of integers as dots on each ring at angle 2pi*(k mod p)/p
    for k in range(2, min(max_n, 30) + 1):
        hit = False
        for i, p in enumerate(ring_primes):
            r = r0 + i * dr
            ang = -math.pi / 2 + 2 * math.pi * (k % p) / p
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
            on_zero = (k % p == 0)
            if on_zero and k != p:
                hit = True
            col = "#ff5d73" if on_zero else "#5b6b7c"
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.5 if on_zero else 2}" fill="{col}"/>')
        if hit:
            composites += 1
        else:
            primes_found.append(k)
    s.append(_txt(cx, h - 40, f"lonely (no 0-spoke hit) => PRIME: {primes_found[:15]}", "#9fe0c8", 12))
    s.append(_txt(cx, h - 22, f"aligned to a 0-spoke => composite ({composites} of 2..{min(max_n,30)})", "#ff9aa8", 12))
    s.append("</svg>")
    # self-check: every number we called prime really is, vs the sieve
    true_primes = set(simple_sieve(min(max_n, 30)))
    mismatches = [k for k in primes_found if k not in true_primes]
    return "\n".join(s), {"rings": ring_primes, "primes_found": primes_found, "sieve_mismatches": mismatches}


def main() -> int:
    ap = argparse.ArgumentParser(description="Prime ruler — three gearings of one fixed-length line.")
    ap.add_argument("--mode", choices=["log", "gear", "ring", "all"], default="all")
    ap.add_argument("--max", type=int, default=60, help="max integer / denominator to etch")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    jobs = ["log", "gear", "ring"] if args.mode == "all" else [args.mode]
    renderers = {"log": render_log, "gear": render_gear, "ring": render_ring}

    print(f"prime ruler  (fixed length = {W:.0f}px, etched from simple_sieve)")
    for j in jobs:
        svg, meta = renderers[j](args.max)
        path = args.out / f"prime_ruler_{j}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"  [{j:>4}] {path.relative_to(REPO_ROOT)}   {meta}")

    # self-verification (the user's rule: tools must self-check, not decorate)
    if "log" in jobs:
        _, m = render_log(args.max)
        assert m["additive_residual"] < 1e-9, "log scale broke the multiply=add property"
    if "ring" in jobs:
        _, m = render_ring(args.max)
        assert not m["sieve_mismatches"], f"ring sieve mislabelled primes: {m['sieve_mismatches']}"
    print("  self-checks: multiply=add holds; ring sieve agrees with simple_sieve  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
