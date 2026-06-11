#!/usr/bin/env python3
"""Two real layers (L8 -> L12) as terrain, plus a proposed same-pole repulsor.

This renders the SCBE governance field using the REAL, imported layer code -- and it
is deliberate about the line between what the code does and what is a design proposal.

WHAT IS REAL (imported live from
src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py, self-checked
against the canonical scalar functions before any pixel is drawn):

  Layer 8  "multi-well realms":   d*(u) = min_k d_H(u, mu_k)
      d_H = arccosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))   (Layer 5 metric)
      mu_k = generate_realm_centers(2, 5): 5 wells on a ring, radii 0.3..0.7, every 72deg.
      L8 is a MINIMUM-HYPERBOLIC-DISTANCE basin field, not a summed potential V(x).

  Layer 12 "harmonic wall":       H(d*, pd) = 1 / (1 + d* + 2*pd)   (bounded, in (0,1])

  Layer 13 decision (real thresholds THETA_1=0.5, THETA_2=2.0 on d*):
      d* < 0.5         -> LOW    -> ALLOW
      0.5 <= d* < 2.0  -> MEDIUM -> REVIEW
      d* >= 2.0        -> HIGH   -> DENY
      (the code's 4th branch, H>100 -> SNAP, is unreachable here: the bounded L12 wall
       maxes at H=1, so SNAP is a dead vestige expecting an unbounded wall. Noted, honestly.)

  Realm sensitivity weights [1.0, 1.2, 0.8, 1.5, 1.1] (L13). The max-weight well (index 3)
  is the most system-governing realm -- the "gated CORE" in panel 1/3.

HOW THE LAYERS ACTUALLY COMPOSE (verified by adversarial code review, 3 lenses):

  L8 and L12 are CHAINED BY A SCALAR, not geometrically nested. L8 collapses the realm
  distances to one number d*; L12 receives only that scalar and re-scales it. L12 holds
  NO realm centers and computes no per-well geometry. So a picture that draws the L12 wall
  literally *inside* each L8 well would be an overclaim.

  The honest nesting -- and the one this figure draws -- is the DIMENSIONAL LIFT: the scalar
  d* handed forward from L8 (the layer before) becomes an AXIS of L12's own sub-dimension
  (d*, pd). Panel 2 is that sub-space. "A vector from the layer before, living inside the
  other dimension" -- literally true, because d* is L12's input axis.

  Caveats kept on the page, not hidden: this depicts the TypeScript reference pipeline's
  L8->L12 hand-off. It is NOT the production Python gate (runtime_gate.py uses a single
  moving centroid, k=1, Euclidean drift, pi^(phi*d*) -- no realm set, no L8). And L8 here
  is the realm-distance field, NOT hamiltonianCFI.ts (a separate, never-imported graph
  control-flow-integrity module). The word "Hamiltonian" is therefore not used for L8.

PANEL 3 IS REAL, TESTED CODE (same_pole_repulsor.py, tests/test_same_pole_repulsor.py):

  A same-pole repulsor at the gated CORE. The potential is the genuine hyperbolic Green's function
  (Laplace-Beltrami on H^2), not a soft-core stand-in:
      d*_eff(u; intent) = d*(u) + lambda * intent * G_H(d_H(u, mu_gate)),  G_H(d) = -log(tanh(d/2))
  G_H truly diverges as d_H -> 0 (no epsilon cap). The arrows are the module's analytic
  repulsor_force(u, gate, intent); the surface adds the same potential to the real cost. intent=0
  -> the term is exactly 0, the field is transparent to an authorized seeker (panel 3 collapses to
  panel 1, proven by test). The force points radially OUTWARD everywhere (proven on 500 points):
  the gate auto-orients an unauthorized seeker away, harder push -> harder shove. intent = g*a is
  GROUNDED: g from the Sacred Eggs ring proof (intent_from_egg, sharing possesses_yolk with live
  ring_descent) is 0 for the yolk-holder; a ramps up as an unauthorized seeker approaches.

Output: demos/layered_realm_topography.png
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from src.symphonic_cipher.scbe_aethermoore.layers.fourteen_layer_pipeline import (  # noqa: E402
    THETA_1,
    THETA_2,
    generate_realm_centers,
    layer_5_hyperbolic_distance,
    layer_12_harmonic_scaling,
)
from src.symphonic_cipher.scbe_aethermoore.layers.same_pole_repulsor import (  # noqa: E402
    LAMBDA_DEFAULT,
    gate_center,
    green_potential,
    repulsor_force,
    repulsor_potential,
)

# ---- house palette (shared with demos/render_realm_topography.py) --------------------
BG = "#020311"
RING = "#5a78c8"
TEXT = "#e6eeff"
SUBTEXT = "#9fb4e0"
FOOT = "#6f86b8"
ALLOW, REVIEW, DENY = "#2f9e54", "#d8c33a", "#b3271a"
GATE = "#ff5a8a"

N_WELLS = 5
GATE_IDX = 3  # realm with max L13 weight (1.5) -> most system-governing -> gated CORE
GRID_N = 560
EPS = 1e-10
# LAMBDA_DEFAULT is imported from the real module so figure == code (no eps soft-core anymore).


def terrain_cmap() -> LinearSegmentedColormap:
    """Valley (low cost / safe) -> ridge (high cost): teal -> gold -> ember."""
    return LinearSegmentedColormap.from_list(
        "realm_terrain",
        ["#0a3d3a", "#13715f", "#3fa66b", "#cdd24a", "#e8902f", "#c0341f", "#5e1410"],
    )


def safety_cmap() -> LinearSegmentedColormap:
    """Low safety (H~0, danger) -> high safety (H~1): ember -> gold -> teal."""
    return LinearSegmentedColormap.from_list(
        "realm_safety",
        ["#5e1410", "#c0341f", "#e8902f", "#cdd24a", "#3fa66b", "#13715f", "#0a3d3a"],
    )


def dH_grid(ux: np.ndarray, uy: np.ndarray, cx: float, cy: float) -> np.ndarray:
    """Vectorized Poincare d_H from grid to one center. Asserted == the L5 scalar fn."""
    norm_u_sq = np.minimum(ux * ux + uy * uy, 1.0 - EPS)
    norm_v_sq = min(cx * cx + cy * cy, 1.0 - EPS)
    diff_sq = (ux - cx) ** 2 + (uy - cy) ** 2
    denom = np.maximum((1.0 - norm_u_sq) * (1.0 - norm_v_sq), EPS)
    cosh_dist = np.maximum(1.0 + 2.0 * diff_sq / denom, 1.0)
    return np.arccosh(cosh_dist)


def _selfcheck(centers: np.ndarray) -> None:
    """Prove the fast grid math equals the canonical imported scalar code."""
    rng = np.random.default_rng(11)
    for _ in range(200):
        p = rng.uniform(-0.9, 0.9, size=2)
        if p[0] ** 2 + p[1] ** 2 >= 1.0 - EPS:
            continue
        c = centers[rng.integers(len(centers))]
        fast = float(dH_grid(np.array([p[0]]), np.array([p[1]]), c[0], c[1])[0])
        ref = layer_5_hyperbolic_distance(np.asarray(p), np.asarray(c))
        assert abs(fast - ref) < 1e-9, f"d_H mismatch: fast={fast} ref={ref}"
    for d in (0.0, 0.5, 1.0, 2.0, 4.0):
        vec = 1.0 / (1.0 + d + 2.0 * 0.0)
        assert abs(vec - layer_12_harmonic_scaling(d, 0.0)) < 1e-12, "L12 mismatch"


def d_star_field(centers: np.ndarray):
    lin = np.linspace(-0.985, 0.985, GRID_N)
    X, Y = np.meshgrid(lin, lin)
    d_star = np.full(X.shape, np.inf)
    for cx, cy in centers:
        d_star = np.minimum(d_star, dH_grid(X, Y, cx, cy))
    inside = (X**2 + Y**2) < (1.0 - 1e-4)
    return X, Y, d_star, inside


def draw_disk_edge(ax) -> None:
    ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, color=RING, lw=1.6, alpha=0.9, zorder=6))


def mark_wells(ax, centers: np.ndarray, gate_color: str = GATE) -> None:
    for k, (cx, cy) in enumerate(centers):
        is_gate = k == GATE_IDX
        ax.scatter(
            [cx],
            [cy],
            s=150 if is_gate else 70,
            color=gate_color if is_gate else "white",
            edgecolors="#0b1a3a",
            linewidths=1.3,
            marker="*" if is_gate else "o",
            zorder=9,
        )
        label = f"realm {k}" + ("  (gated CORE)" if is_gate else "")
        ax.text(
            cx,
            cy + 0.085,
            label,
            color=gate_color if is_gate else TEXT,
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold" if is_gate else "normal",
            zorder=10,
        )


# ====================================================================================
def panel_l8(ax, X, Y, d_star, inside, centers, probe):
    """Panel 1: the real L8 multi-well realm map (elevation = d*) + L13 band boundaries."""
    field = np.where(inside, d_star, np.nan)
    levels = np.linspace(0.0, float(np.nanmax(field)), 24)
    cf = ax.contourf(X, Y, field, levels=levels, cmap=terrain_cmap(), extend="neither")
    # The two REAL L13 decision boundaries as contour lines on the terrain.
    bnd = ax.contour(X, Y, field, levels=[THETA_1, THETA_2], colors=[ALLOW, DENY], linewidths=2.0, linestyles="--")
    ax.clabel(
        bnd, fmt={THETA_1: "ALLOW | REVIEW  (d*=0.5)", THETA_2: "REVIEW | DENY  (d*=2.0)"}, fontsize=7.5, colors=TEXT
    )
    draw_disk_edge(ax)
    mark_wells(ax, centers)

    px, py, pd_star = probe
    ax.scatter([px], [py], s=120, color="#7fe7ff", edgecolors="#02202a", linewidths=1.4, zorder=11)
    ax.annotate(
        f"incoming agent P\n d* = {pd_star:.2f}  ->  REVIEW",
        xy=(px, py),
        xytext=(px + 0.18, py + 0.34),
        color="#7fe7ff",
        fontsize=9,
        fontweight="bold",
        ha="left",
        arrowprops=dict(arrowstyle="->", color="#7fe7ff", lw=1.3),
        zorder=12,
    )
    cb = ax.figure.colorbar(cf, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("L8  d* = min_k d_H(u, mu_k)   (valley 0 -> rim infinity)", color=TEXT, fontsize=9)
    plt.setp(plt.getp(cb.ax.axes, "yticklabels"), color=SUBTEXT)
    ax.set_title("L8  ·  MULTI-WELL REALM MAP", color=TEXT, fontsize=14, fontweight="bold", pad=10)
    ax.text(
        0,
        -1.16,
        "5 real wells (radii 0.3-0.7, every 72deg)   ·   dashed = real L13 cuts at d*=0.5, 2.0",
        color=SUBTEXT,
        ha="center",
        fontsize=8.5,
    )


def panel_l12(ax, probe):
    """Panel 2: the nested sub-dimension -- L12 surface H(d*, pd), d* lifted from L8."""
    d_axis = np.linspace(0.0, 3.2, 400)
    pd_axis = np.linspace(0.0, 1.0, 300)
    D, P = np.meshgrid(d_axis, pd_axis)
    H = 1.0 / (1.0 + D + 2.0 * P)  # real L12, vectorized (== layer_12_harmonic_scaling)

    cf = ax.contourf(D, P, H, levels=np.linspace(0.0, 1.0, 21), cmap=safety_cmap())
    ax.contour(D, P, H, levels=[1 / 3, 1 / 1.5], colors=[TEXT, TEXT], linewidths=0.6, alpha=0.4)

    # The REAL L13 cut points become vertical lines in the sub-space.
    for thr, col, name in [(THETA_1, ALLOW, "d*=0.5"), (THETA_2, DENY, "d*=2.0")]:
        ax.axvline(thr, color=col, ls="--", lw=2.0)
        ax.text(thr, 1.02, name, color=col, ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # The hand-off: P's scalar d* from L8 enters here as a coordinate.
    _, _, pd_star = probe
    ax.axvline(pd_star, color="#7fe7ff", ls="-", lw=1.6, alpha=0.9)
    ax.scatter([pd_star], [0.0], s=90, color="#7fe7ff", edgecolors="#02202a", linewidths=1.3, zorder=8)
    ax.annotate(
        f"P arrives from L8\n d* = {pd_star:.2f}  (the layer before)\n H(d*,0) = {1/(1+pd_star):.2f}",
        xy=(pd_star, 0.0),
        xytext=(pd_star + 0.35, 0.30),
        color="#7fe7ff",
        fontsize=9,
        fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#7fe7ff", lw=1.3),
        zorder=9,
    )
    cb = ax.figure.colorbar(cf, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("L12 safety  H = 1/(1 + d* + 2*pd)", color=TEXT, fontsize=9)
    plt.setp(plt.getp(cb.ax.axes, "yticklabels"), color=SUBTEXT)

    ax.set_xlabel("d*   <-  scalar handed forward from L8", color=TEXT, fontsize=10)
    ax.set_ylabel("pd   (phase deviation -- L12's own sub-axis)", color=TEXT, fontsize=10)
    ax.tick_params(colors=SUBTEXT)
    for s in ax.spines.values():
        s.set_color("#22335f")
    ax.set_title("L12  ·  THE NESTED SUB-DIMENSION", color=TEXT, fontsize=14, fontweight="bold", pad=10)
    ax.text(
        1.6,
        -0.16,
        "L8 hands L12 a SCALAR; L12 lifts it into (d*, pd). Chain, not containment.",
        color=SUBTEXT,
        ha="center",
        fontsize=8.5,
        transform=ax.transData,
    )


def panel_repulsor(ax, X, Y, d_star, inside, centers):
    """Panel 3: same-pole repulsor at the gated CORE -- drawing the REAL tested module."""
    gate, _ = gate_center(centers)
    gx, gy = gate
    d_gate = dH_grid(X, Y, gx, gy)
    c_base = 1.0 - 1.0 / (1.0 + d_star)  # real cost surface
    # Unauthorized field: intent = g*a with g=1 (no yolk) and the real approach ramp a.
    intent_field = np.clip(1.0 - d_gate / THETA_2, 0.0, 1.0)
    green = -np.log(np.tanh(np.maximum(d_gate, 1e-9) / 2.0))  # G_H(d_gate): genuine divergence, no eps
    phi = c_base + LAMBDA_DEFAULT * intent_field * green

    # Self-check: the vectorized G_H term equals same_pole_repulsor.repulsor_potential (intent=1).
    rng = np.random.default_rng(5)
    for _ in range(40):
        p = rng.uniform(-0.85, 0.85, size=2)
        if p @ p >= 0.9:
            continue
        ref = LAMBDA_DEFAULT * green_potential(layer_5_hyperbolic_distance(p, gate))
        assert abs(repulsor_potential(p, gate, 1.0) - ref) < 1e-9

    phi_disp = np.where(inside, np.clip(phi, 0.0, 1.6), np.nan)
    ax.contourf(X, Y, phi_disp, levels=np.linspace(0.0, 1.6, 24), cmap=terrain_cmap(), extend="max")
    draw_disk_edge(ax)
    mark_wells(ax, centers)

    # Arrows are the REAL module force same_pole_repulsor.repulsor_force at the ramped intent.
    step = 26
    xs, ys = X[::step, ::step], Y[::step, ::step]
    ux = np.zeros_like(xs)
    uy = np.zeros_like(ys)
    for a in range(xs.shape[0]):
        for b in range(xs.shape[1]):
            p = np.array([xs[a, b], ys[a, b]])
            if p @ p >= 0.93:
                continue
            d = layer_5_hyperbolic_distance(p, gate)
            ip = float(np.clip(1.0 - d / THETA_2, 0.0, 1.0))
            f = repulsor_force(p, gate, ip)
            mag = math.hypot(f[0], f[1]) + 1e-9
            ux[a, b], uy[a, b] = f[0] / mag, f[1] / mag
    ins = (xs**2 + ys**2) < 0.93
    ax.quiver(xs[ins], ys[ins], ux[ins], uy[ins], color="#cfe0ff", alpha=0.8, scale=26, width=0.004, zorder=7)
    ax.scatter([gx], [gy], s=520, facecolors="none", edgecolors=GATE, linewidths=2.0, zorder=8)

    ax.set_title("SAME-POLE REPULSOR  ·  real module", color=GATE, fontsize=13, fontweight="bold", pad=10)
    ax.text(
        0,
        -1.16,
        "same_pole_repulsor.py: d*_eff = d* + lambda*intent*G_H(d_H),  G_H=-log(tanh(d_H/2)) (diverges).\n"
        "intent = g*a from the ring proof: 0 for the yolk-holder (transparent), else ramps up on approach.",
        color=SUBTEXT,
        ha="center",
        fontsize=8.3,
    )


def main() -> int:
    out = Path(__file__).resolve().parent / "layered_realm_topography.png"
    centers = generate_realm_centers(2, N_WELLS)
    _selfcheck(centers)

    X, Y, d_star, inside = d_star_field(centers)

    # Probe agent at the origin: equidistant-ish, lands in the REVIEW band.
    p0 = np.array([0.0, 0.0])
    pd_star = min(layer_5_hyperbolic_distance(p0, np.asarray(c)) for c in centers)
    probe = (float(p0[0]), float(p0[1]), float(pd_star))

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(28, 10.0), dpi=160)
    fig.patch.set_facecolor(BG)
    for ax in (ax1, ax3):
        ax.set_facecolor(BG)
        ax.set_xlim(-1.18, 1.18)
        ax.set_ylim(-1.24, 1.18)
        ax.set_aspect("equal")
        ax.axis("off")
    ax2.set_facecolor(BG)

    panel_l8(ax1, X, Y, d_star, inside, centers, probe)
    panel_l12(ax2, probe)
    panel_repulsor(ax3, X, Y, d_star, inside, centers)

    fig.suptitle(
        "SCBE governance as terrain  —  L8 realm map  ->  L12 nested sub-dimension  ->  same-pole gate",
        color=TEXT,
        fontsize=13,
        y=0.985,
    )
    fig.text(
        0.5,
        0.012,
        "REAL (imported + self-checked): L8 d*=min_k d_H, L12 H=1/(1+d*+2pd), L13 thresholds 0.5/2.0, "
        "panel 3 = same_pole_repulsor.py (14 tests).   L8->L12 is a stylized depiction of the TS reference "
        "scalar hand-off — NOT the production gate, NOT hamiltonianCFI.",
        color=FOOT,
        ha="center",
        fontsize=8.6,
    )

    fig.savefig(out, facecolor=BG, bbox_inches="tight", pad_inches=0.3)
    print(f"wrote {out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
