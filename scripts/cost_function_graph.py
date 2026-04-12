"""
SCBE-AETHERMOORE — Cost Function Architecture Visualizer
Generates 8-panel figure: docs/cost_function_graph.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

phi = (1 + np.sqrt(5)) / 2  # 1.6180…

d = np.linspace(0, 3.5, 500)
t = np.linspace(0, 10, 500)

# ── Cost functions ────────────────────────────────────────────────────────────
H_phi   = phi ** ((phi * d) ** 2)
H_2     = 2.0 ** (d ** 2)
S_score = 1.0 / (1.0 + d + 0.2 * d ** 2)
Gamma   = np.exp(-np.minimum(H_phi, 300))

tongue_names = ["Kor", "Ava", "Run", "Cas", "Umb", "Dra"]
tongue_k     = [0, 1, 2, 3, 4, 5]

d_tri_short  = 0.5 + 0.4  * np.sin(0.8  * t)
d_tri_medium = 0.3 + 0.2  * np.sin(0.2  * t + 1.0)
d_tri_long   = 0.2 + 0.05 * np.sin(0.05 * t + 2.0)
d_tri = 0.5 * d_tri_short + 0.3 * d_tri_medium + 0.2 * d_tri_long

# ── Figure ────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 14), facecolor="#0d0f1a")
fig.suptitle(
    "SCBE-AETHERMOORE  ·  Cost Function Architecture",
    fontsize=17, color="#e8e0ff", fontweight="bold", y=0.98,
)
gs = gridspec.GridSpec(
    3, 3, figure=fig,
    hspace=0.52, wspace=0.38,
    left=0.07, right=0.97, top=0.93, bottom=0.06,
)

PANEL_BG = "#12152a"
GRID_COL = "#1e2540"
AXIS_COL = "#3a4070"
TEXT_COL = "#c8c0f0"


def _panel(ax, title):
    ax.set_facecolor(PANEL_BG)
    for sp in ax.spines.values():
        sp.set_edgecolor(AXIS_COL)
    ax.tick_params(colors=TEXT_COL, labelsize=8)
    ax.set_title(title, color="#a090ff", fontsize=10)
    ax.grid(True, color=GRID_COL, linewidth=0.6, linestyle="--")
    ax.set_xlabel("d  (hyperbolic distance)", color=TEXT_COL, fontsize=8)


# Panel 1 — Harmonic Wall
ax1 = fig.add_subplot(gs[0, 0])
_panel(ax1, "L12 Harmonic Wall  H(d, R)")
ax1.plot(d, H_phi, color="#ff6b9d", lw=2,   label=f"R=phi={phi:.3f}   phi^(phi*d)^2")
ax1.plot(d, H_2,   color="#69d2e7", lw=2,   label="R=2             2^(d^2)")
ax1.plot(d, d,     color="#aaaaaa", lw=1, ls=":", label="d  (linear ref)")
ax1.set_ylim(-0.5, 80)
ax1.set_ylabel("H(d, R)", color=TEXT_COL, fontsize=8)
ax1.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 2 — Safety Score
ax2 = fig.add_subplot(gs[0, 1])
_panel(ax2, "L12 Safety Score  S(d, pd)")
ax2.plot(d, S_score, color="#7fff7f", lw=2, label="S = 1/(1+d+2*pd)")
ax2.axhline(0.5,  color="#ffdd57", lw=1, ls="--", label="Quarantine  0.5")
ax2.axhline(0.25, color="#ff8c42", lw=1, ls="--", label="Escalate    0.25")
ax2.axhline(0.1,  color="#ff4444", lw=1, ls="--", label="Deny        0.1")
ax2.set_ylim(-0.02, 1.05)
ax2.set_ylabel("S  in (0, 1]", color=TEXT_COL, fontsize=8)
ax2.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 3 — Governance Damping
ax3 = fig.add_subplot(gs[0, 2])
_panel(ax3, "Governance Damping  Gamma = exp(-H)")
ax3.plot(d, Gamma, color="#c77dff", lw=2.5, label="Gamma(d) = exp(-phi^(phi*d)^2)")
ax3.fill_between(d, Gamma, alpha=0.15, color="#c77dff")
ax3.axhline(0.5, color="#aaaaaa", lw=1, ls=":", label="50% flight suppression")
ax3.set_ylim(-0.02, 1.05)
ax3.set_ylabel("Gamma  (flight multiplier)", color=TEXT_COL, fontsize=8)
ax3.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 4 — Tongue Weights
ax4 = fig.add_subplot(gs[1, 0])
_panel(ax4, "L3 Tongue Weights  tau_k(d) = 1/(1+phi^k * d)")
cols = ["#ff6b6b", "#ffd93d", "#6bcb77", "#4d96ff", "#c77dff", "#ff9a3c"]
for name, k, c in zip(tongue_names, tongue_k, cols):
    ax4.plot(d, 1.0 / (1.0 + phi**k * d), color=c, lw=1.8,
             label=f"{name}  phi^{k}={phi**k:.2f}")
ax4.set_ylim(-0.02, 1.05)
ax4.set_ylabel("tau_k(d)", color=TEXT_COL, fontsize=8)
ax4.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 5 — Triadic Temporal Distance
ax5 = fig.add_subplot(gs[1, 1])
_panel(ax5, "L11 Triadic Distance  d_tri(t)")
ax5.set_xlabel("t  (time steps)", color=TEXT_COL, fontsize=8)
ax5.plot(t, d_tri_short,  color="#69d2e7", lw=1.2, ls="--", label="Short  (w=0.5)")
ax5.plot(t, d_tri_medium, color="#ffd93d", lw=1.2, ls="--", label="Medium (w=0.3)")
ax5.plot(t, d_tri_long,   color="#ff9a3c", lw=1.2, ls="--", label="Long   (w=0.2)")
ax5.plot(t, d_tri,        color="#ffffff",  lw=2.2,           label="d_tri  composite")
ax5.set_ylabel("d_tri(t)", color=TEXT_COL, fontsize=8)
ax5.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 6 — Flight-Governance Coupling
ax6 = fig.add_subplot(gs[1, 2])
_panel(ax6, "Flight-Governance Coupling  x_dot_actual")
d_drift  = np.linspace(0, 3.5, 500)
H_drift  = phi ** ((phi * d_drift) ** 2)
gamma_d  = np.exp(-np.minimum(H_drift, 300))
v_lift   = 0.15 * np.exp(-d_drift)
x_actual = gamma_d + v_lift
ax6.plot(d_drift, np.ones_like(d_drift), color="#aaaaaa", lw=1, ls=":", label="Raw flight intent (=1)")
ax6.plot(d_drift, gamma_d,    color="#c77dff", lw=1.5, ls="--", label="Gamma(d)  damping")
ax6.plot(d_drift, v_lift,     color="#ffd93d", lw=1.5, ls="--", label="v_lift  (tongue lift)")
ax6.plot(d_drift, x_actual,   color="#7fff7f", lw=2.5,           label="x_actual  (governed)")
ax6.fill_between(d_drift, x_actual, alpha=0.12, color="#7fff7f")
ax6.set_ylim(-0.02, 1.2)
ax6.set_ylabel("x_dot_actual", color=TEXT_COL, fontsize=8)
ax6.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 7 — Pipeline Cost Accumulation
ax7 = fig.add_subplot(gs[2, :2])
_panel(ax7, "Pipeline Cost Accumulation  L1 -> L14  (at d=1.5 / 2.5 / 3.5)")
ax7.set_xlabel("")
layers = [
    "L1\nctx", "L2\nreal", "L3\nwgt",  "L4\nPoin", "L5\nd_H",
    "L6\nbrth", "L7\nMob",  "L8\nd*",   "L9\nspec", "L10\nspin",
    "L11\ntri",  "L12\nH",   "L13\ndec", "L14\naudio",
]
x_pos = np.arange(len(layers))


def pipeline_cost(dv):
    base = np.zeros(14)
    base[0]  = 0.1
    base[1]  = 0.1  + 0.05  * dv
    base[2]  = base[1] + 0.05 * dv * phi
    base[3]  = base[2] + 0.1  * dv
    base[4]  = dv
    base[5]  = dv * 0.95
    base[6]  = base[5] * 0.95
    base[7]  = dv
    base[8]  = dv * 0.8
    base[9]  = dv * 0.75
    base[10] = dv * 0.9
    base[11] = min(phi ** ((phi * dv) ** 2), 80)
    base[12] = base[11]
    base[13] = base[11] * 0.5
    return base


c15 = pipeline_cost(1.5)
c25 = pipeline_cost(2.5)
c35 = pipeline_cost(3.5)

ax7.plot(x_pos, c15, "o-", color="#7fff7f", lw=2, markersize=5, label="d=1.5  mild drift")
ax7.plot(x_pos, c25, "s-", color="#ffdd57", lw=2, markersize=5, label="d=2.5  moderate drift")
ax7.plot(x_pos, c35, "^-", color="#ff6b6b", lw=2, markersize=5, label="d=3.5  adversarial")
ax7.set_xticks(x_pos)
ax7.set_xticklabels(layers, color=TEXT_COL, fontsize=8)
ax7.axvline(11, color="#ff6b9d", lw=1.5, ls="--", alpha=0.8, label="L12 harmonic wall spike")
ax7.set_ylabel("Accumulated cost", color=TEXT_COL, fontsize=8)
ax7.legend(fontsize=8, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

# Panel 8 — Decision Regime Phase Diagram
ax8 = fig.add_subplot(gs[2, 2])
_panel(ax8, "L13 Decision Regimes  (d* vs H)")
d_grid = np.linspace(0, 3.5, 300)
H_grid = np.minimum(phi ** ((phi * d_grid) ** 2), 100)
ax8.plot(d_grid, H_grid, color="#ff6b9d", lw=2.5, label="H(d*, phi)")
ax8.axhspan(0,   2,  alpha=0.12, color="#7fff7f", label="ALLOW")
ax8.axhspan(2,   8,  alpha=0.12, color="#ffdd57", label="QUARANTINE")
ax8.axhspan(8,   25, alpha=0.12, color="#ff8c42", label="ESCALATE")
ax8.axhspan(25, 100, alpha=0.12, color="#ff4444", label="DENY")
ax8.set_ylim(0, 60)
ax8.set_ylabel("H(d*, R)", color=TEXT_COL, fontsize=8)
ax8.legend(fontsize=7, facecolor="#0d0f1a", labelcolor=TEXT_COL, framealpha=0.8)

out = "docs/cost_function_graph.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#0d0f1a")
print(f"Saved: {out}")
