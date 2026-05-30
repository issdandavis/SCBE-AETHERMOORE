"""
@file visualize.py
@module geoseed/visualize
@component GeoSeed Orbital Visualizations

Three outputs (all optional, degrade gracefully):
  1. ASCII shell map   — always works, no deps
  2. Radial profiles   — requires matplotlib (png saved to artifacts/)
  3. Poincaré disk map — requires matplotlib (png saved to artifacts/)
"""

import math
import os
import sys

PHI = (1.0 + math.sqrt(5.0)) / 2.0

# ── ASCII shell map ───────────────────────────────────────────────────────────

_BAR_WIDTH = 50
_ORBITAL_SYMBOLS = {0: "●", 1: "◉", 2: "⊕", 3: "✦", 4: "⊛", 5: "❋"}
_ORBITAL_NAMES   = {0: "s", 1: "p", 2: "d", 3: "f", 4: "g", 5: "h"}


def ascii_shell_map(orbitals) -> str:
    lines = []
    lines.append("GeoSeed Hyperbolic Orbital Shell Map  (Poincaré ball, H³)")
    lines.append("centre ──────────────────────────────────── boundary")
    lines.append("")

    for o in orbitals:
        # Position marker along bar width
        pos = int(o.poincare_r * _BAR_WIDTH)
        bar = [" "] * _BAR_WIDTH
        if pos < _BAR_WIDTH:
            bar[pos] = _ORBITAL_SYMBOLS.get(o.l, "○")

        sym = _ORBITAL_SYMBOLS.get(o.l, "?")
        name_str = f"{o.abbr} ({_ORBITAL_NAMES[o.l]})"
        bar_str = "".join(bar)
        r_str = f"r={o.poincare_r:.3f}"
        lb_str = f"λ={int(o.lb_eigenvalue):>4}"
        m_str = f"m×{o.m_states}"
        lines.append(f"{name_str:<10} |{bar_str}| {r_str}  {lb_str}  {m_str}")

    lines.append("")
    lines.append(f"  Uniform gap between shells: Δρ = ln(φ) = {math.log(PHI):.6f}")
    lines.append(f"  CA (f-orbital) anchors at r = 1/φ = {1/PHI:.9f}")
    lines.append(f"  Total m-states: {sum(o.m_states for o in orbitals)}  (= 1+3+5+7+9+11)")
    lines.append("")
    lines.append("Eigenvalue ladder  ─────────────────────────────────────────")
    lines.append("  l  tongue    λ = -(l+1)²   gap Δλ")
    prev = None
    for o in orbitals:
        lam = int(o.lb_eigenvalue)
        gap = f"  Δ={lam - prev}" if prev is not None else "  (origin)"
        lines.append(f"  {o.l}  {o.abbr:<12} {lam:>6}        {gap}")
        prev = lam
    return "\n".join(lines)


def ascii_radial_profile(orbital, width: int = 60, height: int = 12) -> str:
    """ASCII plot of |R(ρ)|² along the radial axis for one orbital."""
    # Sample ρ from 0 to 3·hyperbolic_rho (or 3.0 minimum)
    rho_max = max(3.0 * orbital.hyperbolic_rho, 1.5)
    n_samples = width * 2
    rhos = [rho_max * i / (n_samples - 1) for i in range(n_samples)]

    try:
        vals = [orbital.peak_density_at_rho(rho) for rho in rhos]
    except AttributeError:
        # Fall back to radial_wavefunction²
        try:
            from src.geoseed.orbital_model import radial_wavefunction
            vals = [radial_wavefunction(rho, orbital.l) ** 2 for rho in rhos]
        except Exception:
            vals = [0.0] * n_samples

    max_val = max(vals) if any(v > 0 for v in vals) else 1.0
    norm = [v / max_val for v in vals]

    # Downsample to width columns
    col_vals = []
    step = n_samples // width
    for i in range(width):
        chunk = norm[i * step:(i + 1) * step]
        col_vals.append(max(chunk) if chunk else 0.0)

    # Build grid
    rows = []
    for row in range(height, 0, -1):
        threshold = row / height
        line = ""
        for v in col_vals:
            line += "█" if v >= threshold else " "
        rows.append(f"  |{line}|")

    rows.append(f"  0{'─'*width}{rho_max:.1f} ρ")
    header = f"  R²(ρ)  {orbital.abbr} ({_ORBITAL_NAMES[orbital.l]}-orbital, l={orbital.l})  max={max_val:.2e}"
    return header + "\n" + "\n".join(rows)


def ascii_poincare_disk(orbitals, radius: int = 20) -> str:
    """ASCII Poincaré disk cross-section showing concentric shell rings."""
    size = radius * 2 + 1
    grid = [[" "] * size for _ in range(size)]

    # Draw boundary circle
    for angle_i in range(360):
        a = math.radians(angle_i)
        x = int(round(radius * math.cos(a)))
        y = int(round(radius * math.sin(a) * 0.5))  # aspect-correct
        gx, gy = x + radius, y + radius
        if 0 <= gx < size and 0 <= gy < size:
            grid[gy][gx] = "·"

    # Draw shells
    symbols = list(_ORBITAL_SYMBOLS.values())
    for idx, o in enumerate(orbitals):
        if o.poincare_r == 0.0:
            grid[radius][radius] = symbols[0]
            continue
        r_px = o.poincare_r * radius
        for angle_i in range(0, 360, 3):
            a = math.radians(angle_i)
            x = int(round(r_px * math.cos(a)))
            y = int(round(r_px * math.sin(a) * 0.5))
            gx, gy = x + radius, y + radius
            if 0 <= gx < size and 0 <= gy < size:
                grid[gy][gx] = symbols[idx % len(symbols)]

    lines = ["  Poincaré disk (equatorial cross-section):"]
    for row in grid:
        lines.append("  " + "".join(row))

    lines.append("")
    for idx, o in enumerate(orbitals):
        lines.append(f"  {symbols[idx % len(symbols)]} {o.abbr}  r={o.poincare_r:.3f}  {_ORBITAL_NAMES[o.l]}-orbital")
    return "\n".join(lines)


# ── Matplotlib plots (optional) ───────────────────────────────────────────────

def _ensure_artifacts_dir(base: str = ".") -> str:
    path = os.path.join(base, "artifacts", "geoseed")
    os.makedirs(path, exist_ok=True)
    return path


def plot_shell_positions(orbitals, out_dir: str = ".") -> str:
    """Save shell position bar chart as PNG. Returns path."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return "(matplotlib not available — skipped)"

    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
    labels = [f"{o.abbr}\n({_ORBITAL_NAMES[o.l]})" for o in orbitals]
    rs = [o.poincare_r for o in orbitals]

    ax.barh(labels, rs, color=colors, edgecolor="white", height=0.6)
    ax.axvline(1.0 / PHI, color="gold", linestyle="--", linewidth=1.5,
               label=f"1/φ = {1/PHI:.3f} (CA anchor)")
    ax.axvline(1.0, color="grey", linestyle=":", linewidth=1, label="Ball boundary")
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Poincaré ball radius r")
    ax.set_title("GeoSeed Orbital Shell Positions in H³  (uniform Δρ = ln φ)")
    ax.legend(loc="lower right")

    # Annotate gaps
    for i in range(1, len(orbitals)):
        mid = (rs[i] + rs[i - 1]) / 2
        ax.annotate("Δρ=ln φ", xy=(mid, i - 0.5), fontsize=7,
                    ha="center", color="grey")

    plt.tight_layout()
    path = os.path.join(_ensure_artifacts_dir(out_dir), "shell_positions.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_radial_profiles(orbitals, out_dir: str = ".") -> str:
    """Save radial wavefunction profiles as PNG. Returns path."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from src.geoseed.orbital_model import radial_wavefunction
    except ImportError:
        return "(matplotlib or orbital_model not available — skipped)"

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]

    for idx, (o, ax) in enumerate(zip(orbitals, axes.flat)):
        rho_max = max(4.0, 3.0 * o.hyperbolic_rho)
        rhos = np.linspace(1e-4, rho_max, 500)
        R = np.array([radial_wavefunction(float(r), o.l) for r in rhos])
        R2 = R ** 2
        # Hyperbolic volume-weighted density: |R|² × sinh²(ρ)
        vol_R2 = R2 * np.sinh(rhos) ** 2

        ax.plot(rhos, R2 / (R2.max() + 1e-30), color=colors[idx],
                label="|R|²", linewidth=1.5)
        ax.plot(rhos, vol_R2 / (vol_R2.max() + 1e-30), color=colors[idx],
                linestyle="--", alpha=0.6, label="|R|²·sinh²ρ")
        ax.axvline(o.hyperbolic_rho, color="gold", linestyle=":", linewidth=1,
                   label=f"ρ_seed={o.hyperbolic_rho:.2f}")
        ax.set_title(f"{o.abbr} — {_ORBITAL_NAMES[o.l]}-orbital (l={o.l})")
        ax.set_xlabel("ρ (hyperbolic distance)")
        ax.set_ylabel("normalised density")
        ax.legend(fontsize=7)
        ax.set_ylim(0, 1.1)

    fig.suptitle(
        "GeoSeed Hyperbolic Radial Wavefunctions  R(ρ) on H³\n"
        "Dashed = volume-weighted |R|²·sinh²ρ  |  Gold line = seed-sphere depth",
        fontsize=11,
    )
    plt.tight_layout()
    path = os.path.join(_ensure_artifacts_dir(out_dir), "radial_profiles.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_poincare_disk(orbitals, out_dir: str = ".") -> str:
    """Save 2D Poincaré disk cross-section as PNG. Returns path."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return "(matplotlib not available — skipped)"

    fig, ax = plt.subplots(figsize=(7, 7))
    theta = np.linspace(0, 2 * np.pi, 360)
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]

    # Boundary
    ax.plot(np.cos(theta), np.sin(theta), "k-", linewidth=2, label="Ball boundary")

    # Shells
    for idx, o in enumerate(orbitals):
        r = o.poincare_r
        if r == 0.0:
            ax.plot(0, 0, "o", color=colors[idx], markersize=10,
                    label=f"{o.abbr} ({_ORBITAL_NAMES[o.l]}, r=0)")
            continue
        ax.plot(r * np.cos(theta), r * np.sin(theta),
                color=colors[idx], linewidth=2,
                label=f"{o.abbr} ({_ORBITAL_NAMES[o.l]}, r={r:.3f})")
        # Egg nodes (project to 2D equatorial plane)
        for x, y, z in o.egg_nodes:
            eq_r = math.sqrt(x**2 + z**2)
            eq_theta = math.atan2(z, x)
            ax.plot(eq_r * math.cos(eq_theta), eq_r * math.sin(eq_theta),
                    ".", color=colors[idx], markersize=3, alpha=0.5)

    # 1/φ reference
    ax.plot(1.0 / PHI * np.cos(theta), 1.0 / PHI * np.sin(theta),
            "gold", linestyle="--", linewidth=1, alpha=0.7, label="r = 1/φ (CA)")

    ax.set_aspect("equal")
    ax.set_title("GeoSeed Orbitals — Poincaré Disk Cross-Section\n"
                 "Dots = Sacred Egg quantisation nodes (equatorial projection)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)

    plt.tight_layout()
    path = os.path.join(_ensure_artifacts_dir(out_dir), "poincare_disk.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def main(out_dir: str = "."):
    from src.geoseed.orbital_model import build_geoseed_orbitals

    orbitals = build_geoseed_orbitals()

    # Always print ASCII
    print(ascii_shell_map(orbitals))
    print()
    print(ascii_poincare_disk(orbitals))
    print()
    for o in orbitals:
        if o.poincare_r > 0:
            print(ascii_radial_profile(o))
            print()

    # Attempt matplotlib outputs
    p1 = plot_shell_positions(orbitals, out_dir)
    p2 = plot_radial_profiles(orbitals, out_dir)
    p3 = plot_poincare_disk(orbitals, out_dir)
    print(f"Shell positions PNG : {p1}")
    print(f"Radial profiles PNG : {p2}")
    print(f"Poincaré disk PNG   : {p3}")


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    main(base)
