"""
================================================================================
SCBE-AETHERMOORE: PLOTLY 3D VISUALIZATION
================================================================================

Interactive 3D visualization using Plotly for:
- Poincare ball with Sacred Tongue agents
- Harmonic Wall cost heatmap
- Flux state evolution
- Polly Pad convergence zones
- Rogue detection trajectories

Designed for Streamlit integration (plotly_chart).

Author: SCBE Development Team
================================================================================
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Constants
PHI = (1 + np.sqrt(5)) / 2
PYTHAGOREAN_COMMA = 531441 / 524288

# Tongue colors and info
TONGUE_CONFIG = {
    'KO': {'color': '#3498db', 'name': 'Control', 'phase': 0},
    'AV': {'color': '#2ecc71', 'name': 'Transport', 'phase': 60},
    'RU': {'color': '#f1c40f', 'name': 'Policy', 'phase': 120},
    'CA': {'color': '#e67e22', 'name': 'Compute', 'phase': 180},
    'UM': {'color': '#9b59b6', 'name': 'Security', 'phase': 240},
    'DR': {'color': '#e74c3c', 'name': 'Schema', 'phase': 300},
}

SECURITY_LEVELS = {'KO': 0.1, 'AV': 0.2, 'RU': 0.4, 'CA': 0.5, 'UM': 0.9, 'DR': 1.0}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_sphere_mesh(radius: float = 1.0, resolution: int = 30) -> Tuple:
    """Create mesh for sphere surface."""
    u = np.linspace(0, 2 * np.pi, resolution)
    v = np.linspace(0, np.pi, resolution)
    x = radius * np.outer(np.cos(u), np.sin(v))
    y = radius * np.outer(np.sin(u), np.sin(v))
    z = radius * np.outer(np.ones(np.size(u)), np.cos(v))
    return x, y, z


def canonical_position_3d(tongue: str) -> np.ndarray:
    """Get canonical 3D position for a tongue."""
    config = TONGUE_CONFIG[tongue]
    phase_rad = np.radians(config['phase'])
    radius = 0.75 * SECURITY_LEVELS[tongue]

    return np.array([
        radius * np.cos(phase_rad),
        radius * np.sin(phase_rad),
        0.1 * SECURITY_LEVELS[tongue]
    ])


# ==============================================================================
# MAIN VISUALIZATION FUNCTIONS
# ==============================================================================

def create_poincare_ball_figure(
    agent_positions: Optional[Dict[str, np.ndarray]] = None,
    show_wall_heatmap: bool = True,
    show_adjacency: bool = True,
    rogue_position: Optional[np.ndarray] = None,
    polly_pad_position: Optional[np.ndarray] = None,
    flux_state: Optional[Dict] = None,
    title: str = "PHDM Poincaré Ball"
) -> go.Figure:
    """
    Create interactive 3D Poincare ball visualization.

    Args:
        agent_positions: Dict of tongue name -> 3D position
        show_wall_heatmap: Show Harmonic Wall cost surface
        show_adjacency: Show adjacency graph edges
        rogue_position: Position of rogue agent (if any)
        polly_pad_position: Position of Polly Pad
        flux_state: Current flux state dict

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Use canonical positions if not provided
    if agent_positions is None:
        agent_positions = {t: canonical_position_3d(t) for t in TONGUE_CONFIG}

    # 1. BOUNDARY SPHERE (transparent)
    x, y, z = create_sphere_mesh(radius=1.0, resolution=30)
    fig.add_trace(go.Surface(
        x=x, y=y, z=z,
        opacity=0.1,
        colorscale=[[0, 'lightblue'], [1, 'lightblue']],
        showscale=False,
        name='Boundary',
        hoverinfo='skip'
    ))

    # 2. HARMONIC WALL COST HEATMAP (on equatorial disk)
    if show_wall_heatmap:
        grid_size = 50
        x_grid = np.linspace(-0.95, 0.95, grid_size)
        y_grid = np.linspace(-0.95, 0.95, grid_size)
        X, Y = np.meshgrid(x_grid, y_grid)
        R = np.sqrt(X**2 + Y**2)

        # Harmonic wall cost: H(d) where d ~ arctanh(r) for distance from origin
        with np.errstate(divide='ignore', invalid='ignore'):
            D = np.where(R < 0.99, 2 * np.arctanh(R), 10)
            H = np.exp(D**2 / 10)  # Scaled for visibility
            H = np.where(R < 0.99, H, np.nan)

        # Mask outside disk
        mask = R > 0.99
        H[mask] = np.nan

        fig.add_trace(go.Surface(
            x=X, y=Y, z=np.zeros_like(X) - 0.05,
            surfacecolor=np.log10(H + 1),
            colorscale='Reds',
            opacity=0.4,
            showscale=True,
            colorbar=dict(title='log₁₀(Wall Cost)', x=1.1),
            name='Harmonic Wall',
            hovertemplate='x: %{x:.2f}<br>y: %{y:.2f}<br>Cost: %{surfacecolor:.2f}<extra>Wall</extra>'
        ))

    # 3. ADJACENCY EDGES
    if show_adjacency:
        adjacency = {
            'KO': ['AV', 'RU'],
            'AV': ['KO', 'CA', 'RU'],
            'RU': ['KO', 'AV', 'UM'],
            'CA': ['AV', 'UM', 'DR'],
            'UM': ['RU', 'CA', 'DR'],
            'DR': ['CA', 'UM'],
        }

        for src, targets in adjacency.items():
            for dst in targets:
                if src < dst:  # Avoid duplicates
                    p1 = agent_positions[src]
                    p2 = agent_positions[dst]
                    fig.add_trace(go.Scatter3d(
                        x=[p1[0], p2[0]],
                        y=[p1[1], p2[1]],
                        z=[p1[2], p2[2]],
                        mode='lines',
                        line=dict(color='gray', width=2, dash='dash'),
                        showlegend=False,
                        hoverinfo='skip'
                    ))

    # 4. SACRED TONGUE AGENTS
    for tongue, pos in agent_positions.items():
        config = TONGUE_CONFIG.get(tongue, {'color': 'gray', 'name': tongue})

        # Agent marker
        fig.add_trace(go.Scatter3d(
            x=[pos[0]],
            y=[pos[1]],
            z=[pos[2]],
            mode='markers+text',
            marker=dict(
                size=15,
                color=config['color'],
                symbol='diamond',
                line=dict(color='white', width=2)
            ),
            text=[tongue],
            textposition='top center',
            textfont=dict(size=12, color='white'),
            name=f"{tongue} ({config['name']})",
            hovertemplate=(
                f"<b>{tongue}</b><br>"
                f"Role: {config['name']}<br>"
                f"Security: {SECURITY_LEVELS.get(tongue, 0.5):.1f}<br>"
                f"φ-weight: {PHI**list(TONGUE_CONFIG.keys()).index(tongue):.3f}<br>"
                f"<extra></extra>"
            )
        ))

    # 5. ROGUE AGENT (if present)
    if rogue_position is not None:
        fig.add_trace(go.Scatter3d(
            x=[rogue_position[0]],
            y=[rogue_position[1]],
            z=[rogue_position[2]],
            mode='markers+text',
            marker=dict(
                size=18,
                color='black',
                symbol='x',
                line=dict(color='red', width=3)
            ),
            text=['ROGUE'],
            textposition='top center',
            textfont=dict(size=14, color='red'),
            name='Rogue Agent',
            hovertemplate="<b>ROGUE</b><br>Status: QUARANTINED<br>Phase: NULL<extra></extra>"
        ))

    # 6. POLLY PAD (if present)
    if polly_pad_position is not None:
        # Draw as glowing sphere
        theta = np.linspace(0, 2*np.pi, 20)
        phi = np.linspace(0, np.pi, 10)
        pad_r = 0.08
        x_pad = polly_pad_position[0] + pad_r * np.outer(np.cos(theta), np.sin(phi))
        y_pad = polly_pad_position[1] + pad_r * np.outer(np.sin(theta), np.sin(phi))
        z_pad = polly_pad_position[2] + pad_r * np.outer(np.ones_like(theta), np.cos(phi))

        fig.add_trace(go.Surface(
            x=x_pad, y=y_pad, z=z_pad,
            opacity=0.5,
            colorscale=[[0, 'gold'], [1, 'yellow']],
            showscale=False,
            name='Polly Pad',
            hovertemplate="<b>POLLY PAD</b><br>Convergence Zone<br>Flux Boost: +0.1<extra></extra>"
        ))

    # 7. FLUX STATE INDICATOR (if present)
    if flux_state:
        # Add annotation for flux state
        D_f = flux_state.get('D_f', 6.0)
        states = flux_state.get('states', ['P'] * 6)
        state_str = ''.join(s[0] if isinstance(s, str) else s.value[0] for s in states)

        flux_color = 'green' if D_f > 5 else 'orange' if D_f > 3 else 'red'

        fig.add_annotation(
            text=f"D_f = {D_f:.2f} | {state_str}",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=14, color=flux_color),
            bgcolor='rgba(0,0,0,0.7)',
            bordercolor=flux_color,
            borderwidth=2
        )

    # LAYOUT
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=20)),
        scene=dict(
            xaxis=dict(range=[-1.1, 1.1], title='X', gridcolor='gray'),
            yaxis=dict(range=[-1.1, 1.1], title='Y', gridcolor='gray'),
            zaxis=dict(range=[-0.5, 0.5], title='Z', gridcolor='gray'),
            aspectmode='cube',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        ),
        legend=dict(
            x=1.02, y=0.5,
            bgcolor='rgba(0,0,0,0.5)',
            font=dict(color='white')
        ),
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig


def create_flux_evolution_figure(
    trajectory: List[Dict],
    title: str = "Dimensional Flux Evolution"
) -> go.Figure:
    """
    Create animated flux state evolution chart.

    Args:
        trajectory: List of flux state dicts with 'nu', 't', 'D_f', 'states'

    Returns:
        Plotly Figure
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Participation Coefficients (ν)', 'Effective Dimension (D_f)'),
        vertical_spacing=0.15
    )

    times = [s['t'] for s in trajectory]
    tongue_names = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']

    # Top plot: individual ν values
    for i, tongue in enumerate(tongue_names):
        nu_values = [s['nu'][i] for s in trajectory]
        fig.add_trace(go.Scatter(
            x=times,
            y=nu_values,
            mode='lines',
            name=tongue,
            line=dict(color=TONGUE_CONFIG[tongue]['color'], width=2)
        ), row=1, col=1)

    # Add POLLY/QUASI/DEMI thresholds
    fig.add_hline(y=0.95, line_dash="dash", line_color="green",
                  annotation_text="POLLY", row=1, col=1)
    fig.add_hline(y=0.5, line_dash="dash", line_color="orange",
                  annotation_text="QUASI", row=1, col=1)
    fig.add_hline(y=0.05, line_dash="dash", line_color="red",
                  annotation_text="DEMI", row=1, col=1)

    # Bottom plot: D_f over time
    D_f_values = [s['D_f'] for s in trajectory]
    fig.add_trace(go.Scatter(
        x=times,
        y=D_f_values,
        mode='lines+markers',
        name='D_f',
        line=dict(color='white', width=3),
        marker=dict(size=5)
    ), row=2, col=1)

    # Add D_f reference lines
    fig.add_hline(y=6.0, line_dash="dash", line_color="green",
                  annotation_text="Full (6D)", row=2, col=1)
    fig.add_hline(y=3.0, line_dash="dash", line_color="orange",
                  annotation_text="Compressed", row=2, col=1)

    fig.update_layout(
        title=dict(text=title, x=0.5),
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#0f0f1a',
        font=dict(color='white'),
        legend=dict(x=1.02, y=0.5),
        height=600
    )

    fig.update_xaxes(title_text="Time", gridcolor='gray', row=2, col=1)
    fig.update_yaxes(title_text="ν", range=[0, 1.05], gridcolor='gray', row=1, col=1)
    fig.update_yaxes(title_text="D_f", range=[0, 6.5], gridcolor='gray', row=2, col=1)

    return fig


def create_consensus_gauge(
    ratio: float,
    threshold: float = 0.67,
    title: str = "Byzantine Consensus"
) -> go.Figure:
    """
    Create gauge chart for consensus ratio.

    Args:
        ratio: Current approval ratio [0, 1]
        threshold: Quorum threshold (default 67%)

    Returns:
        Plotly Figure
    """
    color = 'green' if ratio >= threshold else 'red'

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=ratio * 100,
        delta={'reference': threshold * 100, 'relative': False},
        title={'text': title, 'font': {'size': 18}},
        number={'suffix': '%'},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': 'darkgray',
            'borderwidth': 2,
            'bordercolor': 'white',
            'steps': [
                {'range': [0, threshold * 100], 'color': 'rgba(255,0,0,0.3)'},
                {'range': [threshold * 100, 100], 'color': 'rgba(0,255,0,0.3)'}
            ],
            'threshold': {
                'line': {'color': 'white', 'width': 4},
                'thickness': 0.75,
                'value': threshold * 100
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor='#1a1a2e',
        font=dict(color='white'),
        height=300
    )

    return fig


def create_rogue_trajectory_figure(
    trajectory: List[Dict],
    title: str = "Rogue Agent Ejection"
) -> go.Figure:
    """
    Create animated 3D trajectory of rogue agent ejection.

    Args:
        trajectory: List of dicts with 'rogue_pos', 'step', 'status'

    Returns:
        Plotly Figure
    """
    fig = go.Figure()

    # Boundary sphere
    x, y, z = create_sphere_mesh(radius=1.0, resolution=20)
    fig.add_trace(go.Surface(
        x=x, y=y, z=z,
        opacity=0.1,
        colorscale=[[0, 'lightblue'], [1, 'lightblue']],
        showscale=False,
        hoverinfo='skip'
    ))

    # Sacred tongues (static)
    for tongue in TONGUE_CONFIG:
        pos = canonical_position_3d(tongue)
        config = TONGUE_CONFIG[tongue]
        fig.add_trace(go.Scatter3d(
            x=[pos[0]], y=[pos[1]], z=[pos[2]],
            mode='markers',
            marker=dict(size=10, color=config['color']),
            name=tongue,
            showlegend=False
        ))

    # Rogue trajectory
    rogue_x = [t['rogue_pos'][0] for t in trajectory]
    rogue_y = [t['rogue_pos'][1] for t in trajectory]
    rogue_z = [t['rogue_pos'][2] for t in trajectory]
    steps = [t['step'] for t in trajectory]

    fig.add_trace(go.Scatter3d(
        x=rogue_x, y=rogue_y, z=rogue_z,
        mode='lines+markers',
        marker=dict(
            size=5,
            color=steps,
            colorscale='Hot',
            colorbar=dict(title='Step')
        ),
        line=dict(color='red', width=3),
        name='Rogue Path',
        hovertemplate="Step: %{marker.color}<br>x: %{x:.2f}<br>y: %{y:.2f}<br>z: %{z:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=title, x=0.5),
        scene=dict(
            xaxis=dict(range=[-1.1, 1.1]),
            yaxis=dict(range=[-1.1, 1.1]),
            zaxis=dict(range=[-0.5, 0.5]),
            aspectmode='cube'
        ),
        paper_bgcolor='#1a1a2e',
        font=dict(color='white'),
        height=600
    )

    return fig


# ==============================================================================
# DEMO
# ==============================================================================

def demo():
    """Generate demo figures."""
    print("=" * 60)
    print("PLOTLY VISUALIZATION DEMO")
    print("=" * 60)

    # 1. Basic Poincare ball
    print("\n1. Creating Poincare ball visualization...")
    fig1 = create_poincare_ball_figure(
        show_wall_heatmap=True,
        show_adjacency=True,
        polly_pad_position=np.array([0.0, 0.0, 0.1]),
        flux_state={'D_f': 5.4, 'states': ['POLLY'] * 6}
    )
    fig1.write_html("demo_poincare_ball.html")
    print("   Saved: demo_poincare_ball.html")

    # 2. Flux evolution
    print("\n2. Creating flux evolution chart...")
    trajectory = []
    nu = np.ones(6) * 0.9
    for t in range(50):
        # Simulate oscillation
        nu = nu + 0.02 * np.sin(np.arange(6) * 0.5 + t * 0.2) - 0.01 * (nu - 0.8)
        nu = np.clip(nu, 0.1, 1.0)
        trajectory.append({
            'nu': nu.copy(),
            't': t * 0.1,
            'D_f': np.sum(nu),
            'states': ['POLLY' if n >= 0.95 else 'QUASI' if n >= 0.5 else 'DEMI' for n in nu]
        })

    fig2 = create_flux_evolution_figure(trajectory)
    fig2.write_html("demo_flux_evolution.html")
    print("   Saved: demo_flux_evolution.html")

    # 3. Consensus gauge
    print("\n3. Creating consensus gauge...")
    fig3 = create_consensus_gauge(ratio=0.78, threshold=0.67)
    fig3.write_html("demo_consensus_gauge.html")
    print("   Saved: demo_consensus_gauge.html")

    # 4. Rogue trajectory
    print("\n4. Creating rogue trajectory visualization...")
    rogue_trajectory = []
    rogue_pos = np.array([0.1, 0.1, 0.0])
    for step in range(30):
        # Simulate ejection
        rogue_pos = rogue_pos + np.random.randn(3) * 0.03
        rogue_pos[2] = 0.0  # Keep in plane
        rogue_pos = rogue_pos * min(1, (0.99 / (np.linalg.norm(rogue_pos) + 0.01)))
        rogue_trajectory.append({
            'rogue_pos': rogue_pos.copy(),
            'step': step,
            'status': 'ROGUE' if step > 10 else 'SUSPICIOUS'
        })

    fig4 = create_rogue_trajectory_figure(rogue_trajectory)
    fig4.write_html("demo_rogue_trajectory.html")
    print("   Saved: demo_rogue_trajectory.html")

    print("\n" + "=" * 60)
    print("Demo complete! Open the HTML files in a browser.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
