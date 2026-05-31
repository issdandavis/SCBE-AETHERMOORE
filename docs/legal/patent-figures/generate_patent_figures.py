"""
USPTO Patent Figures — SCBE-AETHERMOORE
Provisional No. 63/961,403 / Docket SCBE-2026-0001

Generates 6 black-and-white line drawings at 300 DPI.
Output: docs/legal/patent-figures/FIG_{1-6}.png + FIG_{1-6}.pdf
"""

import math
import os

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["font.size"] = 9

OUT = os.path.dirname(__file__)
DPI = 300


def save(fig, name):
    for ext in ("png", "pdf"):
        path = os.path.join(OUT, f"{name}.{ext}")
        fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white", edgecolor="none")
        print(f"  saved {path}")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 1  —  14-Layer Pipeline Block Diagram
# ─────────────────────────────────────────────────────────────────────────────
def fig1():
    layers = [
        ("L1", "Complex Context Ingestion", "z(t) ∈ ℂᴰ"),
        ("L2", "Realification", "ℂᴰ → ℝ²ᴰ"),
        ("L3", "φ-Weighted Transform", "G^(1/2)·x"),
        ("L4", "Poincaré Embedding", "u = tanh(α‖x‖)·x/‖x‖"),
        ("L5", "Hyperbolic Distance", "dH = arcosh(1 + 2‖u−v‖²/((1−‖u‖²)(1−‖v‖²)))"),
        ("L6", "Breathing Transform", "T_breath(u;t) = tanh(b·artanh(‖u‖))/‖u‖ · u"),
        ("L7", "Möbius Phase Transform", "T_phase = Q(t)·(a(t) ⊕ u)"),
        ("L8", "Multi-Well Realm Assignment", "k* = argmin_k dH(u, μk)"),
        ("L9", "Spectral Coherence", "FFT stability measure, bounded [0,1]"),
        ("L10", "Spin Coherence", "Phase alignment measure, bounded [0,1]"),
        ("L11", "Triadic Temporal Distance", "d_tri = √(w0·d0² + w1·d1² + w2·d2²)"),
        ("L12", "Harmonic Wall", "H(d,R) = R^(d²), R > 1"),
        ("L13", "Risk Decision Gate", "ALLOW / QUARANTINE / ESCALATE / DENY"),
        ("L14", "Audio Axis (Telemetry)", "FFT phase-encoded governance signal"),
    ]

    fig, ax = plt.subplots(figsize=(7.5, 11))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 15.5)
    ax.axis("off")

    ax.text(5, 15.1, "FIG. 1", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(5, 14.75, "14-Layer Authorization Pipeline", ha="center", va="center", fontsize=10)

    box_h = 0.72
    gap = 0.28
    top = 14.3

    for i, (label, title, formula) in enumerate(layers):
        y = top - i * (box_h + gap)
        # shaded box
        rect = FancyBboxPatch(
            (0.4, y - box_h),
            9.2,
            box_h,
            boxstyle="round,pad=0.04",
            linewidth=1.0,
            edgecolor="black",
            facecolor="#f0f0f0" if i % 2 == 0 else "white",
        )
        ax.add_patch(rect)
        ax.text(0.85, y - box_h / 2, label, ha="left", va="center", fontsize=8, fontweight="bold")
        ax.text(2.4, y - box_h * 0.35, title, ha="left", va="center", fontsize=8, fontweight="bold")
        ax.text(2.4, y - box_h * 0.72, formula, ha="left", va="center", fontsize=6.5, color="#333333")

        # arrow between boxes
        if i < len(layers) - 1:
            ya = y - box_h
            ax.annotate(
                "",
                xy=(5, ya - gap),
                xytext=(5, ya),
                arrowprops=dict(arrowstyle="->", color="black", lw=0.9),
            )

    # reference numerals
    ax.text(9.8, 14.3, "10", ha="left", va="center", fontsize=7)
    ax.text(9.8, 14.3 - 13 * (box_h + gap), "140", ha="left", va="center", fontsize=7)

    save(fig, "FIG_1")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 2  —  Alternative Harmonic Cost / Safety Functions
# ─────────────────────────────────────────────────────────────────────────────
def fig2():
    fig, ax = plt.subplots(figsize=(6.5, 5))

    d = np.linspace(0, 4.5, 500)
    PHI = (1 + math.sqrt(5)) / 2
    d_star = np.minimum(d, 3.0)
    h_exp = PHI ** (d**2)
    h_recip = 1 / (1 + d + 2 * (0.25 * d))
    h_clamped = math.pi ** (PHI * d_star)

    ax.semilogy(d, h_exp, "k-", lw=1.7, label="H(d,R) = R^(d^2), R = phi")
    ax.semilogy(d, h_clamped, "k--", lw=1.5, label="C = pi^(phi*min(d*, d_max))")
    ax.plot(d, h_recip, "k:", lw=1.8, label="Safety score = 1/(1+d+2*pd)")

    ax.set_xlabel("Measured drift or hyperbolic distance  d", fontsize=9)
    ax.set_ylabel("Cost or safety score (log scale for cost)", fontsize=9)
    ax.set_title("FIG. 2 — Alternative Harmonic Cost / Safety Functions", fontsize=10, fontweight="bold")
    ax.legend(fontsize=7.5, loc="upper left")
    ax.set_xlim(0, 4.5)
    ax.grid(True, which="both", lw=0.4, color="gray", alpha=0.5)

    ax.annotate(
        "Higher drift produces\nhigher cost or lower score",
        xy=(2.7, h_clamped[np.searchsorted(d, 2.7)]),
        xytext=(1.2, 1e3),
        fontsize=7.5,
        arrowprops=dict(arrowstyle="->", lw=0.9),
    )

    # reference numerals
    ax.text(0.05, ax.get_ylim()[1] * 0.5, "200", fontsize=7, color="black")

    fig.tight_layout()
    save(fig, "FIG_2")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 3  —  Poincaré Ball Cross-Section
# ─────────────────────────────────────────────────────────────────────────────
def fig3():
    fig, ax = plt.subplots(figsize=(6, 6.5))
    ax.set_aspect("equal")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.35, 1.4)
    ax.axis("off")

    ax.text(0, 1.32, "FIG. 3", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(0, 1.22, "Poincaré Ball — Concentric Ring Security Zones", ha="center", va="center", fontsize=9)

    # outer boundary
    outer = plt.Circle((0, 0), 1.0, fill=False, edgecolor="black", lw=2.0)
    ax.add_patch(outer)
    ax.text(0, -1.08, "Boundary (‖u‖ → 1)", ha="center", fontsize=7.5)

    # ring levels
    radii = [0.95, 0.8, 0.6, 0.4, 0.2]
    labels = ["Ring 4\n(Edge)", "Ring 3", "Ring 2", "Ring 1", "Ring 0\n(Core)"]
    linestyles = ["--", "--", "--", "--", "-"]
    for r, lbl, ls in zip(radii, labels, linestyles):
        c = plt.Circle((0, 0), r, fill=False, edgecolor="black", lw=0.8, linestyle=ls)
        ax.add_patch(c)
        ax.text(r * 0.707 + 0.02, r * 0.707 + 0.02, lbl, fontsize=6.5, color="black")

    # realm centers (multi-well)
    centers = [
        (0.15, 0.1, "μ₁\n(Auth realm)"),
        (-0.2, 0.18, "μ₂\n(Data realm)"),
        (0.1, -0.22, "μ₃\n(Exec realm)"),
        (-0.12, -0.15, "μ₄\n(Admin realm)"),
    ]
    for cx, cy, lbl in centers:
        ax.plot(cx, cy, "k+", ms=8, mew=1.5)
        ax.text(cx + 0.03, cy + 0.04, lbl, fontsize=6, ha="left")

    # session centroid
    ax.plot(0.08, 0.06, "k*", ms=11)
    ax.text(0.12, 0.09, "Session\ncentroid", fontsize=6.5, ha="left")

    # example safe trajectory (solid line)
    t = np.linspace(0, 1, 40)
    tx = 0.05 + 0.08 * np.sin(3 * t) * t
    ty = 0.04 + 0.07 * np.cos(2 * t) * t
    ax.plot(tx, ty, "k-", lw=1.0, label="Authorized session")

    # example adversarial trajectory (dashed, heading to edge)
    ax2 = np.linspace(0, 1, 30)
    adv_x = 0.1 + ax2 * 0.75
    adv_y = 0.05 + ax2 * 0.55
    ax.plot(adv_x, adv_y, "k:", lw=1.2, label="Adversarial drift")
    ax.annotate(
        "Exponential\ncost barrier",
        xy=(0.72, 0.53),
        xytext=(0.35, 0.82),
        fontsize=7,
        arrowprops=dict(arrowstyle="->", lw=0.8),
    )

    ax.legend(fontsize=7, loc="lower left")

    # reference numerals
    ax.text(1.18, 0.95, "300", fontsize=7)
    ax.text(1.18, 0.78, "310", fontsize=7)
    ax.text(1.18, -1.0, "320", fontsize=7)

    save(fig, "FIG_3")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 4  —  Six Sacred Tongues — φ-Weighted Coordinate System
# ─────────────────────────────────────────────────────────────────────────────
def fig4():
    PHI = (1 + math.sqrt(5)) / 2
    tongues = [
        ("KO\n(Kor'aelin)", PHI**0, "Intent & Command"),
        ("AV\n(Avali)", PHI**1, "Transport & Flow"),
        ("RU\n(Runethic)", PHI**2, "Policy & Rules"),
        ("CA\n(Cassisivadan)", PHI**3, "Compute & Execution"),
        ("UM\n(Umbroth)", PHI**4, "Security & Credentials"),
        ("DR\n(Draumric)", PHI**5, "Schema & Structure"),
    ]

    fig, (ax_bar, ax_wheel) = plt.subplots(1, 2, figsize=(10, 5.5))

    # ── left: bar chart of weights ──
    names = [t[0].replace("\n", " ") for t in tongues]
    weights = [t[1] for t in tongues]
    colors = ["black" if i < 3 else "#555555" for i in range(6)]
    hatches = ["", "", "", "///", "///", "///"]

    bars = ax_bar.barh(names, weights, color=["white"] * 6, edgecolor="black", lw=1.2, hatch=hatches)
    for i, (bar, w) in enumerate(zip(bars, weights)):
        ax_bar.text(w + 0.1, i, f"φ^{i} = {w:.3f}", va="center", fontsize=8)

    ax_bar.set_xlabel("Dimensional weight", fontsize=9)
    ax_bar.set_title("φ-Scaled Weights", fontsize=9, fontweight="bold")
    ax_bar.set_xlim(0, 15)
    ax_bar.invert_yaxis()
    ax_bar.axvline(1, color="black", lw=0.5, ls=":")

    # ── right: spoke diagram ──
    angles = [i * 2 * math.pi / 6 for i in range(6)]
    ax_wheel.set_aspect("equal")
    ax_wheel.set_xlim(-1.6, 1.6)
    ax_wheel.set_ylim(-1.6, 1.7)
    ax_wheel.axis("off")
    ax_wheel.set_title("Orthogonal Axes", fontsize=9, fontweight="bold")

    # draw unit circle reference
    theta = np.linspace(0, 2 * math.pi, 100)
    ax_wheel.plot(np.cos(theta), np.sin(theta), "k-", lw=0.5, alpha=0.3)

    for i, (name, weight, domain) in enumerate(tongues):
        a = angles[i]
        # spoke
        ax_wheel.plot([0, math.cos(a)], [0, math.sin(a)], "k-", lw=1.0)
        # weight indicator on spoke (normalized to max)
        r = weight / (PHI**5) * 1.0
        ax_wheel.plot(r * math.cos(a), r * math.sin(a), "ko", ms=5)
        # label outside
        lr = 1.25
        ax_wheel.text(
            lr * math.cos(a),
            lr * math.sin(a),
            f"{name}\n{domain}",
            ha="center",
            va="center",
            fontsize=6.5,
        )

    ax_wheel.plot(0, 0, "k+", ms=10, mew=2)

    fig.suptitle("FIG. 4 — Sacred Tongues: Six-Dimensional φ-Weighted Semantic Space", fontsize=10, fontweight="bold")
    fig.tight_layout()
    save(fig, "FIG_4")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 5  —  Sacred Egg: Five-Predicate Deferred Authorization
# ─────────────────────────────────────────────────────────────────────────────
def fig5():
    fig, ax = plt.subplots(figsize=(7, 9.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(5, 10.7, "FIG. 5", ha="center", fontsize=11, fontweight="bold")
    ax.text(5, 10.35, "Sacred Egg — Five-Predicate Deferred Authorization", ha="center", fontsize=9)

    predicates = [
        ("P₁: Tongue Membership", "Input tongue matches registered domain"),
        ("P₂: Geometric Ring Position", "‖u‖ ≤ ring_bound for assigned ring level"),
        ("P₃: Monotone Descent Path", "Ring level ≤ max(prior path) — no upward drift"),
        ("P₄: Quorum Approval", "trust-weighted consensus ≥ quorum_threshold"),
        ("P₅: AEAD Cryptographic Verification", "ML-KEM decapsulation + ML-DSA signature valid"),
    ]

    box_w = 5.5
    box_h = 0.72
    left_x = 2.2
    start_y = 9.5
    gap = 0.55

    # input arrow
    ax.annotate(
        "",
        xy=(5, start_y + 0.1),
        xytext=(5, start_y + 0.6),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="black"),
    )
    ax.text(5, start_y + 0.75, "Authorization Request", ha="center", fontsize=8.5)

    for i, (title, detail) in enumerate(predicates):
        y = start_y - i * (box_h + gap)
        cy = y - box_h / 2

        # predicate box
        rect = FancyBboxPatch(
            (left_x, y - box_h),
            box_w,
            box_h,
            boxstyle="round,pad=0.05",
            linewidth=1.2,
            edgecolor="black",
            facecolor="white",
        )
        ax.add_patch(rect)
        ax.text(left_x + 0.15, cy + 0.12, title, va="center", fontsize=8, fontweight="bold")
        ax.text(left_x + 0.15, cy - 0.12, detail, va="center", fontsize=6.5, color="#333333")

        # fail branch → noise
        ax.annotate(
            "",
            xy=(left_x + box_w + 1.4, cy),
            xytext=(left_x + box_w, cy),
            arrowprops=dict(arrowstyle="->", lw=0.9, color="black"),
        )
        fail_box = FancyBboxPatch(
            (left_x + box_w + 1.4, cy - 0.22),
            1.5,
            0.44,
            boxstyle="round,pad=0.03",
            linewidth=0.9,
            edgecolor="black",
            facecolor="#dddddd",
        )
        ax.add_patch(fail_box)
        ax.text(left_x + box_w + 2.15, cy, "NOISE", ha="center", va="center", fontsize=7.5, fontweight="bold")

        # FAIL label on branch
        ax.text(left_x + box_w + 0.7, cy + 0.12, "FAIL", fontsize=7, ha="center")

        # pass arrow down (except last)
        if i < len(predicates) - 1:
            ya = y - box_h
            ax.annotate(
                "",
                xy=(5, ya - gap + 0.05),
                xytext=(5, ya),
                arrowprops=dict(arrowstyle="->", lw=0.9, color="black"),
            )
            ax.text(4.5, ya - gap / 2, "PASS", fontsize=7, ha="center")

    # final output
    final_y = start_y - (len(predicates) - 1) * (box_h + gap) - box_h - 0.5
    ax.annotate(
        "",
        xy=(5, final_y + 0.35),
        xytext=(5, start_y - (len(predicates) - 1) * (box_h + gap) - box_h),
        arrowprops=dict(arrowstyle="->", lw=1.2, color="black"),
    )
    allow_box = FancyBboxPatch(
        (3.2, final_y - 0.1),
        3.6,
        0.5,
        boxstyle="round,pad=0.05",
        linewidth=1.5,
        edgecolor="black",
        facecolor="#e8e8e8",
    )
    ax.add_patch(allow_box)
    ax.text(5, final_y + 0.15, "ALLOW + Authorization Receipt", ha="center", va="center", fontsize=8.5, fontweight="bold")

    # note at bottom
    ax.text(5, final_y - 0.35, "Failure returns same-length noise or pseudorandom-looking audit output.", ha="center", fontsize=7, style="italic")

    # reference numerals
    ax.text(9.5, 9.4, "400", fontsize=7)
    ax.text(9.5, 7.1, "410-450", fontsize=7)
    ax.text(9.5, 0.7, "460", fontsize=7)

    save(fig, "FIG_5")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 6  —  Multi-Layer Pre-Filter Stack (cheapest-reject-first)
# ─────────────────────────────────────────────────────────────────────────────
def fig6():
    stages = [
        ("Stage 1", "Script-Origin Gate", "Coverage score: fraction of UTF-8 bytes in [0x20, 0x7E]", "O(n)", "Non-Latin script attacks"),
        ("Stage 2", "Instruction-Safety Gate", "Regex match: instruction-override, tool-abuse patterns", "O(n)", "Prompt injection, jailbreak"),
        ("Stage 3", "Petri Pattern Filter", "Adversarial intent regex corpus (173 seeds)", "O(n·p)", "Known attack signatures"),
        ("Stage 4", "Semantic SLM Routing", "Small language model: classify intent band", "O(model)", "Band assignment / NONE escape"),
        ("Stage 5", "Hyperbolic Distance Gate", "Session centroid + arcosh formula", "O(1)", "Session drift attacks"),
        ("Stage 6", "Harmonic Wall", "Nonlinear cost / safety-score threshold check", "O(1)", "Boundary adversaries"),
        ("Stage 7", "Risk Decision (L13)", "ALLOW / QUARANTINE / ESCALATE / DENY", "O(1)", "Final governance decision"),
    ]

    fig, ax = plt.subplots(figsize=(8.5, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 10.5)
    ax.axis("off")

    ax.text(6, 10.2, "FIG. 6", ha="center", fontsize=11, fontweight="bold")
    ax.text(6, 9.85, "Multi-Layer Pre-Filter Stack — Cheapest Rejection First", ha="center", fontsize=9)

    # input
    ax.text(2.5, 9.4, "Input text (intent)", ha="center", fontsize=8.5, fontweight="bold")
    ax.annotate("", xy=(2.5, 9.0), xytext=(2.5, 9.35), arrowprops=dict(arrowstyle="->", lw=1.2))

    box_h = 0.72
    gap = 0.38
    top = 8.85
    left = 0.3
    w = 7.2

    for i, (stage, name, detail, cost, catches) in enumerate(stages):
        y = top - i * (box_h + gap)
        cy = y - box_h / 2

        # main box
        shade = "#f5f5f5" if i % 2 == 0 else "white"
        rect = FancyBboxPatch((left, y - box_h), w, box_h, boxstyle="round,pad=0.04", lw=1.1, edgecolor="black", facecolor=shade)
        ax.add_patch(rect)
        ax.text(left + 0.12, cy + 0.16, f"{stage}: {name}", va="center", fontsize=8, fontweight="bold")
        ax.text(left + 0.12, cy - 0.05, detail, va="center", fontsize=6.5, color="#333333")
        ax.text(left + 0.12, cy - 0.24, f"Catches: {catches}", va="center", fontsize=6.5, color="#555555", style="italic")

        # cost badge (right side)
        badge = FancyBboxPatch((left + w + 0.12, cy - 0.22), 1.1, 0.44, boxstyle="round,pad=0.04", lw=0.8, edgecolor="black", facecolor="#dddddd")
        ax.add_patch(badge)
        ax.text(left + w + 0.67, cy, cost, ha="center", va="center", fontsize=7.5)

        # REJECT arrow →
        ax.annotate("", xy=(left + w + 1.22 + 1.5, cy), xytext=(left + w + 1.22, cy), arrowprops=dict(arrowstyle="->", lw=0.9))
        ax.text(left + w + 1.22 + 0.75, cy + 0.14, "REJECT", ha="center", fontsize=6.5, fontweight="bold")
        rej_box = FancyBboxPatch((left + w + 2.72, cy - 0.22), 1.5, 0.44, boxstyle="round,pad=0.03", lw=0.9, edgecolor="black", facecolor="#cccccc")
        ax.add_patch(rej_box)
        ax.text(left + w + 3.47, cy, "BandNot\nApplicable", ha="center", va="center", fontsize=6.2)

        # pass arrow down
        if i < len(stages) - 1:
            ax.annotate("", xy=(2.5 + left, y - box_h - gap + 0.04), xytext=(2.5 + left, y - box_h), arrowprops=dict(arrowstyle="->", lw=0.9))
            ax.text(2.5 + left - 0.5, y - box_h - gap / 2, "PASS", fontsize=7, ha="center")

    # final allow
    final_y = top - (len(stages) - 1) * (box_h + gap) - box_h - 0.5
    ax.annotate("", xy=(2.5 + left, final_y + 0.38), xytext=(2.5 + left, top - (len(stages) - 1) * (box_h + gap) - box_h), arrowprops=dict(arrowstyle="->", lw=1.2))
    allow = FancyBboxPatch((left + 0.5, final_y - 0.1), 6.2, 0.5, boxstyle="round,pad=0.05", lw=1.5, edgecolor="black", facecolor="#e8e8e8")
    ax.add_patch(allow)
    ax.text(left + 3.6, final_y + 0.15, "Route to execution handler", ha="center", va="center", fontsize=8.5, fontweight="bold")

    ax.text(0.1, 0.1, "Stages 1–3: deterministic, no ML model invoked", fontsize=6.5, style="italic")

    save(fig, "FIG_6")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 7  —  Runtime Decision Gate  (ALLOW / QUARANTINE / ESCALATE / DENY)
# ─────────────────────────────────────────────────────────────────────────────
def fig7():
    fig, ax = plt.subplots(figsize=(8, 9))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 11)
    ax.axis("off")

    ax.text(5, 10.6, "FIG. 7", ha="center", fontsize=11, fontweight="bold")
    ax.text(5, 10.25, "Runtime Decision Gate — Score-to-Decision Mapping", ha="center", fontsize=9)

    # ── inputs box ──────────────────────────────────────────────────────────
    inp = FancyBboxPatch((2.8, 9.1), 4.4, 0.7, boxstyle="round,pad=0.06", lw=1.2, edgecolor="black", facecolor="#e8e8e8")
    ax.add_patch(inp)
    ax.text(5, 9.45, "Governance Inputs", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(5, 9.15, "H(d,R) score  |  bijective tamper  |  spectral coherence  |  SLM band", ha="center", va="center", fontsize=7)

    ax.annotate("", xy=(5, 8.9), xytext=(5, 9.1), arrowprops=dict(arrowstyle="->", lw=1.3))

    # ── central gate box ────────────────────────────────────────────────────
    gate = FancyBboxPatch((3.0, 8.1), 4.0, 0.7, boxstyle="round,pad=0.06", lw=1.5, edgecolor="black", facecolor="#f0f0f0")
    ax.add_patch(gate)
    ax.text(5, 8.55, "Composite Threshold Evaluation", ha="center", va="center", fontsize=8.5, fontweight="bold")
    ax.text(5, 8.25, "Immune/reflex fast-path checked first", ha="center", va="center", fontsize=7, color="#444444")

    # ── 4 outcome branches ───────────────────────────────────────────────────
    outcomes = [
        (1.0,  6.5, "ALLOW",      "H ≥ θ_allow\nNo tamper / low drift\nCentroid updated", "#e0ffe0"),
        (3.6,  6.5, "QUARANTINE", "θ_quarantine ≤ H < θ_allow\nStructural tamper OR\nhigh session drift", "#fff8cc"),
        (6.2,  6.5, "ESCALATE",   "θ_escalate ≤ H < θ_quarantine\nMulti-signal conflict\nSwarm review required", "#ffe8cc"),
        (8.8,  6.5, "DENY",       "H < θ_deny  OR\nSyntax tamper  OR\nImmune memory hit\nFail-to-noise response", "#ffe0e0"),
    ]

    # arrows from gate to outcomes
    x_sources = [1.5, 4.0, 6.5, 9.3]
    for (xo, yo, label, desc, color), xs in zip(outcomes, x_sources):
        ax.annotate("", xy=(xo + 1.05, yo + 0.95), xytext=(xs - 0.15, 8.1),
                    arrowprops=dict(arrowstyle="->", lw=0.9, color="black",
                                   connectionstyle="arc3,rad=0.0"))

    for xo, yo, label, desc, color in outcomes:
        w, h = 2.1, 1.55
        box = FancyBboxPatch((xo, yo), w, h, boxstyle="round,pad=0.06", lw=1.3, edgecolor="black", facecolor=color)
        ax.add_patch(box)
        ax.text(xo + w / 2, yo + h - 0.22, label, ha="center", va="center", fontsize=9, fontweight="bold")
        for j, line in enumerate(desc.split("\n")):
            ax.text(xo + w / 2, yo + h - 0.55 - j * 0.28, line, ha="center", va="center", fontsize=6.5)

    # ── downstream effects ───────────────────────────────────────────────────
    effects = [
        (1.0,  4.2, 2.1, "Centroid updated\nPQC receipt issued\nAction executed", "#f0fff0"),
        (3.6,  4.2, 2.1, "Quarantine lock applied\nTool / resource restriction\nAudit trail written", "#fffbdd"),
        (6.2,  4.2, 2.1, "Swarm quorum triggered\nGovernance review queue\nAction suspended", "#fff3e0"),
        (8.8,  4.2, 2.1, "SHA-256 fail-to-noise\nSame-length audit\nnoise output", "#fff0f0"),
    ]
    for xo, yo, w, desc, color in effects:
        ax.annotate("", xy=(xo + w / 2, yo + 0.75), xytext=(xo + w / 2, 6.5),
                    arrowprops=dict(arrowstyle="->", lw=0.8))
        box = FancyBboxPatch((xo, yo), w, 0.9, boxstyle="round,pad=0.05", lw=0.9, edgecolor="#888888", facecolor=color)
        ax.add_patch(box)
        for j, line in enumerate(desc.split("\n")):
            ax.text(xo + w / 2, yo + 0.73 - j * 0.24, line, ha="center", va="center", fontsize=6.2)

    # ── threshold legend ─────────────────────────────────────────────────────
    ax.text(5, 3.1, "Score thresholds (configurable, defaults shown):", ha="center", fontsize=7.5, style="italic")
    ax.text(5, 2.8, "θ_allow ≥ 0.70   θ_quarantine = 0.40   θ_escalate = 0.20   θ_deny < 0.20", ha="center", fontsize=7.5)
    ax.text(5, 2.5, "Immune memory hit → immediate DENY regardless of score", ha="center", fontsize=7, color="#555555")
    ax.text(5, 2.2, "Reflex memory hit → immediate ALLOW regardless of score", ha="center", fontsize=7, color="#555555")

    # ref numerals
    ax.text(9.7, 9.3, "700", fontsize=7)
    ax.text(9.7, 8.3, "710", fontsize=7)
    ax.text(9.7, 7.0, "720–750", fontsize=7)

    save(fig, "FIG_7")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 8  —  Bijective Tamper Detection Flow
# ─────────────────────────────────────────────────────────────────────────────
def fig8():
    fig, ax = plt.subplots(figsize=(7.5, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.3, 11.5)
    ax.axis("off")

    ax.text(5, 11.1, "FIG. 8", ha="center", fontsize=11, fontweight="bold")
    ax.text(5, 10.75, "Bijective Tamper Detection — Tokenize-Decode Round-Trip Invariant", ha="center", fontsize=8.5)
    ax.text(5, 10.4, "parse(decode(encode(src))) ≡ parse(src)  when input is legitimate", ha="center", fontsize=8, style="italic")

    steps = [
        (9.5, "Input source text (src)", "#e8e8e8"),
        (8.5, "Step 1: AST Canonicalization\nast.dump(ast.parse(src))  →  canonical_ast\nsha256(canonical_ast)  →  semantic_fingerprint", "#f5f5f5"),
        (7.0, "Step 2: Tokenize → Decode Round Trip\ntokenizer.encode(src)  →  token_ids\ntokenizer.decode(token_ids)  →  decoded", "#f5f5f5"),
        (5.5, "Step 3: Byte Comparison\ndecoded == src ?", "#eeeeee"),
    ]

    for y, text, color in steps:
        lines = text.split("\n")
        h = 0.35 + len(lines) * 0.3
        box = FancyBboxPatch((1.0, y - h), 8.0, h, boxstyle="round,pad=0.06", lw=1.1, edgecolor="black", facecolor=color)
        ax.add_patch(box)
        for j, line in enumerate(lines):
            ax.text(5, y - 0.18 - j * 0.28, line, ha="center", va="center",
                    fontsize=8 if j == 0 else 7,
                    fontweight="bold" if j == 0 else "normal")
        if y > 5.5:
            ax.annotate("", xy=(5, y - h - 0.08), xytext=(5, y - h),
                        arrowprops=dict(arrowstyle="->", lw=1.0))

    # ── branch from "bytes equal?" ────────────────────────────────────────────
    ax.annotate("", xy=(5, 4.9), xytext=(5, 5.1), arrowprops=dict(arrowstyle="->", lw=1.0))

    # YES branch (left)
    ax.annotate("", xy=(2.2, 4.5), xytext=(4.5, 4.9), arrowprops=dict(arrowstyle="->", lw=0.9, connectionstyle="arc3,rad=0.1"))
    ax.text(2.8, 4.85, "YES (equal)", fontsize=7.5)
    clean = FancyBboxPatch((0.5, 3.7), 3.5, 0.7, boxstyle="round,pad=0.05", lw=1.2, edgecolor="black", facecolor="#e0ffe0")
    ax.add_patch(clean)
    ax.text(2.25, 4.1, "kind = \"none\"\nscore = 0.0\nfingerprint attached", ha="center", va="center", fontsize=7)

    # NO branch (right)
    ax.annotate("", xy=(7.8, 4.5), xytext=(5.5, 4.9), arrowprops=dict(arrowstyle="->", lw=0.9, connectionstyle="arc3,rad=-0.1"))
    ax.text(6.4, 4.85, "NO (diverge)", fontsize=7.5)

    # sub-branches for divergence
    sub = [
        (6.5, 3.7, "NFC recovers?", "#f5f5f5"),
    ]
    ax.annotate("", xy=(7.8, 4.2), xytext=(7.8, 4.5), arrowprops=dict(arrowstyle="->", lw=0.9))
    nfc_box = FancyBboxPatch((6.0, 3.4), 3.6, 0.7, boxstyle="round,pad=0.05", lw=1.1, edgecolor="black", facecolor="#f5f5f5")
    ax.add_patch(nfc_box)
    ax.text(7.8, 3.85, "NFC normalize(src)==decoded?", ha="center", va="center", fontsize=7.5)

    # NFC YES
    ax.annotate("", xy=(6.2, 2.9), xytext=(6.8, 3.4), arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(5.9, 3.25, "YES", fontsize=7)
    nfc_yes = FancyBboxPatch((4.6, 2.2), 3.2, 0.65, boxstyle="round,pad=0.04", lw=1.0, edgecolor="black", facecolor="#fffacc")
    ax.add_patch(nfc_yes)
    ax.text(6.2, 2.56, "kind = \"nfc\"\nscore = 0.20–0.25\nALLOW (log only)", ha="center", va="center", fontsize=6.8)

    # NFC NO → AST diverge?
    ax.annotate("", xy=(8.8, 2.9), xytext=(8.8, 3.4), arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(8.9, 3.25, "NO", fontsize=7)
    ast_box = FancyBboxPatch((7.5, 2.2), 2.8, 0.65, boxstyle="round,pad=0.04", lw=1.0, edgecolor="black", facecolor="#f5f5f5")
    ax.add_patch(ast_box)
    ax.text(8.9, 2.56, "AST diverges?", ha="center", va="center", fontsize=7.5)

    # AST YES
    ax.annotate("", xy=(8.2, 1.6), xytext=(8.5, 2.2), arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(7.7, 2.05, "YES", fontsize=7)
    struct_box = FancyBboxPatch((6.2, 0.9), 2.8, 0.65, boxstyle="round,pad=0.04", lw=1.2, edgecolor="black", facecolor="#ffe8cc")
    ax.add_patch(struct_box)
    ax.text(7.6, 1.24, "kind = \"structural\"\nscore = 0.60\nQUARANTINE", ha="center", va="center", fontsize=6.8)

    # AST NO (decoded doesn't parse)
    ax.annotate("", xy=(9.4, 1.6), xytext=(9.3, 2.2), arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(9.4, 2.05, "NO / no parse", fontsize=6.5)
    syntax_box = FancyBboxPatch((8.2, 0.9), 2.8, 0.65, boxstyle="round,pad=0.04", lw=1.2, edgecolor="black", facecolor="#ffe0e0")
    ax.add_patch(syntax_box)
    ax.text(9.6, 1.24, "kind = \"syntax\"\nscore = 1.00\nDENY", ha="center", va="center", fontsize=6.8)

    # note
    ax.text(5, 0.25, "Fingerprint = SHA-256(canonical AST).  Two semantically-equal programs always produce the same fingerprint.", ha="center", fontsize=6.5, style="italic")

    # ref numerals
    ax.text(9.7, 10.0, "800", fontsize=7)
    ax.text(9.7, 8.0, "810", fontsize=7)
    ax.text(9.7, 6.0, "820", fontsize=7)

    save(fig, "FIG_8")


# ─────────────────────────────────────────────────────────────────────────────
# FIG. 9  —  System Deployment Architecture
# ─────────────────────────────────────────────────────────────────────────────
def fig9():
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.5, 10)
    ax.axis("off")

    ax.text(6, 9.65, "FIG. 9", ha="center", fontsize=11, fontweight="bold")
    ax.text(6, 9.3, "System Deployment Architecture — Runtime Governance Service", ha="center", fontsize=9)

    def box(x, y, w, h, label, sublabel="", color="#f0f0f0", lw=1.0):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.07", lw=lw, edgecolor="black", facecolor=color)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2 + (0.12 if sublabel else 0), label, ha="center", va="center",
                fontsize=8, fontweight="bold")
        if sublabel:
            ax.text(x + w / 2, y + h / 2 - 0.2, sublabel, ha="center", va="center", fontsize=6.5, color="#444444")

    def arr(x1, y1, x2, y2, label="", rad=0.0):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.0, color="black",
                                   connectionstyle=f"arc3,rad={rad}"))
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my + 0.15, label, ha="center", fontsize=6.5)

    # ── entry points (top row) ────────────────────────────────────────────────
    box(0.3,  7.8, 2.2, 0.85, "REST API", "FastAPI / uvicorn\nport 8000", "#e8e8e8")
    box(3.0,  7.8, 2.2, 0.85, "Agent Bus", "npm: scbe-agent-bus\nMCP + WebSocket", "#e8e8e8")
    box(5.7,  7.8, 2.2, 0.85, "CLI", "scbe govern\nstdin/stdout", "#e8e8e8")
    box(8.4,  7.8, 2.2, 0.85, "Programmatic\nSDK", "Python + TypeScript\nclient libraries", "#e8e8e8")

    # ── central runtime gate ───────────────────────────────────────────────────
    box(3.2,  5.9, 5.6, 1.3, "Runtime Governance Gate", "14-layer pipeline  |  session state  |  immune/reflex cache", "#e0e8ff", lw=1.8)

    # arrows entry → gate
    for xc in [1.4, 4.1, 6.8, 9.5]:
        arr(xc, 7.8, 5.0, 7.2)

    # ── sub-components (middle row) ───────────────────────────────────────────
    box(0.3,  4.1, 2.5, 1.3, "Session State\nStore", "centroid  |  immune\nreflex  |  count", "#f5f5f5")
    box(3.2,  4.1, 2.5, 1.3, "Bijective\nTamper Gate", "tokenize-decode\nround-trip check", "#fffadd")
    box(6.0,  4.1, 2.5, 1.3, "Pre-Filter\nStack", "script-origin\ninstr-safety  |  SLM", "#f5f5f5")
    box(8.8,  4.1, 2.5, 1.3, "PQC Envelope\nGenerator", "ML-DSA-65 sign\nML-KEM-768 wrap", "#f5f5f5")

    # arrows gate → sub-components
    arr(4.0, 5.9, 1.55, 5.4)
    arr(4.8, 5.9, 4.45, 5.4)
    arr(5.2, 5.9, 7.25, 5.4)
    arr(6.0, 5.9, 10.05, 5.4)

    # ── outputs (bottom row) ──────────────────────────────────────────────────
    box(0.3,  2.2, 2.5, 1.1, "Quarantine Lock", "resource restrict\ntool block  |  timeout", "#fff8cc")
    box(3.2,  2.2, 2.5, 1.1, "Governance\nDecision", "ALLOW / QUARANTINE\nESCALATE / DENY", "#e0ffe0")
    box(6.0,  2.2, 2.5, 1.1, "Audit Receipt", "score  |  signals\ntimestamp  |  sig", "#f5f5f5")
    box(8.8,  2.2, 2.5, 1.1, "Fail-to-Noise\nResponse", "SHA-256 chain\n≡ random bytes", "#ffe0e0")

    # arrows sub → outputs
    arr(1.55, 4.1, 1.55, 3.3)
    arr(4.45, 4.1, 4.45, 3.3)
    arr(7.25, 4.1, 7.25, 3.3)
    arr(10.05, 4.1, 10.05, 3.3)

    # ── persistent storage (bottom) ───────────────────────────────────────────
    box(4.2,  0.4, 3.6, 0.9, "Durable State (JSON)", "autosave every N decisions  |  rollback on corruption", "#f0f0f0")
    arr(5.5, 2.2, 5.5, 1.3)
    arr(5.5, 1.3, 6.0, 1.3, rad=0.0)

    # ── labels / ref numerals ─────────────────────────────────────────────────
    ax.text(0.1, 9.0, "Client Layer", fontsize=7, color="#666666")
    ax.text(0.1, 6.5, "Core Layer", fontsize=7, color="#666666")
    ax.text(0.1, 4.8, "Signal Layer", fontsize=7, color="#666666")
    ax.text(0.1, 2.9, "Output Layer", fontsize=7, color="#666666")

    ax.text(11.5, 8.2, "900", fontsize=7)
    ax.text(11.5, 6.5, "910", fontsize=7)
    ax.text(11.5, 4.8, "920–950", fontsize=7)
    ax.text(11.5, 2.8, "960–990", fontsize=7)

    save(fig, "FIG_9")


# ─────────────────────────────────────────────────────────────────────────────
# run all
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating patent figures...")
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6()
    fig7()
    fig8()
    fig9()
    print("Done. 9 figures × 2 formats = 18 files.")
