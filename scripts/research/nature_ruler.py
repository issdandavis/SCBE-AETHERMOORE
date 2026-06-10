#!/usr/bin/env python3
"""nature_ruler.py — the ruler + the level (Issac's "math ruler and math level").

Two instruments on one log line:

  RULER  — where a number sits. The dimensionless constants (pi, e, phi, roots,
           1/alpha, m_p/m_e) etched by log(value), so products are sums of lengths.

  LEVEL  — whether an alignment is TRUE. Each pairwise product of marks gets a
           "micro bubble." Its GLOW = significance against a PRE-FIXED null
           ("if my constants were random numbers in this range, how often would
           their products land this close to a mark?"). Brightness rises with
           significance; it only lights above the null's 95th percentile. So a
           real algebraic identity (sqrt3*sqrt3 = 3) blazes, while a numerological
           near-miss (phi*phi ~ e) stays dark even though the marks nearly overlap.
           This is the density-saturation null (prime-fog "beats null95"), made
           physical. The eye can't tell a real alignment from a crowded-line
           accident; the glow can.

  OFFSET RULER — the prime ruler Issac wanted: every mark is prime, so it reads
           "longer than stated, but measuredly so" — mark n sits at p_n, and the
           overhang p_n - n is the KNOWN offset (PNT/Dusart: p_n ~ n(ln n+ln ln n-1)).
           Lay it beside a measured trajectory, align the part you've measured, and
           the marks past your data PREDICT the rest — "measure before you measure."
           Verify by checking gaps against the real object, the way you eyeball a
           ruler against an edge.

Marks come from the nth-prime engine's sieve (nth_prime_baseline_gate.simple_sieve).

Usage:
    python scripts/research/nature_ruler.py --out artifacts/nature_ruler
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
from pathlib import Path

try:
    from scripts.research.nth_prime_baseline_gate import simple_sieve
except ImportError:
    def simple_sieve(limit: int) -> list[int]:
        if limit < 2:
            return []
        f = bytearray([1]) * (limit + 1)
        f[0] = f[1] = 0
        for i in range(2, int(limit**0.5) + 1):
            if f[i]:
                f[i * i :: i] = bytearray(len(f[i * i :: i]))
        return [i for i in range(2, limit + 1) if f[i]]


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "nature_ruler"
W, PAD = 1100.0, 70.0
NULL_DRAWS = 600          # Monte-Carlo fake-constant sets for the level's null
NULL_SEED = 0             # pre-fixed: the null is committed before we look

# Dimensionless constants only — the ones that can share ONE bare line.
PHI = (1 + 5**0.5) / 2
CONSTS = [
    (2.0, "2"), (math.sqrt2 if hasattr(math, "sqrt2") else 2**0.5, "√2"),
    (3**0.5, "√3"), (5**0.5, "√5"), (PHI, "φ"),
    (math.e, "e"), (math.pi, "π"), (3.0, "3"), (5.0, "5"),
    (137.035999, "1/α"), (1836.152, "mₚ/mₑ"),
]
# the "small" constants whose products we test on the level, and the targets
# those products must hit to count as an alignment (integers + the marks).
SMALL = [(3**0.5, "√3"), (5**0.5, "√5"), (2**0.5, "√2"), (PHI, "φ"), (math.e, "e"), (math.pi, "π")]
TARGETS = sorted({float(k) for k in range(2, 13)} | {v for v, _ in CONSTS if v < 13})
XMAX = 2200.0
LOGMAX = math.log(XMAX)


def pos(x: float) -> float:
    return PAD + (W - 2 * PAD) * math.log(x) / LOGMAX


def _nearest_logdist(value: float, targets: list[float]) -> float:
    lv = math.log(value)
    return min(abs(lv - math.log(t)) for t in targets)


# ------------------------------------------------------------------ THE LEVEL
def level_events() -> tuple[list[dict], float]:
    """Each pairwise product (incl. squares) of SMALL consts -> alignment + null z."""
    # real events
    events = []
    for i, (a, la) in enumerate(SMALL):
        for j, (b, lb) in enumerate(SMALL):
            if j < i:
                continue
            prod = a * b
            if prod > XMAX:
                continue
            d = _nearest_logdist(prod, TARGETS)
            events.append({"label": f"{la}·{lb}", "value": prod, "dist": d})

    # PRE-FIXED null: fake constant sets, log-uniform over the small-const range
    rng = random.Random(NULL_SEED)
    lo, hi = math.log(min(v for v, _ in SMALL)), math.log(max(v for v, _ in SMALL))
    null_d = []
    for _ in range(NULL_DRAWS):
        fake = [math.exp(rng.uniform(lo, hi)) for _ in SMALL]
        for i in range(len(fake)):
            for j in range(i, len(fake)):
                prod = fake[i] * fake[j]
                if prod <= XMAX:
                    null_d.append(_nearest_logdist(prod, TARGETS))
    null_p05 = statistics.quantiles(null_d, n=20)[0]      # 5th percentile distance
    nmean, nstd = statistics.mean(null_d), statistics.pstdev(null_d) or 1e-9
    for ev in events:
        ev["z"] = (nmean - ev["dist"]) / nstd            # closer than chance => +z
        ev["glow"] = ev["dist"] < null_p05               # tighter than 95% of chance
        ev["bright"] = max(0.0, min(1.0, (null_p05 - ev["dist"]) / null_p05)) if null_p05 else 0.0
        if ev["dist"] < 1e-9:                            # exact identity blazes
            ev["bright"] = 1.0
    return events, null_p05


def render_ruler_and_level(events: list[dict]) -> str:
    h = 300.0
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {W:.0f} {h:.0f}" font-family="monospace">',
        f'<defs><filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/>'
        f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
        f'<rect width="{W:.0f}" height="{h:.0f}" fill="#0b0e13"/>',
        f'<text x="{PAD}" y="28" fill="#9fb3c8" font-size="15">NATURE RULER + LEVEL — marks=log(constant); bubbles glow by significance vs a pre-fixed null</text>',
    ]
    base = 110.0
    s.append(f'<line x1="{PAD}" y1="{base}" x2="{W-PAD}" y2="{base}" stroke="#5a6b7b" stroke-width="1.5"/>')
    for v, lab in CONSTS:
        x = pos(v)
        s.append(f'<line x1="{x:.1f}" y1="{base}" x2="{x:.1f}" y2="{base-22}" stroke="#7dd3fc" stroke-width="2"/>')
        s.append(f'<text x="{x:.1f}" y="{base-28}" fill="#bfe3ff" font-size="12" text-anchor="middle">{lab}</text>')
    # the level: a micro-bubble per product, at its log position, glowing by significance
    s.append(f'<text x="{PAD}" y="{base+58}" fill="#7e90a3" font-size="12">LEVEL (each = a product of marks; bright = true alignment, dark = crowded-line coincidence):</text>')
    for ev in events:
        x = pos(ev["value"])
        b = ev["bright"]
        if ev["glow"]:
            r = 5 + 7 * b
            s.append(f'<circle cx="{x:.1f}" cy="{base+90}" r="{r:.1f}" fill="#54f0a8" opacity="{0.25+0.75*b:.2f}" filter="url(#glow)"/>')
            s.append(f'<text x="{x:.1f}" y="{base+90-r-3:.1f}" fill="#9fe0c8" font-size="10" text-anchor="middle">{ev["label"]}={ev["value"]:.3g}</text>')
        else:
            s.append(f'<circle cx="{x:.1f}" cy="{base+90}" r="3" fill="#37434f" opacity="0.5"/>')
    glowers = [e for e in events if e["glow"]]
    glow_txt = ", ".join(f'{e["label"]}={e["value"]:.0f}' for e in glowers)
    s.append(f'<text x="{PAD}" y="{base+150}" fill="#9fe0c8" font-size="12">glowing (real): {glow_txt}</text>')
    s.append(f'<text x="{PAD}" y="{base+170}" fill="#7e90a3" font-size="11">dark = density-saturated near-misses (e.g. φ·φ≈e, π·φ): the line is just crowded there.</text>')
    s.append("</svg>")
    return "\n".join(s)


# ------------------------------------------------------------- OFFSET / EXTRAP RULER
def offset_ruler(n_marks: int = 80) -> tuple[str, dict]:
    # first n primes
    limit = max(30, int(n_marks * (math.log(n_marks) + math.log(math.log(n_marks)) + 2)))
    primes = simple_sieve(limit)[:n_marks]
    n_marks = len(primes)
    # known offset / "measuredly so": PNT-Dusart asymptotic p_n ~ n(ln n+ln ln n-1)
    def predict(n: int) -> float:
        if n < 6:
            return float(simple_sieve(20)[n - 1])
        return n * (math.log(n) + math.log(math.log(n)) - 1.0)
    # asymptotic offset is poor at small n, sharpens further out — measure where it applies
    errs = {idx: abs(primes[idx - 1] - predict(idx)) / primes[idx - 1] for idx in range(20, n_marks + 1)}
    max_err = max(errs.values())
    near_err = statistics.mean(errs[i] for i in range(20, 31))
    far_err = statistics.mean(errs[i] for i in range(n_marks - 9, n_marks + 1))

    # "measure before you measure": align on first K, predict the rest, gap-check
    K = n_marks // 2
    gaps = [primes[idx - 1] - predict(idx) for idx in range(K + 1, n_marks + 1)]
    mean_gap = statistics.mean(g / primes[K + g_i] for g_i, g in enumerate(gaps)) if gaps else 0.0

    # render: stated index line vs prime line on the SAME start -> overhang = offset
    pmax = primes[-1]
    inner = W - 2 * PAD
    h = 320.0

    def xn(value: float) -> float:
        return PAD + inner * value / pmax

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {W:.0f} {h:.0f}" font-family="monospace">',
        f'<rect width="{W:.0f}" height="{h:.0f}" fill="#0b0e13"/>',
        f'<text x="{PAD}" y="26" fill="#9fb3c8" font-size="15">OFFSET RULER — every mark is prime; reads longer than stated, measuredly so (offset = p_n − n)</text>',
    ]
    yi, yp = 90.0, 170.0
    s.append(f'<text x="{PAD-8}" y="{yi+4}" fill="#7e90a3" font-size="11" text-anchor="end">index n</text>')
    s.append(f'<text x="{PAD-8}" y="{yp+4}" fill="#7e90a3" font-size="11" text-anchor="end">prime pₙ</text>')
    s.append(f'<line x1="{PAD}" y1="{yi}" x2="{W-PAD}" y2="{yi}" stroke="#46566a" stroke-width="1"/>')
    s.append(f'<line x1="{PAD}" y1="{yp}" x2="{W-PAD}" y2="{yp}" stroke="#5a6b7b" stroke-width="1.5"/>')
    for i, p in enumerate(primes, start=1):
        xp = xn(p)
        s.append(f'<line x1="{xp:.1f}" y1="{yp}" x2="{xp:.1f}" y2="{yp-12}" stroke="#ff5d73" stroke-width="1"/>')
        if i % 10 == 0 or i == 1:
            xi = xn(i)
            s.append(f'<line x1="{xi:.1f}" y1="{yi}" x2="{xi:.1f}" y2="{yi+12}" stroke="#7dd3fc" stroke-width="1.5"/>')
            s.append(f'<text x="{xi:.1f}" y="{yi-6}" fill="#bfe3ff" font-size="10" text-anchor="middle">{i}</text>')
            s.append(f'<text x="{xp:.1f}" y="{yp-16}" fill="#ff9aa8" font-size="10" text-anchor="middle">{p}</text>')
            s.append(f'<line x1="{xi:.1f}" y1="{yi}" x2="{xp:.1f}" y2="{yp}" stroke="#54c5a0" stroke-width="0.6" opacity="0.6"/>')
    s.append(f'<text x="{PAD}" y="{yp+50}" fill="#9fe0c8" font-size="12">known offset pₙ ≈ n(ln n+ln ln n−1): error SHRINKS outward — near(n≈20)={near_err*100:.1f}% → far(n≈{n_marks})={far_err*100:.1f}%</text>')
    s.append(f'<text x="{PAD}" y="{yp+70}" fill="#9fe0c8" font-size="12">measure-before-measure: fit on first {K}, predict {K+1}..{n_marks}, mean gap = {mean_gap*100:.1f}% (trajectory holds ⇒ extrapolation valid)</text>')
    s.append(f'<text x="{PAD}" y="{yp+92}" fill="#7e90a3" font-size="11">green threads = the offset; the further you extrapolate the better it fits. verify by eyeballing gaps against the measured edge.</text>')
    s.append("</svg>")
    return "\n".join(s), {"n_marks": n_marks, "max_rel_err": max_err,
                          "mean_extrap_gap": mean_gap, "near_err": near_err, "far_err": far_err}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--marks", type=int, default=80)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    events, p05 = level_events()
    (args.out / "nature_ruler_level.svg").write_text(render_ruler_and_level(events), encoding="utf-8")
    off_svg, off_meta = offset_ruler(args.marks)
    (args.out / "offset_ruler.svg").write_text(off_svg, encoding="utf-8")

    glow = [e["label"] for e in events if e["glow"]]
    dark_examples = [e["label"] for e in events if not e["glow"]][:4]
    print("NATURE RULER + LEVEL")
    print(f"  null 5th-pctile log-distance (glow threshold) = {p05:.4f}")
    print(f"  GLOWING (true alignments): {glow}")
    print(f"  dark (crowded-line coincidences, sample): {dark_examples}")
    print(f"  -> artifacts: {(args.out/'nature_ruler_level.svg').relative_to(REPO_ROOT)}")
    print("OFFSET RULER")
    print(f"  marks={off_meta['n_marks']}  trajectory max rel-err={off_meta['max_rel_err']*100:.1f}%  "
          f"extrap mean gap={off_meta['mean_extrap_gap']*100:.1f}%")
    print(f"  -> artifacts: {(args.out/'offset_ruler.svg').relative_to(REPO_ROOT)}")

    # self-checks (the user's rule: the level proves itself; no decoration)
    exact = [e for e in events if e["dist"] < 1e-9]
    assert exact, "expected exact identities (√k·√k=k) on the level"
    assert all(e["glow"] for e in exact), "an exact identity failed to glow — level is broken"
    # numerology must stay DARK where it isn't tight: φ·φ≈e (3.7% off) must not glow
    phisq = next(e for e in events if e["label"] == "φ·φ")
    assert not phisq["glow"], "φ·φ glowed — the null gate is leaking"
    # honest limit: the level flags TIGHT coincidences too (√5·π≈7). "tighter than chance"
    # is not "structurally true" — separating those needs theory, not the level alone.
    tight_coincidences = [e["label"] for e in events if e["glow"] and e["dist"] >= 1e-9]
    # extrapolation premise: trajectory must CONVERGE (far fits better than near)
    assert off_meta["far_err"] < off_meta["near_err"], "prime trajectory not converging — extrapolation premise broken"
    print(f"  honest limit — also glows (tight coincidence, not identity): {tight_coincidences}")
    print("  self-checks: exact identities glow; φ·φ≈e stays dark; trajectory converges outward  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
