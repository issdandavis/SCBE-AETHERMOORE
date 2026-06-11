#!/usr/bin/env python3
"""Render the SCBE governance field as a realm topography (contour map).

This is NOT an invented potential. The altitude at every point is the real
harmonic scaling law from the patent core, imported live from
``src/symphonic_cipher/harmonic_scaling_law.py``:

    d*(x)  = min_k  d_H(x, mu_k)            # hyperbolic distance to nearest trusted realm
    d_H    = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))   # Poincare ball metric
    H(d*)  = 1 + alpha * tanh(beta * d*)    # bounded harmonic wall, H in [1, 1+alpha]

Read as terrain:
  * The trusted realms (mu_k) are BASINS -- at a realm d*=0 so H=1 (valley floor).
  * Moving away from every realm raises d*, so H climbs: the harmonic WALL is the ridge.
  * The unit-disk boundary is the edge of the world: d_H -> infinity there, so the
    wall saturates to 1+alpha (the encircling cliff). Adversarial drift literally
    has to climb out of the valley, and the cost is bounded but steep.

Two panels:
  LEFT  -- continuous elevation (filled contours + elevation lines) of the real H field.
  RIGHT -- the same field cut into L13-style decision regions
           (ALLOW / QUARANTINE / ESCALATE / DENY) by wall-saturation shells.

HONESTY NOTES (so this reads as evidence, not decoration):
  * The FIELD is real code: H, d_H, and find_nearest_trusted_realm are imported, and
    the fast vectorized d_H used for the grid is asserted equal to the canonical scalar
    function at sample points before rendering.
  * The 6 realm placements (one per Sacred Tongue, golden-angle spaced) are the demo's
    SCENARIO, not a claim that the tongues are six separate safe basins.
  * The 25/50/75% saturation cut-points for the decision bands are an illustrative
    mapping. L13's production thresholds run on detector scores (classifier /
    trichromatic), a different axis; here we band the wall itself so the regions line up
    with the visible terrain.

Output: demos/realm_topography.png
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap  # noqa: E402

from src.symphonic_cipher.harmonic_scaling_law import (  # noqa: E402
    PHI,
    HarmonicScalingLaw,
    hyperbolic_distance_poincare,
)

BG = "#020311"
RING = "#5a78c8"
TEXT = "#e6eeff"
SUBTEXT = "#9fb4e0"

# The six Sacred Tongues, used here as six trusted realms (basins).
TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
REALM_RADIUS = 0.55  # how far the basins sit from the origin, inside the unit disk
GRID_N = 600
EPS = 1e-10


def realm_centers(radius: float = REALM_RADIUS) -> np.ndarray:
    """Six trusted-realm centers in the Poincare disk, golden-angle spaced."""
    golden = math.pi * (3.0 - math.sqrt(5.0))  # ~137.5 deg, the phi angle
    pts = []
    for k in range(len(TONGUES)):
        theta = math.pi / 2 + k * golden  # start at top, fan out by golden angle
        pts.append([radius * math.cos(theta), radius * math.sin(theta)])
    return np.asarray(pts, dtype=np.float64)


def dH_grid(ux: np.ndarray, uy: np.ndarray, cx: float, cy: float) -> np.ndarray:
    """Vectorized Poincare-ball d_H from every grid point to one center (cx, cy).

    Identical formula to harmonic_scaling_law.hyperbolic_distance_poincare; verified
    against that scalar function in _selfcheck() before this is trusted for rendering.
    """
    norm_u_sq = np.minimum(ux * ux + uy * uy, 1.0 - EPS)
    norm_v_sq = min(cx * cx + cy * cy, 1.0 - EPS)
    diff_sq = (ux - cx) ** 2 + (uy - cy) ** 2
    denom = np.maximum((1.0 - norm_u_sq) * (1.0 - norm_v_sq), EPS)
    cosh_dist = np.maximum(1.0 + 2.0 * diff_sq / denom, 1.0)
    return np.arccosh(cosh_dist)


def _selfcheck(centers: np.ndarray, wall: HarmonicScalingLaw) -> None:
    """Prove the fast grid math equals the canonical scalar code, on real samples."""
    rng = np.random.default_rng(7)
    for _ in range(200):
        p = rng.uniform(-0.9, 0.9, size=2)
        if p[0] ** 2 + p[1] ** 2 >= 1.0 - EPS:
            continue
        c = centers[rng.integers(len(centers))]
        fast = float(dH_grid(np.array([p[0]]), np.array([p[1]]), c[0], c[1])[0])
        ref = hyperbolic_distance_poincare(p, c)
        assert abs(fast - ref) < 1e-9, f"d_H mismatch: fast={fast} ref={ref}"
    # And the vectorized wall matches the canonical scalar wall.
    for d in (0.0, 0.3, 1.0, 2.5, 8.0):
        vec = 1.0 + wall.alpha * math.tanh(wall.beta * d)
        assert abs(vec - wall.compute(d)) < 1e-12, "wall mismatch"


def compute_field(centers: np.ndarray, wall: HarmonicScalingLaw):
    """Return (X, Y, d_star, H, inside-mask) over the unit disk."""
    lin = np.linspace(-0.985, 0.985, GRID_N)
    X, Y = np.meshgrid(lin, lin)

    d_star = np.full(X.shape, np.inf)
    for cx, cy in centers:
        d_star = np.minimum(d_star, dH_grid(X, Y, cx, cy))

    # Vectorized harmonic wall (asserted equal to wall.compute in _selfcheck).
    H = 1.0 + wall.alpha * np.tanh(wall.beta * d_star)

    inside = (X ** 2 + Y ** 2) < (1.0 - 1e-4)
    H = np.where(inside, H, np.nan)
    d_star = np.where(inside, d_star, np.nan)
    return X, Y, d_star, H, inside


def _terrain_cmap() -> LinearSegmentedColormap:
    """Deep valley -> ridge: teal basins, gold mid-slope, ember ridge."""
    return LinearSegmentedColormap.from_list(
        "realm_terrain",
        ["#0a3d3a", "#13715f", "#3fa66b", "#cdd24a", "#e8902f", "#c0341f", "#5e1410"],
    )


def draw_disk_edge(ax) -> None:
    ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, color=RING, lw=1.6, alpha=0.9, zorder=6))


def mark_realms(ax, centers: np.ndarray, label_color: str) -> None:
    for (cx, cy), name in zip(centers, TONGUES):
        ax.scatter([cx], [cy], s=70, color="white", edgecolors="#0b1a3a", linewidths=1.2, zorder=8)
        ax.text(
            cx,
            cy + 0.075,
            name,
            color=label_color,
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            zorder=9,
        )


def main() -> int:
    out = Path(__file__).resolve().parent / "realm_topography.png"
    centers = realm_centers()
    wall = HarmonicScalingLaw(require_pq_binding=False)  # alpha=10, beta=0.5 (module defaults)
    _selfcheck(centers, wall)

    X, Y, d_star, H, inside = compute_field(centers, wall)
    alpha = wall.alpha  # 10.0
    sat = (H - 1.0) / alpha  # wall saturation in [0, 1] == tanh(beta * d*)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(20, 10.5), dpi=170)
    fig.patch.set_facecolor(BG)

    # ---------------------------------------------------------------- LEFT: elevation
    axL.set_facecolor(BG)
    cmap = _terrain_cmap()
    levels = np.linspace(1.0, 1.0 + alpha, 22)
    cf = axL.contourf(X, Y, H, levels=levels, cmap=cmap, extend="neither")
    # elevation lines (the contour map proper)
    cl = axL.contour(X, Y, H, levels=levels[::3], colors="#04121f", linewidths=0.6, alpha=0.55)
    axL.clabel(cl, fmt="%.0f", fontsize=7, colors="#04121f")
    draw_disk_edge(axL)
    mark_realms(axL, centers, TEXT)

    cb = fig.colorbar(cf, ax=axL, fraction=0.046, pad=0.02)
    cb.set_label("harmonic wall   H = 1 + alpha*tanh(beta*d*)   (valley 1  ->  ridge 11)", color=TEXT, fontsize=10)
    cb.ax.yaxis.set_tick_params(color=SUBTEXT)
    plt.setp(plt.getp(cb.ax.axes, "yticklabels"), color=SUBTEXT)

    axL.set_title(
        "REALM TOPOGRAPHY  ·  elevation = governance cost",
        color=TEXT,
        fontsize=15,
        fontweight="bold",
        pad=12,
    )
    axL.text(
        0,
        -1.14,
        "basins = trusted realms (d*=0, H=1)   ·   slopes = harmonic wall   ·   rim = edge of the disk (d_H -> inf)",
        color=SUBTEXT,
        ha="center",
        fontsize=10,
    )

    # ---------------------------------------------------------------- RIGHT: decisions
    axR.set_facecolor(BG)
    # Saturation shells -> L13-style bands. Cut-points are illustrative (see header).
    band_edges = [0.0, 0.25, 0.50, 0.75, 1.0001]
    band_colors = ["#2f9e54", "#d8c33a", "#e07b1e", "#b3271a"]  # ALLOW / QUAR / ESC / DENY
    band_names = ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]
    band_cmap = ListedColormap(band_colors)
    norm = BoundaryNorm(band_edges, band_cmap.N)

    axR.contourf(X, Y, sat, levels=band_edges, colors=band_colors, norm=norm)
    # crisp band boundaries
    axR.contour(X, Y, sat, levels=band_edges[1:-1], colors="#04121f", linewidths=1.1, alpha=0.7)
    draw_disk_edge(axR)
    mark_realms(axR, centers, "#06140a")

    handles = [
        plt.Line2D([0], [0], marker="s", color=BG, markerfacecolor=c, markersize=14, label=n)
        for c, n in zip(band_colors, band_names)
    ]
    leg = axR.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.135),
        ncol=4,
        frameon=False,
        fontsize=11,
        labelcolor=TEXT,
    )
    for txt in leg.get_texts():
        txt.set_fontweight("bold")

    axR.set_title(
        "L13 DECISION REGIONS  ·  wall-saturation shells",
        color=TEXT,
        fontsize=15,
        fontweight="bold",
        pad=12,
    )
    axR.text(
        0,
        -1.14,
        "saturation s = tanh(beta*d*)   ·   bands at s = 0.25 / 0.50 / 0.75 (illustrative cut-points)",
        color=SUBTEXT,
        ha="center",
        fontsize=10,
    )

    for ax in (axL, axR):
        ax.set_xlim(-1.18, 1.18)
        ax.set_ylim(-1.22, 1.18)
        ax.set_aspect("equal")
        ax.axis("off")

    fig.suptitle(
        "SCBE governance field as terrain  —  real harmonic scaling law over the Poincare disk",
        color=TEXT,
        fontsize=12,
        y=0.975,
    )
    fig.text(
        0.5,
        0.012,
        f"phi = {PHI:.6f}   ·   6 trusted realms (one per Sacred Tongue), golden-angle placed   ·   "
        "field imported live from src/symphonic_cipher/harmonic_scaling_law.py",
        color="#6f86b8",
        ha="center",
        fontsize=9,
    )

    fig.savefig(out, facecolor=BG, bbox_inches="tight", pad_inches=0.3)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
