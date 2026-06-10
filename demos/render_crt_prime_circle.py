#!/usr/bin/env python3
"""Render a static labeled snapshot of the Orthogonal/CRT Prime Sieve "circle of primes".

The wheel of 30 (= 2*3*5). Every residue class mod 30 sits on the ring. A residue
is a PRIME CANDIDATE exactly when it is coprime to 30 -- i.e. not killed by the
mod-2, mod-3, or mod-5 axis. The 8 survivors {1,7,11,13,17,19,23,29} are the only
residues that can hold primes; everything else collapses onto an axis and is culled.

CRT decomposition (the "orthogonal" part):
    n = 15a + 10b + 6c  (mod 30),  a=n mod2, b=n mod3, c=n mod5
    prime candidate  <=>  a != 0  AND  b != 0  AND  c != 0

Companion to demos/crt_prime_sieve_viz.html. Output: demos/crt_prime_sieve_circle.png
"""
from __future__ import annotations

from math import cos, gcd, pi, sin
from pathlib import Path

import matplotlib.pyplot as plt

BG = "#020311"
NODE_PRIME = "#b4d2ff"      # coprime-to-30 survivor (light blue, matches the viz)
AX2 = "#ff5a2d"            # culled by 2  (amber/orange)
AX3 = "#37c850"            # culled by 3  (green)
AX5 = "#b06cff"            # culled by 5  (violet)
RING = "#28407a"


def axis_color(r: int) -> str:
    """Smallest prime axis (2<3<5) that culls residue r."""
    if r % 2 == 0:
        return AX2
    if r % 3 == 0:
        return AX3
    return AX5  # r % 5 == 0


def main() -> int:
    out = Path(__file__).resolve().parent / "crt_prime_sieve_circle.png"
    survivors = [r for r in range(30) if gcd(r, 30) == 1]  # {1,7,11,13,17,19,23,29}

    fig, ax = plt.subplots(figsize=(10, 10), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    R = 1.0
    # ring outline
    ax.add_patch(plt.Circle((0, 0), R, fill=False, color=RING, lw=1.2, alpha=0.7))

    for r in range(30):
        theta = pi / 2 - 2 * pi * r / 30  # 0 at top, clockwise
        x, y = R * cos(theta), R * sin(theta)
        lx, ly = 1.16 * cos(theta), 1.16 * sin(theta)
        is_prime_cand = r in survivors
        if is_prime_cand:
            ax.scatter([x], [y], s=520, color=NODE_PRIME, edgecolors="white",
                       linewidths=1.4, zorder=5)
            ax.scatter([x], [y], s=1600, color=NODE_PRIME, alpha=0.12, zorder=4)  # glow
            ax.text(lx, ly, str(r), color="white", ha="center", va="center",
                    fontsize=15, fontweight="bold", zorder=6)
            tag = "unit" if r == 1 else "prime-bearing"
            ax.text(x, y, "", zorder=6)
        else:
            c = axis_color(r)
            ax.scatter([x], [y], s=120, color=c, alpha=0.85, zorder=3)
            ax.text(lx, ly, str(r), color=c, ha="center", va="center",
                    fontsize=9, alpha=0.85, zorder=3)

    # center identity block
    ax.text(0, 0.16, r"$n \equiv 15a + 10b + 6c \;(\mathrm{mod}\ 30)$",
            color="white", ha="center", va="center", fontsize=15)
    ax.text(0, -0.02, r"$a=n\,\mathrm{mod}\,2 \quad b=n\,\mathrm{mod}\,3 \quad c=n\,\mathrm{mod}\,5$",
            color="#9fb4e0", ha="center", va="center", fontsize=11)
    ax.text(0, -0.18, "prime candidate  " + r"$\Leftrightarrow$" + "  a, b, c all " + r"$\neq 0$",
            color=NODE_PRIME, ha="center", va="center", fontsize=12, fontweight="bold")

    # title + footnote
    ax.text(0, 1.42, "ORTHOGONAL PRIME SIEVE", color="white", ha="center",
            fontsize=20, fontweight="bold")
    ax.text(0, 1.32, "the coprime-30 ring  ·  8 survivors carry every prime > 5",
            color="#9fb4e0", ha="center", fontsize=12)
    ax.text(0, -1.46,
            "survivors {1, 7, 11, 13, 17, 19, 23, 29}   ·   1 is the unit   ·   "
            "first composite survivor: 49 = 7$^2$",
            color="#9fb4e0", ha="center", fontsize=10.5)

    # legend
    handles = [
        plt.Line2D([0], [0], marker="o", color=BG, markerfacecolor=NODE_PRIME,
                   markeredgecolor="white", markersize=14, label="prime candidate (coprime to 30)"),
        plt.Line2D([0], [0], marker="o", color=BG, markerfacecolor=AX2, markersize=10,
                   label="culled by 2-axis  (a = 0)"),
        plt.Line2D([0], [0], marker="o", color=BG, markerfacecolor=AX3, markersize=10,
                   label="culled by 3-axis  (b = 0)"),
        plt.Line2D([0], [0], marker="o", color=BG, markerfacecolor=AX5, markersize=10,
                   label="culled by 5-axis  (c = 0)"),
    ]
    leg = ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.12),
                    ncol=2, frameon=False, fontsize=10, labelcolor="#cfddff")

    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.62, 1.55)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(out, facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
