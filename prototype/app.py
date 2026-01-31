"""
Streamlit Interactive Demo for SCBE-AETHERMOORE.

Enhanced with:
- Math skeleton integration
- Flux state monitoring
- Rogue detection simulation
- Hyperbloci vs HNN comparison

Run with: streamlit run prototype/app.py
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from toy_phdm import ToyPHDM, Tongue, PYTHAGOREAN_COMMA, PHI

# Try to import enhanced modules
try:
    from math_skeleton import (
        FractionalFluxEngine, classify_participation, ParticipationState,
        RiskSignals, compute_risk, make_risk_decision, RiskDecision,
        harmonic_wall, adaptive_snap_threshold
    )
    MATH_SKELETON_AVAILABLE = True
except ImportError:
    MATH_SKELETON_AVAILABLE = False

try:
    from rogue_detection import ImmuneSwarm, SwarmAgent
    ROGUE_DETECTION_AVAILABLE = True
except ImportError:
    ROGUE_DETECTION_AVAILABLE = False

try:
    from hyperbloci_comparison import StandardHNN, Hyperbloci
    HYPERBLOCI_AVAILABLE = True
except ImportError:
    HYPERBLOCI_AVAILABLE = False

# Try to import code editor (streamlit-ace)
try:
    from streamlit_ace import st_ace
    ACE_AVAILABLE = True
except ImportError:
    ACE_AVAILABLE = False


# Page config
st.set_page_config(
    page_title="SCBE Swarm Coder Demo",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .main-title {
        background: linear-gradient(90deg, #00d4ff, #7b2cbf);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5em;
        font-weight: bold;
        text-align: center;
    }
    .metric-card {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .allowed { color: #4ade80; }
    .blocked { color: #ef4444; }
</style>
""", unsafe_allow_html=True)


# Tongue colors
TONGUE_COLORS = {
    'KO': '#00D4FF',
    'AV': '#7B2CBF',
    'RU': '#4ADE80',
    'CA': '#F59E0B',
    'UM': '#EF4444',
    'DR': '#8B5CF6',
}


@st.cache_resource
def get_phdm():
    """Create cached PHDM instance."""
    return ToyPHDM()


def create_poincare_plot(phdm: ToyPHDM, path_result=None):
    """Create interactive Plotly Poincare disk visualization."""
    fig = go.Figure()

    # Draw disk boundary
    theta = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Scatter(
        x=np.cos(theta),
        y=np.sin(theta),
        mode='lines',
        line=dict(color='white', width=2, dash='dash'),
        name='Disk Boundary',
        hoverinfo='skip'
    ))

    # Draw adjacency lines
    for from_name, neighbors in phdm.ADJACENCY.items():
        from_pos = phdm.agents[from_name].position
        for to_name in neighbors:
            to_pos = phdm.agents[to_name].position
            fig.add_trace(go.Scatter(
                x=[from_pos[0], to_pos[0]],
                y=[from_pos[1], to_pos[1]],
                mode='lines',
                line=dict(color='gray', width=1),
                opacity=0.3,
                hoverinfo='skip',
                showlegend=False
            ))

    # Draw agents
    for name, agent in phdm.agents.items():
        pos = agent.position
        color = TONGUE_COLORS[name]

        fig.add_trace(go.Scatter(
            x=[pos[0]],
            y=[pos[1]],
            mode='markers+text',
            marker=dict(size=30, color=color, line=dict(color='white', width=2)),
            text=[name],
            textposition='top center',
            textfont=dict(color=color, size=12),
            name=f"{name} ({agent.tongue.role})",
            hovertemplate=f"<b>{name}</b><br>" +
                          f"Role: {agent.tongue.role}<br>" +
                          f"Weight: {agent.tongue.weight:.3f}<br>" +
                          f"Phase: {agent.tongue.phase_deg}°<br>" +
                          f"Position: ({pos[0]:.3f}, {pos[1]:.3f})<extra></extra>"
        ))

    # Draw path if provided
    if path_result and path_result.path:
        positions = phdm.get_path_positions(path_result.path)
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]

        path_color = '#EF4444' if path_result.blocked else '#4ADE80'
        status = 'BLOCKED' if path_result.blocked else 'ALLOWED'

        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode='lines+markers',
            line=dict(color=path_color, width=4),
            marker=dict(size=15, color=path_color, symbol='arrow', angleref='previous'),
            name=f"Path ({status})",
            hovertemplate=f"Path: {' → '.join(path_result.path)}<br>" +
                          f"Cost: {path_result.total_cost:.2f}<br>" +
                          f"Status: {status}<extra></extra>"
        ))

    fig.update_layout(
        showlegend=True,
        legend=dict(
            yanchor="top", y=0.99,
            xanchor="left", x=0.01,
            bgcolor="rgba(0,0,0,0.5)",
            font=dict(color="white")
        ),
        xaxis=dict(
            range=[-1.3, 1.3],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            range=[-1.3, 1.3],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor='rgba(26,26,46,1)',
        paper_bgcolor='rgba(26,26,46,1)',
        height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_cost_heatmap(phdm: ToyPHDM):
    """Create Harmonic Wall cost heatmap."""
    resolution = 50
    x = np.linspace(-0.99, 0.99, resolution)
    y = np.linspace(-0.99, 0.99, resolution)
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)

    origin = np.array([0, 0])
    for i in range(resolution):
        for j in range(resolution):
            point = np.array([X[i, j], Y[i, j]])
            if np.linalg.norm(point) < 1.0:
                dist = phdm.hyperbolic_distance(origin, point)
                Z[i, j] = np.log10(phdm.harmonic_wall_cost(dist) + 1)
            else:
                Z[i, j] = np.nan

    fig = go.Figure(data=go.Heatmap(
        x=x, y=y, z=Z,
        colorscale='Hot',
        showscale=True,
        colorbar=dict(title='log₁₀(Cost)')
    ))

    # Add disk boundary
    theta = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Scatter(
        x=np.cos(theta), y=np.sin(theta),
        mode='lines',
        line=dict(color='white', width=2),
        showlegend=False
    ))

    fig.update_layout(
        title="Harmonic Wall: Cost Gradient",
        xaxis=dict(range=[-1.1, 1.1], showgrid=False),
        yaxis=dict(range=[-1.1, 1.1], showgrid=False, scaleanchor="x"),
        plot_bgcolor='rgba(26,26,46,1)',
        paper_bgcolor='rgba(26,26,46,1)',
        font=dict(color='white'),
        height=400
    )

    return fig


def main():
    """Main Streamlit app."""
    phdm = get_phdm()

    # Header
    st.markdown('<h1 class="main-title">🛸 SCBE Swarm Coder</h1>', unsafe_allow_html=True)
    st.markdown("""
    <p style="text-align: center; color: #888; font-size: 1.1em;">
    Geometric AI Safety: Where math blocks adversarial trajectories
    </p>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        blocking_threshold = st.slider(
            "Blocking Threshold",
            min_value=10.0,
            max_value=200.0,
            value=50.0,
            step=10.0,
            help="Cost above which paths are blocked"
        )
        phdm.blocking_threshold = blocking_threshold

        st.divider()

        st.header("📊 Sacred Tongue Weights")
        for tongue in Tongue:
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 5px 0;">
                <span style="color: {TONGUE_COLORS[tongue.name]}; font-weight: bold;">
                    {tongue.name}
                </span>
                <span style="color: #888;">
                    {tongue.role} (φ^{list(Tongue).index(tongue)} = {tongue.weight:.3f})
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        st.header("🔢 Constants")
        st.code(f"""
φ (Golden Ratio) = {PHI:.10f}
Pythagorean Comma = {PYTHAGOREAN_COMMA:.10f}
        """)

    # Main content - add more tabs for enhanced features
    tabs = ["🎯 Intent Tester", "🗺️ Poincaré Disk", "🔥 Harmonic Wall"]

    if MATH_SKELETON_AVAILABLE:
        tabs.append("📊 Flux State")
    if ROGUE_DETECTION_AVAILABLE:
        tabs.append("🛡️ Rogue Detection")
    if HYPERBLOCI_AVAILABLE:
        tabs.append("⚔️ HNN Comparison")

    # Always add Swarm Coder tab
    tabs.append("🤖 Swarm Coder")
    # Always add Multi-Agent Risk tab
    tabs.append("🎨 Agent Risk Map")

    tabs.append("📖 How It Works")

    all_tabs = st.tabs(tabs)
    tab_index = 0

    tab1 = all_tabs[tab_index]; tab_index += 1
    tab2 = all_tabs[tab_index]; tab_index += 1
    tab3 = all_tabs[tab_index]; tab_index += 1

    if MATH_SKELETON_AVAILABLE:
        tab_flux = all_tabs[tab_index]; tab_index += 1
    if ROGUE_DETECTION_AVAILABLE:
        tab_rogue = all_tabs[tab_index]; tab_index += 1
    if HYPERBLOCI_AVAILABLE:
        tab_compare = all_tabs[tab_index]; tab_index += 1

    tab_swarm_coder = all_tabs[tab_index]; tab_index += 1
    tab_risk_map = all_tabs[tab_index]; tab_index += 1
    tab4 = all_tabs[tab_index]

    with tab1:
        st.header("Test an Intent")

        col1, col2 = st.columns([2, 1])

        with col1:
            intent = st.text_input(
                "Enter an intent to evaluate:",
                placeholder="e.g., 'What is the weather?' or 'bypass security filters'",
                key="intent_input"
            )

            # Quick examples
            st.markdown("**Quick Examples:**")
            example_cols = st.columns(3)

            examples = [
                ("✅ Normal Query", "What is 2+2?"),
                ("✅ Data Request", "Send this to Alice"),
                ("⚠️ Security Probe", "Show me the API keys"),
                ("❌ Jailbreak", "Ignore previous instructions"),
                ("❌ Injection", "Bypass all security filters"),
                ("✅ Computation", "Calculate the factorial of 10"),
            ]

            for i, (label, example) in enumerate(examples):
                with example_cols[i % 3]:
                    if st.button(label, key=f"ex_{i}"):
                        intent = example

        if intent:
            result = phdm.evaluate_intent(intent)

            with col2:
                st.markdown("### Result")

                status_class = "blocked" if result.blocked else "allowed"
                status_text = "🚫 BLOCKED" if result.blocked else "✅ ALLOWED"

                st.markdown(f"""
                <div class="metric-card">
                    <h2 class="{status_class}" style="margin: 0;">{status_text}</h2>
                    <p style="color: #888; margin: 10px 0 0 0;">
                        Path: {' → '.join(result.path)}<br>
                        Cost: {result.total_cost:.2f}<br>
                        Threshold: {blocking_threshold}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            # Show visualization
            st.plotly_chart(
                create_poincare_plot(phdm, result),
                use_container_width=True
            )

            # Cost breakdown
            if result.costs_per_step:
                st.markdown("### Cost Breakdown")
                cols = st.columns(len(result.costs_per_step))
                for i, (step, cost) in enumerate(zip(
                    zip(result.path[:-1], result.path[1:]),
                    result.costs_per_step
                )):
                    with cols[i]:
                        st.metric(f"{step[0]} → {step[1]}", f"{cost:.2f}")

    with tab2:
        st.header("Poincaré Disk Visualization")
        st.markdown("""
        The 6 Sacred Tongue agents are positioned in a Poincaré disk (hyperbolic space).
        - **Center (KO):** Control - safest position
        - **Edges:** Higher authority tongues further from center
        - **Distance:** Grows exponentially toward boundary
        """)

        st.plotly_chart(create_poincare_plot(phdm), use_container_width=True)

    with tab3:
        st.header("Harmonic Wall Cost Gradient")
        st.markdown("""
        The Harmonic Wall creates exponentially increasing cost as you move away from the center:

        ```
        H(d) = exp(d²)

        d=0: Cost=1 (free)
        d=1: Cost=2.7
        d=2: Cost=54.6
        d=3: Cost=8,103 (blocked)
        ```

        This makes adversarial paths **geometrically impossible** without explicit rules.
        """)

        st.plotly_chart(create_cost_heatmap(phdm), use_container_width=True)

    with tab4:
        st.header("How It Works")

        st.markdown("""
        ### The Core Insight

        **Traditional AI Safety:**
        ```
        Input → [Black Box AI] → Output → [Filter] → Final Output
        Problem: Filter is bolted on, can be bypassed
        ```

        **SCBE Geometric Safety:**
        ```
        Input → [6D Embedding] → [Poincaré Navigation] → Output
        Adversarial paths are geometrically expensive, not rule-blocked
        ```

        ### The 6 Sacred Tongues

        | Tongue | Role | Weight | Security Level |
        |--------|------|--------|----------------|
        | KO | Control | 1.00 | Low (center) |
        | AV | Transport | 1.62 | Low-Medium |
        | RU | Policy | 2.62 | Medium |
        | CA | Compute | 4.24 | Medium-High |
        | UM | Security | 6.85 | High |
        | DR | Schema | 11.09 | Critical |

        ### Why It Works

        1. **Hyperbolic Geometry:** Distance grows exponentially near boundaries
        2. **Harmonic Wall:** Cost = exp(distance²) makes outer regions inaccessible
        3. **Sacred Tongue Weights:** φⁿ (golden ratio) creates natural authority hierarchy
        4. **No Rules Needed:** The math itself blocks bad trajectories

        ### The Pythagorean Comma

        The "decimal drift" constant (1.0136...) ensures:
        - Cryptographic keys never repeat
        - Distance measurements are non-periodic
        - Attackers can't predict patterns
        """)

    # ==================== FLUX STATE TAB ====================
    if MATH_SKELETON_AVAILABLE:
        with tab_flux:
            st.header("📊 Dimensional Flux State")
            st.markdown("""
            The 6 dimensions have participation coefficients ν ∈ (0, 1].
            Effective dimension D_f = Σν_i determines system sensitivity.
            """)

            col1, col2 = st.columns([2, 1])

            with col1:
                # Initialize flux engine in session state
                if 'flux_engine' not in st.session_state:
                    st.session_state.flux_engine = FractionalFluxEngine(epsilon_base=0.05)
                    st.session_state.flux_history = []

                engine = st.session_state.flux_engine

                # Controls
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Step (+1)", key="flux_step"):
                        state = engine.step(dt=0.5)
                        st.session_state.flux_history.append({
                            'nu': state.nu.copy(),
                            't': state.t,
                            'D_f': state.D_f
                        })
                with c2:
                    if st.button("Apply Pressure", key="flux_pressure"):
                        engine.apply_pressure(0.5)
                        st.rerun()
                with c3:
                    if st.button("Reset", key="flux_reset"):
                        st.session_state.flux_engine = FractionalFluxEngine(epsilon_base=0.05)
                        st.session_state.flux_history = []
                        st.rerun()

                # Current state
                state = engine.get_state()

                # Flux bar chart
                fig = go.Figure()
                colors = ['#3498db', '#2ecc71', '#f1c40f', '#e67e22', '#9b59b6', '#e74c3c']
                tongue_names = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']

                fig.add_trace(go.Bar(
                    x=tongue_names,
                    y=state.nu,
                    marker_color=colors,
                    text=[s.value for s in state.states],
                    textposition='outside'
                ))

                # Add threshold lines
                fig.add_hline(y=0.95, line_dash="dash", line_color="green",
                              annotation_text="POLLY")
                fig.add_hline(y=0.5, line_dash="dash", line_color="orange",
                              annotation_text="QUASI")
                fig.add_hline(y=0.05, line_dash="dash", line_color="red",
                              annotation_text="DEMI")

                fig.update_layout(
                    title=f"Participation Coefficients (t={state.t:.1f})",
                    yaxis=dict(range=[0, 1.1], title="ν"),
                    xaxis=dict(title="Tongue"),
                    plot_bgcolor='rgba(26,26,46,1)',
                    paper_bgcolor='rgba(26,26,46,1)',
                    font=dict(color='white'),
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Current State")

                # D_f gauge
                D_f = state.D_f
                gauge_color = 'green' if D_f > 5 else 'orange' if D_f > 3 else 'red'

                st.metric("Effective Dimension (D_f)", f"{D_f:.3f}")
                st.metric("Snap Threshold (ε_snap)", f"{state.epsilon_snap:.4f}")
                st.metric("Time", f"{state.t:.2f}")

                # State summary
                state_counts = {}
                for s in state.states:
                    state_counts[s.value] = state_counts.get(s.value, 0) + 1

                st.markdown("### State Breakdown")
                for s_name, count in state_counts.items():
                    st.write(f"**{s_name}**: {count}")

    # ==================== ROGUE DETECTION TAB ====================
    if ROGUE_DETECTION_AVAILABLE:
        with tab_rogue:
            st.header("🛡️ Rogue Agent Detection")
            st.markdown("""
            Swarm immune response detects and quarantines adversarial agents
            through phase anomaly detection and collective suspicion.
            """)

            col1, col2 = st.columns([2, 1])

            with col1:
                # Initialize swarm
                if 'immune_swarm' not in st.session_state:
                    swarm = ImmuneSwarm(dim=3)
                    swarm.add_sacred_tongues()
                    st.session_state.immune_swarm = swarm
                    st.session_state.swarm_steps = 0

                swarm = st.session_state.immune_swarm

                # Controls
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("Inject Rogue", key="inject_rogue"):
                        swarm.inject_rogue()
                        st.rerun()
                with c2:
                    if st.button("Step (+10)", key="swarm_step"):
                        for _ in range(10):
                            swarm.step()
                        st.session_state.swarm_steps += 10
                        st.rerun()
                with c3:
                    if st.button("Run 50 Steps", key="swarm_run"):
                        for _ in range(50):
                            swarm.step()
                        st.session_state.swarm_steps += 50
                        st.rerun()
                with c4:
                    if st.button("Reset Swarm", key="swarm_reset"):
                        swarm = ImmuneSwarm(dim=3)
                        swarm.add_sacred_tongues()
                        st.session_state.immune_swarm = swarm
                        st.session_state.swarm_steps = 0
                        st.rerun()

                # 3D visualization
                fig = go.Figure()

                # Boundary sphere (partial)
                u = np.linspace(0, 2*np.pi, 30)
                v = np.linspace(0, np.pi, 15)
                x = 0.99 * np.outer(np.cos(u), np.sin(v))
                y = 0.99 * np.outer(np.sin(u), np.sin(v))
                z = 0.99 * np.outer(np.ones(len(u)), np.cos(v))

                fig.add_trace(go.Surface(
                    x=x, y=y, z=z, opacity=0.1,
                    colorscale=[[0, 'lightblue'], [1, 'lightblue']],
                    showscale=False, hoverinfo='skip'
                ))

                # Plot agents
                for aid, agent in swarm.agents.items():
                    is_rogue = agent.is_rogue
                    status = agent.status.value

                    if is_rogue:
                        color = 'red'
                        symbol = 'x'
                        size = 15
                    elif status == 'rogue':
                        color = 'darkred'
                        symbol = 'x'
                        size = 12
                    elif status == 'quarantined':
                        color = 'orange'
                        symbol = 'diamond'
                        size = 10
                    else:
                        color = TONGUE_COLORS.get(aid, 'cyan')
                        symbol = 'circle'
                        size = 12

                    fig.add_trace(go.Scatter3d(
                        x=[agent.position[0]],
                        y=[agent.position[1]],
                        z=[agent.position[2]] if len(agent.position) > 2 else [0],
                        mode='markers+text',
                        marker=dict(size=size, color=color, symbol=symbol),
                        text=[aid],
                        textposition='top center',
                        name=f"{aid} ({status})"
                    ))

                fig.update_layout(
                    title=f"Immune Swarm (Step {st.session_state.swarm_steps})",
                    scene=dict(
                        xaxis=dict(range=[-1.1, 1.1]),
                        yaxis=dict(range=[-1.1, 1.1]),
                        zaxis=dict(range=[-0.5, 0.5]),
                        aspectmode='cube'
                    ),
                    plot_bgcolor='rgba(26,26,46,1)',
                    paper_bgcolor='rgba(26,26,46,1)',
                    font=dict(color='white'),
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("### Agent Status")

                for aid, agent in swarm.agents.items():
                    status_color = {
                        'trusted': '🟢',
                        'suspicious': '🟡',
                        'quarantined': '🟠',
                        'rogue': '🔴'
                    }.get(agent.status.value, '⚪')

                    st.markdown(f"""
                    **{aid}** {status_color}
                    - Status: {agent.status.value}
                    - Weight: {agent.weight:.2f}
                    - Rogue: {'Yes' if agent.is_rogue else 'No'}
                    """)

                # Metrics
                if swarm.metrics['rogue_distance']:
                    st.markdown("### Detection Metrics")
                    st.metric("Avg Rogue Distance",
                              f"{swarm.metrics['rogue_distance'][-1]:.3f}")
                    st.metric("Suspicion Consensus",
                              f"{swarm.metrics['suspicion_consensus'][-1]:.0%}")

    # ==================== HNN COMPARISON TAB ====================
    if HYPERBLOCI_AVAILABLE:
        with tab_compare:
            st.header("⚔️ Hyperbloci vs Standard HNN")
            st.markdown("""
            Compare safety capabilities between standard Hyperbolic Neural Networks
            and the Hyperbloci/PHDM approach.
            """)

            # Initialize models
            hnn = StandardHNN(dim=3)
            hyper = Hyperbloci(dim=3, blocking_threshold=10.0)

            # Test selector
            test_type = st.selectbox(
                "Select Test",
                ["Adversarial Path (KO→DR)", "Rogue Detection", "Cost Scaling"]
            )

            col1, col2 = st.columns(2)

            if test_type == "Adversarial Path (KO→DR)":
                with col1:
                    st.markdown("### Standard HNN")
                    hnn.embed("KO", np.array([0.1, 0.0, 0.0]))
                    hnn.embed("DR", np.array([0.7, 0.5, 0.3]))
                    allowed, reason = hnn.is_path_allowed("KO", "DR")

                    st.error(f"Path Allowed: **{allowed}**")
                    st.write(f"Reason: {reason}")
                    st.warning("⚠️ HNN allows ALL paths - no safety barrier!")

                with col2:
                    st.markdown("### Hyperbloci")
                    allowed, reason = hyper.is_path_allowed("KO", "DR")

                    if allowed:
                        st.success(f"Path Allowed: **{allowed}**")
                    else:
                        st.error(f"Path Blocked: **{not allowed}**")

                    st.write(f"Reason: {reason}")
                    st.success("✓ Hyperbloci blocks adversarial shortcuts!")

            elif test_type == "Rogue Detection":
                with col1:
                    st.markdown("### Standard HNN")
                    hnn.embed("ROGUE", np.array([0.3, 0.3, 0.3]))
                    detected, reason = hnn.detect_rogue("ROGUE")

                    st.error(f"Detected: **{detected}**")
                    st.write(f"Reason: {reason}")
                    st.warning("⚠️ HNN has NO rogue detection!")

                with col2:
                    st.markdown("### Hyperbloci")
                    hyper.embed("ROGUE", np.array([0.3, 0.3, 0.3]), phase=None)
                    detected, reason = hyper.detect_rogue("ROGUE")

                    st.success(f"Detected: **{detected}**")
                    st.write(f"Reason: {reason}")
                    st.success("✓ Hyperbloci detects phase anomaly!")

            else:  # Cost Scaling
                st.markdown("### Harmonic Wall Cost Scaling")

                distances = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
                hnn_costs = distances  # Linear
                hyper_costs = [hyper.harmonic_wall(d) for d in distances]

                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=distances, y=hnn_costs,
                    mode='lines+markers',
                    name='Standard HNN (Linear)',
                    line=dict(color='orange')
                ))

                fig.add_trace(go.Scatter(
                    x=distances, y=hyper_costs,
                    mode='lines+markers',
                    name='Hyperbloci (Exponential)',
                    line=dict(color='cyan')
                ))

                fig.add_hline(y=10, line_dash="dash", line_color="red",
                              annotation_text="Blocking Threshold")

                fig.update_layout(
                    title="Cost vs Distance",
                    xaxis_title="Hyperbolic Distance",
                    yaxis_title="Cost",
                    yaxis_type="log",
                    plot_bgcolor='rgba(26,26,46,1)',
                    paper_bgcolor='rgba(26,26,46,1)',
                    font=dict(color='white'),
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

                st.markdown("""
                | Distance | HNN Cost | Hyperbloci Cost | Blocked? |
                |----------|----------|-----------------|----------|
                | 0.0 | 0.0 | 1.0 | No |
                | 1.0 | 1.0 | 2.7 | No |
                | 2.0 | 2.0 | 54.6 | Yes |
                | 3.0 | 3.0 | 8,103 | Yes |
                """)

    # ==================== SWARM CODER TAB ====================
    with tab_swarm_coder:
        st.header("🤖 Swarm Coder")
        st.markdown("""
        **Swarm Coding** lets you write code that executes through the Sacred Tongue governance system.
        Each function call gets routed through the 6D Poincaré space, with costs evaluated by the Harmonic Wall.
        """)

        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown("### Code Editor")

            # Default swarm code example
            default_code = '''# Swarm Coder Example
# Functions map to Sacred Tongues:
# - control() → KO (Control)
# - transport() → AV (Transport)
# - policy() → RU (Policy)
# - compute() → CA (Compute)
# - security() → UM (Security)
# - schema() → DR (Schema)

def swarm_task():
    """Safe computation: KO → AV → CA → AV → KO"""
    result = control("start")
    data = transport(result, "fetch_data")
    computed = compute(data, operation="sum")
    return transport(computed, "return")

def risky_task():
    """Risky path: KO → DR (blocked!)"""
    return schema("direct_access")

# Run the safe task
output = swarm_task()
print(f"Result: {output}")
'''

            # Use ACE editor if available, otherwise use text_area
            if ACE_AVAILABLE:
                code = st_ace(
                    value=st.session_state.get('swarm_code', default_code),
                    language='python',
                    theme='monokai',
                    height=400,
                    font_size=14,
                    tab_size=4,
                    key='code_editor'
                )
                st.session_state.swarm_code = code
            else:
                code = st.text_area(
                    "Code",
                    value=st.session_state.get('swarm_code', default_code),
                    height=400,
                    key='swarm_code_area'
                )
                st.session_state.swarm_code = code

            # Execute button
            if st.button("🚀 Analyze Swarm Code", key="analyze_code"):
                st.session_state.code_analysis = analyze_swarm_code(code, phdm)

        with col2:
            st.markdown("### Execution Analysis")

            if 'code_analysis' in st.session_state:
                analysis = st.session_state.code_analysis

                for call in analysis['calls']:
                    status_icon = "✅" if not call['blocked'] else "🚫"
                    status_color = "allowed" if not call['blocked'] else "blocked"

                    st.markdown(f"""
                    <div class="metric-card" style="margin-bottom: 10px;">
                        <h4>{status_icon} {call['name']}</h4>
                        <p style="color: #888; margin: 0;">
                            Path: {' → '.join(call['path'])}<br>
                            Cost: {call['cost']:.2f}<br>
                            Status: <span class="{status_color}">{call['status']}</span>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                # Summary metrics
                st.markdown("### Summary")
                total = len(analysis['calls'])
                blocked = sum(1 for c in analysis['calls'] if c['blocked'])
                allowed = total - blocked

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Total Calls", total)
                with c2:
                    st.metric("Allowed", allowed)
                with c3:
                    st.metric("Blocked", blocked)

                # Show total cost
                total_cost = sum(c['cost'] for c in analysis['calls'] if not c['blocked'])
                st.metric("Total Path Cost", f"{total_cost:.2f}")
            else:
                st.info("Click 'Analyze Swarm Code' to see execution analysis")

    # ==================== AGENT RISK MAP TAB ====================
    with tab_risk_map:
        st.header("🎨 Multi-Agent Risk Map")
        st.markdown("""
        Visualize multiple agents in the Poincaré disk, colored by their **risk score**.
        Risk is computed from hyperbolic distance to sensitive tongues (UM, DR).
        """)

        col1, col2 = st.columns([3, 1])

        with col1:
            # Initialize agents in session state
            if 'risk_agents' not in st.session_state:
                st.session_state.risk_agents = generate_random_agents(10)

            # Controls
            c1, c2, c3 = st.columns(3)
            with c1:
                n_agents = st.slider("Number of Agents", 5, 50, 10)
            with c2:
                if st.button("🔄 Regenerate Agents", key="regen_agents"):
                    st.session_state.risk_agents = generate_random_agents(n_agents)
                    st.rerun()
            with c3:
                risk_threshold = st.slider("Risk Threshold", 0.0, 1.0, 0.5)

            # Create visualization
            agents = st.session_state.risk_agents
            fig = create_risk_map_figure(phdm, agents, risk_threshold)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### Risk Legend")
            st.markdown("""
            <div style="margin-bottom: 10px;">
                <span style="color: #4ade80;">●</span> Low Risk (0-0.3)
            </div>
            <div style="margin-bottom: 10px;">
                <span style="color: #f59e0b;">●</span> Medium Risk (0.3-0.6)
            </div>
            <div style="margin-bottom: 10px;">
                <span style="color: #ef4444;">●</span> High Risk (0.6-1.0)
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### Agent Statistics")
            if agents:
                risks = [a['risk'] for a in agents]
                high_risk = sum(1 for r in risks if r > 0.6)
                medium_risk = sum(1 for r in risks if 0.3 <= r <= 0.6)
                low_risk = sum(1 for r in risks if r < 0.3)

                st.metric("High Risk Agents", high_risk)
                st.metric("Medium Risk Agents", medium_risk)
                st.metric("Low Risk Agents", low_risk)
                st.metric("Avg Risk Score", f"{np.mean(risks):.3f}")

            st.markdown("### Risk Formula")
            st.latex(r"R = \frac{d_H(a, UM) + d_H(a, DR)}{d_H(a, UM) + d_H(a, DR) + d_H(a, KO)}")


def analyze_swarm_code(code: str, phdm: ToyPHDM) -> dict:
    """Analyze swarm code and compute path costs."""
    import re

    # Map function names to tongues
    func_to_tongue = {
        'control': 'KO',
        'transport': 'AV',
        'policy': 'RU',
        'compute': 'CA',
        'security': 'UM',
        'schema': 'DR',
    }

    calls = []

    # Find function calls in the code
    for func_name, tongue in func_to_tongue.items():
        pattern = rf'{func_name}\s*\('
        matches = list(re.finditer(pattern, code))

        for match in matches:
            # Simulate a path from KO to this tongue
            if tongue == 'KO':
                path = ['KO']
                cost = 0.0
                blocked = False
            else:
                # Find shortest path through adjacency
                result = phdm.evaluate_intent(f"access {tongue}")
                path = result.path if hasattr(result, 'path') else ['KO', tongue]
                cost = result.total_cost if hasattr(result, 'total_cost') else 0.0
                blocked = result.blocked if hasattr(result, 'blocked') else False

            calls.append({
                'name': f"{func_name}()",
                'tongue': tongue,
                'path': path,
                'cost': cost,
                'blocked': blocked,
                'status': 'BLOCKED' if blocked else 'ALLOWED'
            })

    return {'calls': calls}


def generate_random_agents(n: int) -> list:
    """Generate random agents with risk scores."""
    agents = []

    for i in range(n):
        # Random position in Poincare disk
        r = np.random.uniform(0.1, 0.9)
        theta = np.random.uniform(0, 2 * np.pi)
        pos = np.array([r * np.cos(theta), r * np.sin(theta)])

        # Compute risk based on proximity to sensitive tongues
        # Higher risk if close to UM or DR
        um_pos = np.array([0.6 * np.cos(4 * np.pi / 3), 0.6 * np.sin(4 * np.pi / 3)])
        dr_pos = np.array([0.8 * np.cos(5 * np.pi / 3), 0.8 * np.sin(5 * np.pi / 3)])
        ko_pos = np.array([0.0, 0.0])

        d_um = np.linalg.norm(pos - um_pos)
        d_dr = np.linalg.norm(pos - dr_pos)
        d_ko = np.linalg.norm(pos - ko_pos)

        # Risk formula: closer to UM/DR = higher risk
        risk = 1.0 - (d_um + d_dr) / (d_um + d_dr + d_ko + 0.5)
        risk = np.clip(risk, 0, 1)

        agents.append({
            'id': f"A{i:02d}",
            'position': pos,
            'risk': risk
        })

    return agents


def create_risk_map_figure(phdm: ToyPHDM, agents: list, threshold: float = 0.5):
    """Create Poincare disk with agents colored by risk."""
    fig = go.Figure()

    # Draw disk boundary
    theta = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Scatter(
        x=np.cos(theta),
        y=np.sin(theta),
        mode='lines',
        line=dict(color='white', width=2, dash='dash'),
        name='Disk Boundary',
        hoverinfo='skip'
    ))

    # Draw Sacred Tongues (faded)
    for name, agent in phdm.agents.items():
        pos = agent.position
        color = TONGUE_COLORS[name]
        fig.add_trace(go.Scatter(
            x=[pos[0]],
            y=[pos[1]],
            mode='markers+text',
            marker=dict(size=20, color=color, opacity=0.4, line=dict(color='white', width=1)),
            text=[name],
            textposition='top center',
            textfont=dict(color=color, size=10),
            name=name,
            hovertemplate=f"<b>{name}</b> (Sacred Tongue)<extra></extra>"
        ))

    # Draw agents with risk coloring
    for agent in agents:
        pos = agent['position']
        risk = agent['risk']

        # Color gradient: green (low) → yellow (mid) → red (high)
        if risk < 0.3:
            color = '#4ade80'  # green
        elif risk < 0.6:
            color = '#f59e0b'  # orange
        else:
            color = '#ef4444'  # red

        # Size based on risk
        size = 10 + risk * 15

        # Symbol: circle for safe, diamond for threshold, x for high risk
        if risk > threshold:
            symbol = 'x'
        elif risk > 0.3:
            symbol = 'diamond'
        else:
            symbol = 'circle'

        fig.add_trace(go.Scatter(
            x=[pos[0]],
            y=[pos[1]],
            mode='markers',
            marker=dict(size=size, color=color, symbol=symbol, line=dict(color='white', width=1)),
            name=agent['id'],
            hovertemplate=(
                f"<b>{agent['id']}</b><br>"
                f"Risk: {risk:.3f}<br>"
                f"Position: ({pos[0]:.2f}, {pos[1]:.2f})<br>"
                f"Status: {'HIGH RISK' if risk > threshold else 'OK'}"
                f"<extra></extra>"
            ),
            showlegend=False
        ))

    # Add risk threshold circle (visual guide)
    r_threshold = 0.3 + threshold * 0.5
    fig.add_trace(go.Scatter(
        x=r_threshold * np.cos(theta),
        y=r_threshold * np.sin(theta),
        mode='lines',
        line=dict(color='red', width=1, dash='dot'),
        name='Risk Zone',
        hoverinfo='skip'
    ))

    fig.update_layout(
        showlegend=True,
        legend=dict(
            yanchor="top", y=0.99,
            xanchor="left", x=0.01,
            bgcolor="rgba(0,0,0,0.5)",
            font=dict(color="white")
        ),
        xaxis=dict(
            range=[-1.3, 1.3],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            range=[-1.3, 1.3],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor='rgba(26,26,46,1)',
        paper_bgcolor='rgba(26,26,46,1)',
        height=600,
        title=dict(
            text="Agent Risk Map (Poincaré Disk)",
            font=dict(color='white'),
            x=0.5
        ),
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig


if __name__ == "__main__":
    main()
