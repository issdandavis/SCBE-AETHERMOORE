#!/usr/bin/env python3
"""3D Graph Cube Visualization — Content Spin Topology.

Visualizes the content spin pipeline as a 3D graph cube where:
- Nodes = topics (positioned by hash → Poincare ball mapping)
- Edges = topic graph adjacency
- Relay chains = colored paths through the graph
- Harmonic frequencies = node oscillation amplitude
- Platform voices = color-coded layers
- 4D context vectors = size + alpha

Usage:
    python scripts/visualize_spin.py              # Static 3D snapshot
    python scripts/visualize_spin.py animate       # Animated spin evolution
    python scripts/visualize_spin.py relay          # Show relay chains only
    python scripts/visualize_spin.py ferrofluid     # Ferrofluid harmonic field

@layer Layer 5 (hyperbolic distance), Layer 14 (telemetry)
@component Visualization.SpinCube
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for file output
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from mpl_toolkits.mplot3d.art3d import Line3DCollection

# ---------------------------------------------------------------------------
#  Import spin pipeline
# ---------------------------------------------------------------------------

from scripts.content_spin import (
    ContentSpinner,
    HARMONIC_RATIOS,
    PLATFORM_VOICES,
    TONGUE_WEIGHTS,
    PHI,
)

# ---------------------------------------------------------------------------
#  Color palettes
# ---------------------------------------------------------------------------

PLATFORM_COLORS = {
    "twitter": "#1DA1F2",
    "bluesky": "#0085FF",
    "mastodon": "#6364FF",
    "linkedin": "#0A66C2",
    "medium": "#00AB6C",
    "shopify_blog": "#96BF48",
    "github": "#F0F0F0",
}

TOPIC_COLORS = {
    "ai_governance": "#FF6B6B",
    "ai_safety": "#FF8E72",
    "post_quantum": "#4ECDC4",
    "cryptography": "#45B7D1",
    "multi_agent": "#96CEB4",
    "trust_systems": "#FFEAA7",
    "hyperbolic_geometry": "#DDA0DD",
    "sacred_tongues": "#F0E68C",
    "geoseed": "#98D8C8",
    "game_dev": "#FF6F61",
    "education": "#88D8B0",
    "shopify": "#96BF48",
    "multi_agent_trust": "#96CEB4",
}

# Default for any topic not in the map
DEFAULT_COLOR = "#AAAAAA"


# ---------------------------------------------------------------------------
#  Node positioning — hash-based 3D layout inside unit cube
# ---------------------------------------------------------------------------

def topic_to_3d(topic: str, jitter: float = 0.0) -> np.ndarray:
    """Map a topic string to a 3D position inside the unit cube.

    Uses hash bytes for deterministic placement. Optional jitter
    for animation displacement.
    """
    h = hashlib.sha256(topic.encode()).digest()
    x = (h[0] + h[1] * 256) / 65535.0
    y = (h[2] + h[3] * 256) / 65535.0
    z = (h[4] + h[5] * 256) / 65535.0
    return np.array([x + jitter, y + jitter, z + jitter])


def poincare_to_3d(topic: str, radius: float = 0.9) -> np.ndarray:
    """Map topic to Poincare ball position (constrained inside sphere)."""
    pos = topic_to_3d(topic)
    # Center at origin, scale to Poincare ball
    pos = (pos - 0.5) * 2.0 * radius
    # Clamp inside ball
    norm = np.linalg.norm(pos)
    if norm > radius:
        pos = pos * (radius / norm)
    return pos


# ---------------------------------------------------------------------------
#  Build graph data
# ---------------------------------------------------------------------------

def build_graph_data(spinner: ContentSpinner) -> dict:
    """Extract nodes and edges from the topic graph."""
    graph = spinner.graph.topic_graph
    nodes = {}
    edges = []

    for topic in graph:
        pos = poincare_to_3d(topic)
        color = TOPIC_COLORS.get(topic, DEFAULT_COLOR)
        nodes[topic] = {"pos": pos, "color": color}

    for topic, adjacents in graph.items():
        for adj in adjacents:
            if adj in graph:  # Only draw edges to nodes that exist
                edges.append((topic, adj))

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
#  Static 3D snapshot
# ---------------------------------------------------------------------------

def plot_static(spinner: ContentSpinner):
    """Render static 3D graph cube of the topic graph."""
    data = build_graph_data(spinner)
    nodes = data["nodes"]
    edges = data["edges"]

    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a1a")
    fig.patch.set_facecolor("#0a0a1a")

    # Draw edges (adjacency lines)
    for t1, t2 in edges:
        if t1 in nodes and t2 in nodes:
            p1 = nodes[t1]["pos"]
            p2 = nodes[t2]["pos"]
            ax.plot(
                [p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                color="#333355", linewidth=0.4, alpha=0.3,
            )

    # Draw nodes
    for topic, info in nodes.items():
        p = info["pos"]
        # Size by number of connections
        n_conn = len(spinner.graph.get_adjacents(topic))
        size = 60 + n_conn * 25

        ax.scatter(
            p[0], p[1], p[2],
            c=info["color"], s=size, alpha=0.85,
            edgecolors="white", linewidth=0.8, zorder=5,
            depthshade=True,
        )

        # Label
        ax.text(
            p[0], p[1], p[2] + 0.08,
            topic.replace("_", "\n"),
            fontsize=6, color="white", ha="center", va="bottom",
            fontweight="bold", alpha=0.9,
        )

    # Draw Poincare ball wireframe (unit sphere)
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 20)
    r = 0.9
    x = r * np.outer(np.cos(u), np.sin(v))
    y = r * np.outer(np.sin(u), np.sin(v))
    z = r * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_wireframe(x, y, z, color="#222244", linewidth=0.2, alpha=0.1)

    ax.set_xlim([-1, 1])
    ax.set_ylim([-1, 1])
    ax.set_zlim([-1, 1])
    ax.set_xlabel("X", color="white", fontsize=10)
    ax.set_ylabel("Y", color="white", fontsize=10)
    ax.set_zlabel("Z", color="white", fontsize=10)
    ax.tick_params(colors="white", labelsize=7)

    ax.set_title(
        "Content Spin Topology — Poincare Ball\n"
        f"{len(nodes)} topics, {len(edges)} connections",
        color="white", fontsize=14, fontweight="bold", pad=20,
    )

    plt.tight_layout()
    # Save to artifacts
    out_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "visualizations")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "spin_topology_static.png")
    plt.savefig(out_path, dpi=150, facecolor="#0a0a1a", bbox_inches="tight")
    print(f"Saved: {out_path}")
    plt.show()


# ---------------------------------------------------------------------------
#  Relay chain visualization
# ---------------------------------------------------------------------------

def plot_relay_chains(spinner: ContentSpinner, topic: str = "ai_governance", depth: int = 3):
    """Visualize Fibonacci relay chains as colored 3D paths."""
    data = build_graph_data(spinner)
    nodes = data["nodes"]
    edges = data["edges"]

    # Generate relay chains
    chains = spinner.graph.fibonacci_relay(topic, depth=depth, branch_factor=3)

    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a1a")
    fig.patch.set_facecolor("#0a0a1a")

    # Draw dim edges
    for t1, t2 in edges:
        if t1 in nodes and t2 in nodes:
            p1 = nodes[t1]["pos"]
            p2 = nodes[t2]["pos"]
            ax.plot(
                [p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                color="#222244", linewidth=0.3, alpha=0.15,
            )

    # Draw dim nodes
    for t, info in nodes.items():
        p = info["pos"]
        ax.scatter(p[0], p[1], p[2], c="#444466", s=30, alpha=0.3)

    # Draw relay chains with vivid colors
    chain_colors = plt.cm.plasma(np.linspace(0.1, 0.9, max(len(chains), 1)))

    for i, chain in enumerate(chains):
        color = chain_colors[i]
        looped = chain[-1] == chain[0] and len(chain) > 1

        # Draw chain path
        positions = []
        for t in chain:
            if t in nodes:
                positions.append(nodes[t]["pos"])
            else:
                positions.append(poincare_to_3d(t))

        if len(positions) >= 2:
            positions = np.array(positions)
            ax.plot(
                positions[:, 0], positions[:, 1], positions[:, 2],
                color=color, linewidth=2.5, alpha=0.85,
                marker="o", markersize=8,
            )

            # Glow effect (wider, dimmer line underneath)
            ax.plot(
                positions[:, 0], positions[:, 1], positions[:, 2],
                color=color, linewidth=6, alpha=0.15,
            )

        # Label start node
        if positions is not None and len(positions) > 0:
            start_pos = positions[0]
            label = f"Chain {i+1}"
            if looped:
                label += " [LOOP]"
            ax.text(
                start_pos[0] + 0.05, start_pos[1], start_pos[2] + 0.05,
                label, fontsize=7, color=color, alpha=0.9,
            )

    # Highlight origin node
    if topic in nodes:
        origin = nodes[topic]["pos"]
        ax.scatter(
            origin[0], origin[1], origin[2],
            c="#FF4444", s=300, alpha=0.9, marker="*",
            edgecolors="white", linewidth=1.5, zorder=10,
        )
        ax.text(
            origin[0], origin[1], origin[2] + 0.12,
            topic.replace("_", " ").upper(),
            fontsize=10, color="#FF6666", ha="center",
            fontweight="bold",
        )

    ax.set_xlim([-1, 1])
    ax.set_ylim([-1, 1])
    ax.set_zlim([-1, 1])
    ax.set_xlabel("X", color="white", fontsize=10)
    ax.set_ylabel("Y", color="white", fontsize=10)
    ax.set_zlabel("Z", color="white", fontsize=10)
    ax.tick_params(colors="white", labelsize=7)

    ax.set_title(
        f"Fibonacci Relay Chains — {topic}\n"
        f"{len(chains)} chains, depth={depth}",
        color="white", fontsize=14, fontweight="bold", pad=20,
    )

    plt.tight_layout()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "visualizations")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"relay_chains_{topic}.png")
    plt.savefig(out_path, dpi=150, facecolor="#0a0a1a", bbox_inches="tight")
    print(f"Saved: {out_path}")
    plt.show()


# ---------------------------------------------------------------------------
#  Animated spin evolution (ferrofluid harmonic field)
# ---------------------------------------------------------------------------

def plot_animated(spinner: ContentSpinner, frames: int = 200):
    """Animate the content spin as a ferrofluid harmonic field.

    Nodes oscillate at their harmonic frequency.
    Edges pulse with communication strength.
    Platform colors cycle through the spectrum.
    """
    data = build_graph_data(spinner)
    nodes = data["nodes"]
    edges = data["edges"]

    topic_list = list(nodes.keys())
    n_topics = len(topic_list)

    # Assign harmonic frequencies (from ferrofluid core ratios)
    harmonic_values = list(HARMONIC_RATIOS.values())
    topic_harmonics = {}
    for i, topic in enumerate(topic_list):
        topic_harmonics[topic] = harmonic_values[i % len(harmonic_values)]

    # Base positions
    base_positions = np.array([nodes[t]["pos"] for t in topic_list])

    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a1a")
    fig.patch.set_facecolor("#0a0a1a")

    # Pre-draw wireframe sphere
    u = np.linspace(0, 2 * np.pi, 20)
    v = np.linspace(0, np.pi, 15)
    r = 0.9
    sx = r * np.outer(np.cos(u), np.sin(v))
    sy = r * np.outer(np.sin(u), np.sin(v))
    sz = r * np.outer(np.ones_like(u), np.cos(v))

    def update(frame):
        ax.clear()
        ax.set_facecolor("#0a0a1a")

        t = frame * 0.05  # Time parameter

        # Poincare ball wireframe
        ax.plot_wireframe(sx, sy, sz, color="#181833", linewidth=0.15, alpha=0.08)

        # Calculate oscillated positions
        positions = np.copy(base_positions)
        for i, topic in enumerate(topic_list):
            freq = topic_harmonics[topic]
            # Oscillate in all 3 axes with different phase offsets
            positions[i, 0] += 0.04 * math.sin(t * freq * 2 * math.pi)
            positions[i, 1] += 0.04 * math.cos(t * freq * 2 * math.pi + math.pi / 3)
            positions[i, 2] += 0.04 * math.sin(t * freq * 2 * math.pi + 2 * math.pi / 3)

            # Clamp inside ball
            norm = np.linalg.norm(positions[i])
            if norm > 0.88:
                positions[i] *= 0.88 / norm

        # Draw edges with pulsing alpha
        for t1, t2 in edges:
            if t1 in nodes and t2 in nodes:
                i1 = topic_list.index(t1)
                i2 = topic_list.index(t2)
                p1 = positions[i1]
                p2 = positions[i2]

                # Communication strength = harmonic resonance
                freq_ratio = topic_harmonics[t1] / topic_harmonics[t2]
                resonance = 1.0 / (1.0 + abs(freq_ratio - round(freq_ratio)))
                pulse = 0.15 + 0.35 * resonance * abs(math.sin(t * 2))

                ax.plot(
                    [p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                    color="#4466AA", linewidth=0.5 + resonance, alpha=pulse,
                )

        # Draw nodes with oscillating size
        for i, topic in enumerate(topic_list):
            p = positions[i]
            freq = topic_harmonics[topic]
            color = TOPIC_COLORS.get(topic, DEFAULT_COLOR)

            # Size oscillates with harmonic
            size_pulse = 60 + 30 * abs(math.sin(t * freq * math.pi))
            alpha = 0.7 + 0.3 * abs(math.cos(t * freq * math.pi))

            ax.scatter(
                p[0], p[1], p[2],
                c=color, s=size_pulse, alpha=alpha,
                edgecolors="white", linewidth=0.5, zorder=5,
            )

            # Labels for larger nodes only
            n_conn = len(spinner.graph.get_adjacents(topic))
            if n_conn >= 4:
                ax.text(
                    p[0], p[1], p[2] + 0.08,
                    topic.replace("_", " "),
                    fontsize=6, color="white", ha="center",
                    alpha=0.8, fontweight="bold",
                )

        # Status text
        coherence = np.mean([
            1.0 / (1.0 + abs(topic_harmonics[t1] / topic_harmonics[t2] -
                              round(topic_harmonics[t1] / topic_harmonics[t2])))
            for t1, t2 in edges[:20] if t1 in topic_harmonics and t2 in topic_harmonics
        ]) if edges else 0

        ax.set_xlim([-1, 1])
        ax.set_ylim([-1, 1])
        ax.set_zlim([-1, 1])
        ax.set_xlabel("X", color="white", fontsize=9)
        ax.set_ylabel("Y", color="white", fontsize=9)
        ax.set_zlabel("Z", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=6)

        ax.set_title(
            f"Ferrofluid Content Spin — Harmonic Field\n"
            f"t={t:.2f}s | {n_topics} nodes | coherence={coherence:.3f}",
            color="white", fontsize=13, fontweight="bold", pad=15,
        )

        # Slowly rotate view
        ax.view_init(elev=25 + 5 * math.sin(t * 0.3), azim=frame * 0.8)

    anim = FuncAnimation(fig, update, frames=frames, interval=50, blit=False)

    # Save as GIF
    out_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "visualizations")
    os.makedirs(out_dir, exist_ok=True)
    gif_path = os.path.join(out_dir, "ferrofluid_spin.gif")

    try:
        anim.save(gif_path, writer="pillow", fps=20, dpi=100)
        print(f"Saved animation: {gif_path}")
    except Exception as e:
        print(f"Could not save GIF ({e}). Showing live animation...")

    plt.show()


# ---------------------------------------------------------------------------
#  Platform harmonic spectrum
# ---------------------------------------------------------------------------

def plot_harmonic_spectrum():
    """Visualize platform harmonic frequencies as a 3D spectrum."""
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0a0a1a")
    fig.patch.set_facecolor("#0a0a1a")

    platforms = list(PLATFORM_VOICES.keys())
    n = len(platforms)
    t = np.linspace(0, 4 * np.pi, 200)

    for i, platform in enumerate(platforms):
        voice = PLATFORM_VOICES[platform]
        harmonic_name = voice.get("harmonic", "unison")
        freq = HARMONIC_RATIOS.get(harmonic_name, 1.0)
        color = PLATFORM_COLORS.get(platform, "#AAAAAA")

        # Each platform is a wave at its harmonic frequency
        x = t
        y = np.full_like(t, i * 0.4)  # Offset per platform
        z = 0.15 * np.sin(t * freq)

        ax.plot(x, y, z, color=color, linewidth=2, alpha=0.85, label=f"{platform} ({harmonic_name})")

        # Node at peak
        peak_idx = np.argmax(z)
        ax.scatter(x[peak_idx], y[peak_idx], z[peak_idx],
                   c=color, s=100, edgecolors="white", linewidth=1, zorder=5)

    # Sacred Tongue weights as vertical bars
    tongue_names = list(TONGUE_WEIGHTS.keys())
    for i, (tongue, weight) in enumerate(TONGUE_WEIGHTS.items()):
        bar_x = 2 * np.pi + i * 0.3
        bar_y = -0.5
        ax.bar3d(bar_x, bar_y, 0, 0.2, 0.2, weight * 0.02,
                 color=plt.cm.inferno(weight / 12), alpha=0.7)
        ax.text(bar_x + 0.1, bar_y, weight * 0.02 + 0.02,
                tongue, fontsize=8, color="white", ha="center")

    ax.set_xlabel("Phase", color="white", fontsize=10)
    ax.set_ylabel("Platform", color="white", fontsize=10)
    ax.set_zlabel("Amplitude", color="white", fontsize=10)
    ax.tick_params(colors="white", labelsize=7)

    ax.set_title(
        "Platform Harmonic Spectrum + Sacred Tongue Weights\n"
        "Wave patterns for inter-communication frequency",
        color="white", fontsize=13, fontweight="bold", pad=20,
    )

    ax.legend(loc="upper left", fontsize=8, facecolor="#1a1a2e", labelcolor="white",
              edgecolor="#333355")

    plt.tight_layout()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "visualizations")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "harmonic_spectrum.png")
    plt.savefig(out_path, dpi=150, facecolor="#0a0a1a", bbox_inches="tight")
    print(f"Saved: {out_path}")
    plt.show()


# ---------------------------------------------------------------------------
#  Anti-magnetic shielding visualization
# ---------------------------------------------------------------------------

def plot_antimagnetic_shield(spinner: ContentSpinner):
    """Visualize anti-magnetic field lines that counteract external interference.

    In space, external magnetic fields (solar wind, planetary magnetospheres,
    cosmic rays) can disrupt ferrofluid agent communication. The shield
    generates opposing field lines that cancel external flux.

    Physics model:
    - External field B_ext = uniform + dipole noise
    - Shield field B_shield = -B_ext (active cancellation)
    - Net field B_net = B_ext + B_shield ≈ 0 inside the shielded volume
    - Residual at edges = harmonic cost H(d,R) = R^(d^2)

    The shield is a Faraday cage equivalent using counter-rotating
    magnetic flux loops. Visualized as opposing field line pairs.
    """
    data = build_graph_data(spinner)
    nodes = data["nodes"]

    fig = plt.figure(figsize=(18, 14))
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#050510")
    fig.patch.set_facecolor("#050510")

    # Shield radius (Poincare ball boundary)
    R_shield = 0.92

    # --- External magnetic field lines (threats from space) ---
    # Solar wind: uniform field in +X direction with noise
    n_ext_lines = 12
    for i in range(n_ext_lines):
        y_start = -1.3 + (i / n_ext_lines) * 2.6
        z_start = -1.3 + ((i * 7) % n_ext_lines) / n_ext_lines * 2.6

        t_param = np.linspace(-1.5, 1.5, 100)
        x_line = t_param
        y_line = np.full_like(t_param, y_start) + 0.05 * np.sin(t_param * 3)
        z_line = np.full_like(t_param, z_start) + 0.05 * np.cos(t_param * 2)

        # Check which parts are inside the shield
        r_dist = np.sqrt(x_line**2 + y_line**2 + z_line**2)
        inside = r_dist < R_shield

        # External lines are red (threats)
        outside_mask = ~inside
        ax.plot(
            x_line[outside_mask], y_line[outside_mask], z_line[outside_mask],
            color="#FF2222", linewidth=0.8, alpha=0.4,
        )

        # Where lines meet the shield, they get deflected (bent away)
        # This represents active cancellation
        shield_boundary = np.where(np.diff(inside.astype(int)) != 0)[0]
        for sb in shield_boundary:
            if sb < len(t_param) - 1:
                bx, by, bz = x_line[sb], y_line[sb], z_line[sb]
                ax.scatter(bx, by, bz, c="#FF4444", s=15, alpha=0.6, marker="x")

    # --- Anti-magnetic shield lines (our defense) ---
    # Counter-rotating flux loops around the Poincare ball
    n_shield_lines = 8
    for i in range(n_shield_lines):
        theta_offset = i * 2 * np.pi / n_shield_lines
        phi_offset = i * np.pi / n_shield_lines

        t_param = np.linspace(0, 2 * np.pi, 150)

        # Toroidal loops around the sphere
        major_r = R_shield
        minor_r = 0.12 + 0.04 * math.sin(phi_offset)

        x_loop = (major_r + minor_r * np.cos(t_param)) * np.cos(t_param / 2 + theta_offset)
        y_loop = (major_r + minor_r * np.cos(t_param)) * np.sin(t_param / 2 + theta_offset)
        z_loop = minor_r * np.sin(t_param) * np.cos(phi_offset)

        # Shield lines are cyan/blue (protection)
        ax.plot(
            x_loop, y_loop, z_loop,
            color="#00CCFF", linewidth=1.2, alpha=0.35,
        )

        # Counter-rotating pair (opposite direction)
        x_counter = (major_r + minor_r * np.cos(-t_param)) * np.cos(-t_param / 2 + theta_offset + np.pi)
        y_counter = (major_r + minor_r * np.cos(-t_param)) * np.sin(-t_param / 2 + theta_offset + np.pi)
        z_counter = minor_r * np.sin(-t_param) * np.cos(phi_offset + np.pi / 4)

        ax.plot(
            x_counter, y_counter, z_counter,
            color="#0066FF", linewidth=1.0, alpha=0.25,
        )

    # --- Shielded volume (Poincare ball) ---
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 20)
    sx = R_shield * np.outer(np.cos(u), np.sin(v))
    sy = R_shield * np.outer(np.sin(u), np.sin(v))
    sz = R_shield * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_wireframe(sx, sy, sz, color="#00AAFF", linewidth=0.2, alpha=0.08)

    # --- Interior nodes (protected agents) ---
    for topic, info in nodes.items():
        p = info["pos"]
        n_conn = len(spinner.graph.get_adjacents(topic))
        size = 40 + n_conn * 20

        ax.scatter(
            p[0], p[1], p[2],
            c=info["color"], s=size, alpha=0.85,
            edgecolors="#00CCFF", linewidth=0.6, zorder=5,
        )

    # --- Interior communication lines (safe, inside shield) ---
    edges = data["edges"]
    for t1, t2 in edges:
        if t1 in nodes and t2 in nodes:
            p1 = nodes[t1]["pos"]
            p2 = nodes[t2]["pos"]
            ax.plot(
                [p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                color="#00FF88", linewidth=0.4, alpha=0.15,
            )

    # --- Harmonic cost at shield boundary ---
    # Show H(d,R) = R^(d^2) as color gradient on the sphere
    # Higher cost near the edge (redder)
    n_boundary_points = 50
    for _ in range(n_boundary_points):
        theta = np.random.uniform(0, 2 * np.pi)
        phi = np.random.uniform(0, np.pi)
        r_point = R_shield * (0.95 + 0.05 * np.random.random())

        bx = r_point * np.sin(phi) * np.cos(theta)
        by = r_point * np.sin(phi) * np.sin(theta)
        bz = r_point * np.cos(phi)

        # Harmonic cost: distance from center
        d = np.sqrt(bx**2 + by**2 + bz**2) / R_shield
        cost = R_shield ** (d**2)
        color_val = min(1.0, cost / 3.0)

        ax.scatter(
            bx, by, bz,
            c=plt.cm.hot(color_val), s=5, alpha=0.3,
        )

    # --- Dipole field vectors (external interference arrows) ---
    n_arrows = 6
    for i in range(n_arrows):
        angle = i * 2 * np.pi / n_arrows
        ax_start = 1.3 * np.cos(angle)
        ay_start = 1.3 * np.sin(angle)
        az_start = 0.5 * np.sin(angle * 2)

        # Arrow pointing inward (threat)
        ax.quiver(
            ax_start, ay_start, az_start,
            -ax_start * 0.3, -ay_start * 0.3, -az_start * 0.3,
            color="#FF3333", alpha=0.5, arrow_length_ratio=0.3, linewidth=1.5,
        )

        # Counter-arrow at shield boundary (defense)
        shield_x = R_shield * np.cos(angle)
        shield_y = R_shield * np.sin(angle)
        shield_z = 0.3 * np.sin(angle * 2)

        ax.quiver(
            shield_x, shield_y, shield_z,
            (ax_start - shield_x) * 0.2, (ay_start - shield_y) * 0.2, (az_start - shield_z) * 0.2,
            color="#00CCFF", alpha=0.6, arrow_length_ratio=0.3, linewidth=1.5,
        )

    ax.set_xlim([-1.5, 1.5])
    ax.set_ylim([-1.5, 1.5])
    ax.set_zlim([-1.5, 1.5])
    ax.set_xlabel("X", color="white", fontsize=10)
    ax.set_ylabel("Y", color="white", fontsize=10)
    ax.set_zlabel("Z", color="white", fontsize=10)
    ax.tick_params(colors="white", labelsize=7)

    # Dark panes
    ax.xaxis.pane.fill = True
    ax.yaxis.pane.fill = True
    ax.zaxis.pane.fill = True
    ax.xaxis.pane.set_facecolor((0.02, 0.02, 0.06, 1.0))
    ax.yaxis.pane.set_facecolor((0.03, 0.03, 0.08, 1.0))
    ax.zaxis.pane.set_facecolor((0.02, 0.02, 0.05, 1.0))
    ax.xaxis.pane.set_edgecolor((0.1, 0.1, 0.2, 0.5))
    ax.yaxis.pane.set_edgecolor((0.1, 0.1, 0.2, 0.5))
    ax.zaxis.pane.set_edgecolor((0.1, 0.1, 0.2, 0.5))
    ax.grid(True, alpha=0.1, color="#334466")

    ax.set_title(
        "Anti-Magnetic Shield — Ferrofluid Active Cancellation\n"
        "Red=external threats | Cyan=counter-field | Green=safe comms\n"
        f"Shield radius={R_shield} | H(d,R)=R^(d^2) at boundary",
        color="white", fontsize=12, fontweight="bold", pad=15,
    )

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color="#FF2222", linewidth=2, label="External B-field (solar wind)"),
        Line2D([0], [0], color="#00CCFF", linewidth=2, label="Shield counter-field"),
        Line2D([0], [0], color="#0066FF", linewidth=2, label="Counter-rotating pair"),
        Line2D([0], [0], color="#00FF88", linewidth=2, label="Safe internal comms"),
        Line2D([0], [0], marker="x", color="#FF4444", linewidth=0, markersize=8,
               label="Deflection point"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=8,
              facecolor="#0a0a1a", labelcolor="white", edgecolor="#333355")

    plt.tight_layout()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts", "visualizations")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "antimagnetic_shield.png")
    plt.savefig(out_path, dpi=150, facecolor="#050510", bbox_inches="tight")
    print(f"Saved: {out_path}")
    plt.show()


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "static"
    spinner = ContentSpinner()

    if cmd == "static":
        print("Rendering static 3D topology...")
        plot_static(spinner)

    elif cmd == "animate" or cmd == "ferrofluid":
        frames = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        print(f"Rendering ferrofluid animation ({frames} frames)...")
        plot_animated(spinner, frames=frames)

    elif cmd == "relay":
        topic = sys.argv[2] if len(sys.argv) > 2 else "ai_governance"
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        print(f"Rendering relay chains for {topic} (depth={depth})...")
        plot_relay_chains(spinner, topic=topic, depth=depth)

    elif cmd == "spectrum":
        print("Rendering harmonic spectrum...")
        plot_harmonic_spectrum()

    elif cmd == "shield":
        print("Rendering anti-magnetic shield...")
        plot_antimagnetic_shield(spinner)

    elif cmd == "all":
        print("Rendering all visualizations...")
        plot_static(spinner)
        plot_relay_chains(spinner, "ai_governance", 3)
        plot_harmonic_spectrum()
        plot_antimagnetic_shield(spinner)

    else:
        print("Usage: python scripts/visualize_spin.py [static|animate|relay|spectrum|all]")
        print("  static           — 3D graph cube snapshot")
        print("  animate [frames] — Ferrofluid harmonic field animation")
        print("  relay [topic] [depth] — Fibonacci relay chain paths")
        print("  spectrum         — Platform harmonic waves + tongue weights")
        print("  all              — Render all static visualizations")


if __name__ == "__main__":
    main()
