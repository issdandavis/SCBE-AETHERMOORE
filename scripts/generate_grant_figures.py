"""
Generate publication-quality figures for Schmidt Sciences LOI and white paper.

Produces 5 figures:
1. Binary manifold walks — clean vs adversarial (728-bit trajectories)
2. Harmonic wall cost surface — 3D visualization of H(d,R) = R^(d²)
3. Fibonacci spiral fingerprints — clean vs adversarial governance
4. Poincare ball risk zones — 2D projection with cost contours
5. 14-layer pipeline comparison — per-layer metrics side by side

@patent USPTO #63/961,403
"""

import sys
import math
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
import numpy as np

from src.fibonacci_drift.tracker import (
    LayerSnapshot, PHI, TONGUE_WEIGHTS, FIBONACCI_SEQ,
    FibonacciDriftTracker, LAYER_TONGUE_RESONANCE,
)
from src.fibonacci_drift.binary_manifold import (
    BinaryManifoldAnalyzer, float_to_bits, bits_to_walk,
)

# Output directory
FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "grants", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# Style
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.facecolor": "#0d1117",
    "axes.facecolor": "#161b22",
    "text.color": "#e6edf3",
    "axes.labelcolor": "#e6edf3",
    "xtick.color": "#8b949e",
    "ytick.color": "#8b949e",
    "axes.edgecolor": "#30363d",
    "grid.color": "#21262d",
    "grid.alpha": 0.6,
})

# Color palette
GOLD = "#f0c040"
CYAN = "#58a6ff"
RED = "#f85149"
GREEN = "#3fb950"
PURPLE = "#bc8cff"
ORANGE = "#d29922"
WHITE = "#e6edf3"
DIM = "#8b949e"

# Tongue colors
TONGUE_COLORS = {
    "KO": "#f0c040", "AV": "#58a6ff", "RU": "#f85149",
    "CA": "#3fb950", "UM": "#bc8cff", "DR": "#d29922",
}

# --- Data ---
analyzer = BinaryManifoldAnalyzer()
tracker = FibonacciDriftTracker()

clean_values = {
    1: 0.95, 2: 0.92, 3: PHI * 0.5, 4: PHI * 0.48,
    5: 0.15, 6: PHI * 0.3, 7: PHI * 0.35, 8: 0.88,
    9: 0.91, 10: 0.89, 11: 0.12, 12: 0.95, 13: 1.0, 14: 0.90,
}
adv_values = {
    1: 0.45, 2: 0.38, 3: 0.99, 4: 0.02,
    5: 1.85, 6: 0.11, 7: 3.14, 8: 0.05,
    9: 0.22, 10: 0.15, 11: 2.3, 12: 0.08, 13: 0.0, 14: 0.10,
}

clean_snap = LayerSnapshot(values=clean_values, tongue="KO", risk_score=0.05,
                           decision="ALLOW", harmonic_wall=0.95, hyperbolic_distance=0.15)
adv_snap = LayerSnapshot(values=adv_values, tongue="KO", risk_score=0.92,
                         decision="DENY", harmonic_wall=0.08, hyperbolic_distance=1.85)

clean_m = analyzer.analyze(clean_snap)
adv_m = analyzer.analyze(adv_snap)
clean_s = tracker.track(clean_snap)
adv_s = tracker.track(adv_snap)


# =========================================================================
# FIGURE 1: Binary Manifold Walks
# =========================================================================
def fig1_binary_walks():
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle("Binary Manifold Walks: 728-Bit Mantissa Trajectories",
                 fontsize=16, fontweight="bold", color=WHITE)

    # Layer boundaries
    boundaries = [i * 52 for i in range(1, 14)]

    for ax, manifold, label, color, decision in [
        (axes[0], clean_m, "Safe Governance Operation", CYAN, "ALLOW"),
        (axes[1], adv_m, "Adversarial Operation", RED, "DENY"),
    ]:
        walk = manifold.full_walk
        x = np.arange(len(walk))
        y = np.array(walk)

        # Color segments by tongue
        for i in range(14):
            start = i * 52
            end = min((i + 1) * 52 + 1, len(walk))
            tongue = LAYER_TONGUE_RESONANCE[i + 1]
            tc = TONGUE_COLORS[tongue]
            ax.plot(x[start:end], y[start:end], color=tc, linewidth=0.8, alpha=0.9)

        # Layer boundaries
        for b in boundaries:
            ax.axvline(x=b, color=DIM, linewidth=0.3, alpha=0.4)

        # Fill above/below zero
        ax.fill_between(x, y, 0, where=y > 0, alpha=0.1, color=GREEN)
        ax.fill_between(x, y, 0, where=y < 0, alpha=0.1, color=RED)

        ax.axhline(y=0, color=DIM, linewidth=0.5)
        ax.set_ylabel("Walk Position")
        ax.set_title(f"{label} ({decision})", color=color, fontsize=13)
        ax.grid(True, alpha=0.3)

        # Stats annotation
        stats = (f"Fib: {manifold.total_fibonacci_score:.3f}  "
                 f"QC: {manifold.quasicrystal_quality:.3f}  "
                 f"Range: {manifold.walk_range}")
        ax.text(0.98, 0.95, stats, transform=ax.transAxes, fontsize=9,
                va="top", ha="right", color=DIM,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0d1117", alpha=0.8))

    axes[1].set_xlabel("Bit Position (14 layers x 52 mantissa bits = 728 total)")

    # Tongue legend
    patches = [mpatches.Patch(color=TONGUE_COLORS[t], label=t) for t in TONGUE_COLORS]
    fig.legend(handles=patches, loc="lower center", ncol=6, fontsize=9,
               framealpha=0.3, edgecolor=DIM)

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    path = os.path.join(FIG_DIR, "fig1_binary_manifold_walks.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =========================================================================
# FIGURE 2: Harmonic Wall Cost Surface
# =========================================================================
def fig2_harmonic_wall():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Harmonic Wall: H(d, R) = R^(d²)",
                 fontsize=16, fontweight="bold", color=WHITE)

    # Left: 2D curve with risk zones
    d = np.linspace(0, 3.5, 500)
    h = PHI ** (d ** 2)

    ax1.semilogy(d, h, color=GOLD, linewidth=2.5)

    # Risk zones
    zones = [
        (0, 0.5, GREEN, "ALLOW", 0.15),
        (0.5, 1.0, CYAN, "CAUTION", 0.15),
        (1.0, 1.5, ORANGE, "ESCALATE", 0.15),
        (1.5, 2.5, RED, "DENY", 0.10),
        (2.5, 3.5, PURPLE, "ADVERSARIAL", 0.08),
    ]
    for d_lo, d_hi, color, label, alpha in zones:
        ax1.axvspan(d_lo, d_hi, alpha=alpha, color=color)
        mid = (d_lo + d_hi) / 2
        y_mid = PHI ** (mid ** 2)
        ax1.text(mid, y_mid * 1.5, label, ha="center", fontsize=8,
                 color=color, fontweight="bold")

    ax1.set_xlabel("Hyperbolic Distance d_H")
    ax1.set_ylabel("Cost Multiplier H(d)")
    ax1.set_title("Exponential Cost Scaling", fontsize=13)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0.8, 200)

    # Key points
    for d_val, label in [(1.0, "phi"), (2.0, "6.85x"), (3.0, "76x")]:
        h_val = PHI ** (d_val ** 2)
        ax1.plot(d_val, h_val, "o", color=GOLD, markersize=8)
        ax1.annotate(f"d={d_val}: {h_val:.1f}x", (d_val, h_val),
                     textcoords="offset points", xytext=(10, 10),
                     fontsize=9, color=GOLD)

    # Right: 2D contour map (x,y plane through Poincare ball)
    x_grid = np.linspace(-1, 1, 200)
    y_grid = np.linspace(-1, 1, 200)
    X, Y = np.meshgrid(x_grid, y_grid)
    R_sq = X ** 2 + Y ** 2

    # Mask outside unit ball
    mask = R_sq >= 1.0
    R_sq[mask] = np.nan

    # Hyperbolic distance from origin: d_H = arccosh(1 + 2r²/(1-r²))
    # Simplified: for origin, d_H = 2 * arctanh(r)
    r = np.sqrt(R_sq)
    r_safe = np.clip(r, 0, 0.999)
    d_H = 2 * np.arctanh(r_safe)

    # Cost
    cost = PHI ** (d_H ** 2)
    cost[mask] = np.nan

    # Plot
    levels = [1, 1.5, 2, 3, 5, 10, 20, 50, 100]
    cs = ax2.contourf(X, Y, cost, levels=levels, cmap="inferno", extend="max")
    ax2.contour(X, Y, cost, levels=levels, colors=DIM, linewidths=0.5, alpha=0.5)

    # Unit circle boundary
    theta = np.linspace(0, 2 * np.pi, 100)
    ax2.plot(np.cos(theta), np.sin(theta), color=WHITE, linewidth=1.5, linestyle="--")

    # Safe origin
    ax2.plot(0, 0, "o", color=GREEN, markersize=10, zorder=5)
    ax2.text(0.05, 0.05, "Safe\nOrigin", color=GREEN, fontsize=9, fontweight="bold")

    # Adversarial example point
    ax2.plot(0.65, 0.3, "x", color=RED, markersize=12, markeredgewidth=2, zorder=5)
    ax2.text(0.68, 0.35, "Adversarial", color=RED, fontsize=9)

    cbar = fig.colorbar(cs, ax=ax2, label="Cost Multiplier")
    cbar.ax.yaxis.label.set_color(WHITE)
    cbar.ax.tick_params(colors=DIM)

    ax2.set_xlabel("Poincare Ball x")
    ax2.set_ylabel("Poincare Ball y")
    ax2.set_title("Cost Landscape in Poincare Ball", fontsize=13)
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig2_harmonic_wall_surface.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =========================================================================
# FIGURE 3: Fibonacci Spiral Fingerprints
# =========================================================================
def fig3_fibonacci_spirals():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6),
                                    subplot_kw={"projection": "polar"})
    fig.suptitle("Fibonacci Spiral Governance Fingerprints",
                 fontsize=16, fontweight="bold", color=WHITE)

    golden_angle = math.pi * (3 - math.sqrt(5))

    for ax, snap, sig, label, color in [
        (ax1, clean_snap, clean_s, "Safe (ALLOW)", CYAN),
        (ax2, adv_snap, adv_s, "Adversarial (DENY)", RED),
    ]:
        thetas = []
        radii = []
        colors_list = []
        for i, pt in enumerate(sig.points):
            thetas.append(pt.theta)
            radii.append(pt.radius)
            tongue = LAYER_TONGUE_RESONANCE[i + 1]
            colors_list.append(TONGUE_COLORS[tongue])

        # Spiral path
        ax.plot(thetas, radii, color=color, linewidth=1.5, alpha=0.6)

        # Points colored by tongue
        for t, r, c in zip(thetas, radii, colors_list):
            ax.plot(t, r, "o", color=c, markersize=10, zorder=5)

        ax.set_title(f"{label}\nDrift: {sig.total_drift:.2f}",
                     color=color, fontsize=12, pad=15)
        ax.set_facecolor("#161b22")
        ax.tick_params(colors=DIM)
        ax.grid(True, alpha=0.3)

    # Legend
    patches = [mpatches.Patch(color=TONGUE_COLORS[t], label=f"L{i*2+1}-{i*2+2}: {t}")
               for i, t in enumerate(["KO", "AV", "RU", "CA", "UM", "DR"])]
    fig.legend(handles=patches, loc="lower center", ncol=6, fontsize=8,
               framealpha=0.3, edgecolor=DIM)

    plt.tight_layout(rect=[0, 0.06, 1, 0.93])
    path = os.path.join(FIG_DIR, "fig3_fibonacci_spirals.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =========================================================================
# FIGURE 4: 14-Layer Pipeline Comparison
# =========================================================================
def fig4_layer_comparison():
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("14-Layer Pipeline: Clean vs Adversarial",
                 fontsize=16, fontweight="bold", color=WHITE)

    layers = list(range(1, 15))
    clean_vals = [clean_values[i] for i in layers]
    adv_vals = [adv_values[i] for i in layers]
    tongues = [LAYER_TONGUE_RESONANCE[i] for i in layers]
    tongue_c = [TONGUE_COLORS[t] for t in tongues]

    # Top-left: Layer values bar chart
    ax = axes[0, 0]
    x = np.arange(14)
    width = 0.35
    bars1 = ax.bar(x - width / 2, clean_vals, width, color=CYAN, alpha=0.8, label="Clean")
    bars2 = ax.bar(x + width / 2, adv_vals, width, color=RED, alpha=0.8, label="Adversarial")
    ax.set_xlabel("Layer")
    ax.set_ylabel("Value")
    ax.set_title("Layer Values", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([f"L{i}" for i in layers], fontsize=8)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")

    # Top-right: Per-layer Fibonacci scores
    ax = axes[0, 1]
    clean_fib = [l.fibonacci_score for l in clean_m.layers]
    adv_fib = [l.fibonacci_score for l in adv_m.layers]
    ax.plot(layers, clean_fib, "o-", color=CYAN, linewidth=2, label="Clean")
    ax.plot(layers, adv_fib, "s--", color=RED, linewidth=2, label="Adversarial")
    for i, t in enumerate(tongues):
        ax.axvspan(i + 0.5, i + 1.5, alpha=0.05, color=TONGUE_COLORS[t])
    ax.set_xlabel("Layer")
    ax.set_ylabel("Fibonacci Score")
    ax.set_title("Per-Layer Fibonacci Structure", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(layers)

    # Bottom-left: Walk endpoints (manifold projection)
    ax = axes[1, 0]
    clean_ep = clean_m.layer_walk_endpoints
    adv_ep = adv_m.layer_walk_endpoints
    for i in range(14):
        ax.plot(i + 1, clean_ep[i], "o", color=TONGUE_COLORS[tongues[i]],
                markersize=10, zorder=5)
        ax.plot(i + 1, adv_ep[i], "x", color=TONGUE_COLORS[tongues[i]],
                markersize=10, markeredgewidth=2, zorder=5)
    ax.plot(layers, clean_ep, "-", color=CYAN, linewidth=1.5, alpha=0.6, label="Clean (o)")
    ax.plot(layers, adv_ep, "--", color=RED, linewidth=1.5, alpha=0.6, label="Adversarial (x)")
    ax.set_xlabel("Layer")
    ax.set_ylabel("Walk Endpoint (52-bit)")
    ax.set_title("Manifold Projection: Walk Endpoints", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(layers)

    # Bottom-right: Bit density heatmap
    ax = axes[1, 1]
    clean_density = [l.ones_density for l in clean_m.layers]
    adv_density = [l.ones_density for l in adv_m.layers]
    data = np.array([clean_density, adv_density])
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0.3, vmax=0.7)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Clean", "Adversarial"])
    ax.set_xticks(range(14))
    ax.set_xticklabels([f"L{i}" for i in layers], fontsize=8)
    ax.set_xlabel("Layer")
    ax.set_title("Ones Density per Layer (0.5 = balanced)", fontsize=13)
    cbar = fig.colorbar(im, ax=ax)
    cbar.ax.yaxis.label.set_color(WHITE)
    cbar.ax.tick_params(colors=DIM)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig4_layer_comparison.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =========================================================================
# FIGURE 5: Poincare Ball Risk Zones
# =========================================================================
def fig5_poincare_risk_zones():
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.suptitle("Poincare Ball Governance Space",
                 fontsize=16, fontweight="bold", color=WHITE)

    # Unit circle
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), color=WHITE, linewidth=2)

    # Cost contour rings (at specific hyperbolic distances)
    for d_h, label, color in [
        (0.5, "d=0.5 (1.13x)", GREEN),
        (1.0, "d=1.0 (1.62x)", CYAN),
        (1.5, "d=1.5 (2.95x)", ORANGE),
        (2.0, "d=2.0 (6.85x)", RED),
    ]:
        # Euclidean radius for given hyperbolic distance from origin
        # d_H = 2 * arctanh(r) => r = tanh(d_H / 2)
        r = math.tanh(d_h / 2)
        circle = plt.Circle((0, 0), r, fill=False, color=color,
                             linewidth=1.5, linestyle="--", alpha=0.7)
        ax.add_patch(circle)
        ax.text(r * 0.707 + 0.03, r * 0.707 + 0.03, label,
                color=color, fontsize=9, fontweight="bold")

    # Filled risk zones
    r_allow = math.tanh(0.5 / 2)
    r_caution = math.tanh(1.0 / 2)
    r_escalate = math.tanh(1.5 / 2)
    r_deny = math.tanh(2.0 / 2)

    zones_fill = [
        (0, r_allow, GREEN, "ALLOW", 0.15),
        (r_allow, r_caution, CYAN, "CAUTION", 0.10),
        (r_caution, r_escalate, ORANGE, "ESCALATE", 0.10),
        (r_escalate, 1.0, RED, "DENY", 0.08),
    ]
    for r_in, r_out, color, label, alpha in zones_fill:
        wedge = mpatches.Annulus((0, 0), r_out, r_out - r_in,
                                 facecolor=color, alpha=alpha)
        ax.add_patch(wedge)

    # Safe origin
    ax.plot(0, 0, "o", color=GREEN, markersize=15, zorder=10)
    ax.text(0.03, -0.05, "Safe Origin", color=GREEN, fontsize=11, fontweight="bold")

    # Sacred Tongue directions (6 directions at 60-degree intervals)
    tongue_angles = {"KO": 0, "AV": 60, "RU": 120, "CA": 180, "UM": 240, "DR": 300}
    for tongue, angle_deg in tongue_angles.items():
        angle = math.radians(angle_deg)
        weight = TONGUE_WEIGHTS[tongue]
        # Arrow length proportional to weight (normalized)
        arr_len = min(0.9, weight / 12)
        dx = arr_len * math.cos(angle)
        dy = arr_len * math.sin(angle)
        ax.annotate("", xy=(dx, dy), xytext=(0, 0),
                     arrowprops=dict(arrowstyle="->", color=TONGUE_COLORS[tongue],
                                     linewidth=2))
        # Label at end
        label_r = arr_len + 0.06
        ax.text(label_r * math.cos(angle), label_r * math.sin(angle),
                f"{tongue}\n(w={weight:.2f})", ha="center", va="center",
                color=TONGUE_COLORS[tongue], fontsize=9, fontweight="bold")

    # Example points
    # Clean operation: close to origin
    ax.plot(0.07, 0.05, "*", color=CYAN, markersize=15, zorder=10)
    ax.text(0.12, 0.08, "Clean Op\n(d=0.15)", color=CYAN, fontsize=9)

    # Adversarial: far from origin
    r_adv = math.tanh(1.85 / 2)
    ax.plot(r_adv * 0.8, r_adv * 0.5, "X", color=RED, markersize=15,
            markeredgewidth=2, zorder=10)
    ax.text(r_adv * 0.8 + 0.03, r_adv * 0.5 - 0.06,
            f"Adversarial\n(d=1.85, {PHI ** (1.85 ** 2):.1f}x cost)",
            color=RED, fontsize=9)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_aspect("equal")
    ax.set_xlabel("Poincare Ball x-axis")
    ax.set_ylabel("Poincare Ball y-axis")
    ax.grid(True, alpha=0.2)

    # Zone legend
    legend_patches = [
        mpatches.Patch(color=GREEN, alpha=0.3, label="ALLOW (d < 0.5)"),
        mpatches.Patch(color=CYAN, alpha=0.3, label="CAUTION (0.5 < d < 1.0)"),
        mpatches.Patch(color=ORANGE, alpha=0.3, label="ESCALATE (1.0 < d < 1.5)"),
        mpatches.Patch(color=RED, alpha=0.3, label="DENY (d > 1.5)"),
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9,
              framealpha=0.5, edgecolor=DIM)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig5_poincare_risk_zones.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# =========================================================================
# Run all
# =========================================================================
if __name__ == "__main__":
    print("Generating grant figures...")
    fig1_binary_walks()
    fig2_harmonic_wall()
    fig3_fibonacci_spirals()
    fig4_layer_comparison()
    fig5_poincare_risk_zones()
    print(f"\nAll figures saved to: {FIG_DIR}")
