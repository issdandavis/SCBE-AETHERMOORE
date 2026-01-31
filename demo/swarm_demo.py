"""
SCBE Swarm Coordinator - Interactive Demo
Visualizes 6 Sacred Tongue agents in a Poincaré ball with decimal drift detection.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import requests
import json
from dataclasses import dataclass
from typing import Tuple
import time

# ============================================================================
# Constants
# ============================================================================

PYTHAGOREAN_COMMA = 1.0136432648  # 531441:524288
GOLDEN_RATIO = 1.618033988749895

AGENTS = {
    "KO": {"name": "Orchestrator", "phase": 0, "color": "#FF6B6B", "role": "Control flow"},
    "AV": {"name": "Transport", "phase": 60, "color": "#4ECDC4", "role": "I/O operations"},
    "RU": {"name": "Policy", "phase": 120, "color": "#45B7D1", "role": "Rule enforcement"},
    "CA": {"name": "Compute", "phase": 180, "color": "#96CEB4", "role": "Core computation"},
    "UM": {"name": "Security", "phase": 240, "color": "#FFEAA7", "role": "Threat detection"},
    "DR": {"name": "Schema", "phase": 300, "color": "#DDA0DD", "role": "Validation"},
}

# ============================================================================
# Poincaré Ball Math
# ============================================================================

def poincare_position(phase_deg: float, radius: float = 0.5, drift: float = 0.0) -> Tuple[float, float, float]:
    """Calculate position in Poincaré ball based on phase and drift."""
    phase_rad = np.radians(phase_deg)
    # Apply decimal drift to radius
    adjusted_radius = min(0.95, radius * (PYTHAGOREAN_COMMA ** drift))

    x = adjusted_radius * np.cos(phase_rad)
    y = adjusted_radius * np.sin(phase_rad)
    z = drift * 0.3  # Drift moves agent "up" in the ball

    return (x, y, z)

def hyperbolic_distance(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Calculate hyperbolic distance in Poincaré ball."""
    p1, p2 = np.array(p1), np.array(p2)
    norm1_sq = np.sum(p1**2)
    norm2_sq = np.sum(p2**2)
    diff_sq = np.sum((p1 - p2)**2)

    if norm1_sq >= 1 or norm2_sq >= 1:
        return float('inf')

    delta = 2 * diff_sq / ((1 - norm1_sq) * (1 - norm2_sq))
    return np.arccosh(1 + delta)

def harmonic_wall_cost(distance: float) -> float:
    """Calculate harmonic wall cost: H(d) = exp(d²)"""
    return np.exp(distance ** 2)

def security_gradient(x: float, y: float, z: float, security_level: float) -> float:
    """Calculate security repulsive force at position."""
    distance_from_center = np.sqrt(x**2 + y**2 + z**2)
    return -security_level * np.exp(distance_from_center * 2) * 0.1

# ============================================================================
# Visualization
# ============================================================================

def create_poincare_ball(agents_state: dict, show_drift_lines: bool = True) -> go.Figure:
    """Create 3D Poincaré ball visualization with agents."""
    fig = go.Figure()

    # Draw the ball boundary (unit sphere wireframe)
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 20)
    x_sphere = np.outer(np.cos(u), np.sin(v))
    y_sphere = np.outer(np.sin(u), np.sin(v))
    z_sphere = np.outer(np.ones(np.size(u)), np.cos(v))

    fig.add_trace(go.Surface(
        x=x_sphere, y=y_sphere, z=z_sphere,
        opacity=0.1,
        colorscale=[[0, 'rgba(100,100,100,0.1)'], [1, 'rgba(100,100,100,0.1)']],
        showscale=False,
        name='Poincaré Boundary'
    ))

    # Draw agents
    for code, state in agents_state.items():
        agent_info = AGENTS[code]
        pos = state['position']

        # Agent marker
        fig.add_trace(go.Scatter3d(
            x=[pos[0]], y=[pos[1]], z=[pos[2]],
            mode='markers+text',
            marker=dict(size=15, color=agent_info['color'], symbol='diamond'),
            text=[code],
            textposition='top center',
            name=f"{code}: {agent_info['name']}"
        ))

        # Drift line from origin
        if show_drift_lines and state['drift'] > 0.1:
            origin_pos = poincare_position(agent_info['phase'], 0.5, 0)
            fig.add_trace(go.Scatter3d(
                x=[origin_pos[0], pos[0]],
                y=[origin_pos[1], pos[1]],
                z=[origin_pos[2], pos[2]],
                mode='lines',
                line=dict(color=agent_info['color'], width=2, dash='dash'),
                name=f"{code} drift path",
                showlegend=False
            ))

    # Draw consensus lines between agents
    codes = list(agents_state.keys())
    for i, code1 in enumerate(codes):
        for code2 in codes[i+1:]:
            p1 = agents_state[code1]['position']
            p2 = agents_state[code2]['position']
            dist = hyperbolic_distance(p1, p2)

            # Color based on distance (green=close, red=far)
            if dist < 1:
                color = 'rgba(0,255,0,0.3)'
            elif dist < 2:
                color = 'rgba(255,255,0,0.3)'
            else:
                color = 'rgba(255,0,0,0.3)'

            fig.add_trace(go.Scatter3d(
                x=[p1[0], p2[0]],
                y=[p1[1], p2[1]],
                z=[p1[2], p2[2]],
                mode='lines',
                line=dict(color=color, width=1),
                showlegend=False
            ))

    fig.update_layout(
        title="Poincaré Ball - Agent Positions",
        scene=dict(
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Drift (Z)",
            aspectmode='cube',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        ),
        showlegend=True,
        legend=dict(x=0, y=1),
        height=600
    )

    return fig

def create_drift_gauge(drift_values: dict) -> go.Figure:
    """Create gauge chart for decimal drift."""
    fig = go.Figure()

    for i, (code, drift) in enumerate(drift_values.items()):
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=drift,
            domain={'row': 0, 'column': i},
            title={'text': code},
            gauge={
                'axis': {'range': [0, 3]},
                'bar': {'color': AGENTS[code]['color']},
                'steps': [
                    {'range': [0, 0.3], 'color': "lightgreen"},
                    {'range': [0.3, 0.6], 'color': "yellow"},
                    {'range': [0.6, 1], 'color': "orange"},
                    {'range': [1, 3], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 2},
                    'thickness': 0.75,
                    'value': 0.6
                }
            }
        ))

    fig.update_layout(
        grid={'rows': 1, 'columns': 6, 'pattern': "independent"},
        height=200,
        margin=dict(t=50, b=20)
    )

    return fig

def create_security_heatmap(security_level: float) -> go.Figure:
    """Create security gradient field heatmap."""
    x = np.linspace(-1, 1, 50)
    y = np.linspace(-1, 1, 50)
    X, Y = np.meshgrid(x, y)

    # Calculate security gradient (repulsive force)
    R = np.sqrt(X**2 + Y**2)
    Z = -security_level * np.exp(R * 2) * 0.1

    # Mask outside unit circle
    Z[R > 1] = np.nan

    fig = go.Figure(data=go.Heatmap(
        z=Z,
        x=x,
        y=y,
        colorscale='RdYlGn_r',
        colorbar=dict(title="Repulsive Force")
    ))

    # Add unit circle
    theta = np.linspace(0, 2*np.pi, 100)
    fig.add_trace(go.Scatter(
        x=np.cos(theta),
        y=np.sin(theta),
        mode='lines',
        line=dict(color='black', width=2),
        name='Boundary'
    ))

    fig.update_layout(
        title=f"Security Gradient Field (Level: {security_level:.2f})",
        xaxis_title="X",
        yaxis_title="Y",
        height=400,
        yaxis=dict(scaleanchor="x", scaleratio=1)
    )

    return fig

# ============================================================================
# Governance Engine (Embedded for Streamlit Cloud)
# ============================================================================

POLICIES = [
    {"id": "POL-001", "name": "High Value Transaction", "threshold": 10000},
    {"id": "POL-002", "name": "Confidential Data Access", "ai_restricted": True},
    {"id": "POL-003", "name": "Auto-Approval Limits", "ai_limit": 5000},
    {"id": "POL-004", "name": "Destructive Operations", "blocked_intents": ["delete", "destroy", "purge"]},
    {"id": "POL-005", "name": "Low Trust Actor", "trust_threshold": 0.3},
]

def simulate_governance(actor_id: str, actor_type: str, resource_type: str,
                        intent: str, trust_score: float = 0.5, value_usd: float = 0,
                        classification: str = "internal"):
    """Simulate governance decision using embedded engine."""
    import hashlib

    # Calculate risk using hyperbolic distance
    actor_hash = hashlib.sha256(f"{actor_id}{actor_type}".encode()).digest()
    resource_hash = hashlib.sha256(f"{resource_type}{intent}".encode()).digest()

    # Map to Poincaré ball positions
    ax, ay, az = (actor_hash[0]/255 - 0.5) * 0.7, (actor_hash[1]/255 - 0.5) * 0.7, (actor_hash[2]/255 - 0.5) * 0.7
    rx, ry, rz = (resource_hash[0]/255 - 0.5) * 0.7, (resource_hash[1]/255 - 0.5) * 0.7, (resource_hash[2]/255 - 0.5) * 0.7

    distance = hyperbolic_distance((ax, ay, az), (rx, ry, rz))
    base_risk = min(1, distance / 3)

    # Apply policy modifiers
    policy_ids = []
    rationales = []
    decision = "ALLOW"
    risk_modifier = 0

    # POL-001: High value
    if value_usd > 50000:
        decision = "ESCALATE"
        policy_ids.append("POL-001")
        rationales.append(f"Transaction ${value_usd} exceeds $50,000")
        risk_modifier += 0.3
    elif value_usd > 10000:
        policy_ids.append("POL-001")
        rationales.append(f"Transaction ${value_usd} requires scrutiny")
        risk_modifier += 0.15

    # POL-002: AI + restricted
    if classification == "restricted" and actor_type == "ai":
        decision = "DENY"
        policy_ids.append("POL-002")
        rationales.append("AI cannot access restricted resources")
        risk_modifier += 0.5

    # POL-003: AI auto-approve limits
    if intent == "auto_approve" and actor_type == "ai" and value_usd > 5000:
        decision = "ESCALATE"
        policy_ids.append("POL-003")
        rationales.append(f"AI cannot auto-approve >${value_usd}")
        risk_modifier += 0.25

    # POL-004: Destructive operations
    if intent in ["delete", "destroy", "purge", "remove"]:
        if actor_type == "ai":
            decision = "DENY"
            policy_ids.append("POL-004")
            rationales.append("AI cannot perform destructive operations")
            risk_modifier += 0.6
        else:
            decision = "ESCALATE"
            policy_ids.append("POL-004")
            rationales.append("Destructive operation requires confirmation")
            risk_modifier += 0.35

    # POL-005: Low trust
    if trust_score < 0.3:
        decision = "QUARANTINE"
        policy_ids.append("POL-005")
        rationales.append(f"Trust score {trust_score:.2f} below threshold")
        risk_modifier += 0.5

    # Final risk calculation
    risk_score = min(1, base_risk * (1.5 - trust_score) + risk_modifier)
    harmonic_cost = harmonic_wall_cost(risk_score * 3)

    # Override decision based on risk if no policy triggered
    if not policy_ids:
        if risk_score > 0.8:
            decision = "DENY"
            rationales.append(f"Risk {risk_score:.3f} exceeds threshold")
        elif risk_score > 0.6:
            decision = "ESCALATE"
            rationales.append(f"Risk {risk_score:.3f} requires review")
        else:
            rationales.append(f"Risk {risk_score:.3f} acceptable")

    return {
        "decision": decision,
        "risk_score": risk_score,
        "harmonic_cost": harmonic_cost,
        "rationale": "; ".join(rationales) if rationales else "Low risk operation",
        "policy_ids": policy_ids
    }

def call_governance_api(actor_id: str, actor_type: str, resource_type: str,
                        intent: str, trust_score: float = 0.5, value_usd: float = 0):
    """Try local API first, fall back to embedded simulation."""
    try:
        response = requests.post(
            "http://localhost:8080/v1/govern",
            json={
                "actor": {"id": actor_id, "type": actor_type, "trust_score": trust_score},
                "resource": {"type": resource_type, "id": f"{resource_type}-001", "value_usd": value_usd},
                "intent": intent,
                "nonce": str(time.time_ns())
            },
            timeout=2
        )
        return response.json()
    except:
        # Fall back to embedded simulation for Streamlit Cloud
        return simulate_governance(actor_id, actor_type, resource_type, intent, trust_score, value_usd)

# ============================================================================
# Main App
# ============================================================================

def main():
    st.set_page_config(
        page_title="SCBE Swarm Coordinator",
        page_icon="🛸",
        layout="wide"
    )

    st.title("🛸 SCBE Swarm Coordinator")
    st.markdown("*Hyperbolic geometry-based AI governance with decimal drift detection*")

    # Sidebar controls
    st.sidebar.header("Swarm Controls")

    # Agent drift sliders
    st.sidebar.subheader("Agent Drift")
    drift_values = {}
    for code in AGENTS:
        drift_values[code] = st.sidebar.slider(
            f"{code} ({AGENTS[code]['name']})",
            0.0, 3.0, 0.0, 0.1,
            help=AGENTS[code]['role']
        )

    # Security level
    st.sidebar.subheader("Security")
    security_level = st.sidebar.slider("Security Gradient", 0.0, 1.0, 0.5, 0.1)

    # Calculate agent states
    agents_state = {}
    for code, info in AGENTS.items():
        drift = drift_values[code]
        pos = poincare_position(info['phase'], 0.5, drift)
        cost = harmonic_wall_cost(drift)
        agents_state[code] = {
            'position': pos,
            'drift': drift,
            'harmonic_cost': cost,
            'status': 'NORMAL' if drift < 0.3 else ('WARNING' if drift < 0.6 else 'CRITICAL')
        }

    # Main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # 3D Poincaré ball
        st.plotly_chart(create_poincare_ball(agents_state), use_container_width=True)

    with col2:
        # Agent status table
        st.subheader("Agent Status")
        for code, state in agents_state.items():
            status_color = {"NORMAL": "🟢", "WARNING": "🟡", "CRITICAL": "🔴"}[state['status']]
            st.markdown(f"""
            **{status_color} {code}** - {AGENTS[code]['name']}
            Drift: `{state['drift']:.2f}` | Cost: `{state['harmonic_cost']:.1f}`
            """)

        # BFT Consensus check
        st.subheader("BFT Consensus")
        normal_agents = sum(1 for s in agents_state.values() if s['status'] == 'NORMAL')
        quorum = 4  # 2f+1 where f=1
        if normal_agents >= quorum:
            st.success(f"✅ Quorum achieved: {normal_agents}/6 agents normal")
        else:
            st.error(f"❌ Quorum failed: {normal_agents}/6 agents normal (need {quorum})")

    # Drift gauges
    st.subheader("Decimal Drift Detection")
    st.plotly_chart(create_drift_gauge(drift_values), use_container_width=True)

    # Security gradient
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(create_security_heatmap(security_level), use_container_width=True)

    with col4:
        st.subheader("Governance API Test")

        with st.form("governance_test"):
            actor_type = st.selectbox("Actor Type", ["human", "ai", "system", "external"])
            intent = st.selectbox("Intent", ["read", "write", "delete", "auto_approve"])
            resource_type = st.selectbox("Resource", ["document", "contract", "database", "api"])
            trust_score = st.slider("Trust Score", 0.0, 1.0, 0.7)
            value_usd = st.number_input("Value (USD)", 0, 100000, 0, 1000)

            submitted = st.form_submit_button("Test Governance Decision")

            if submitted:
                result = call_governance_api(
                    f"{actor_type}-agent",
                    actor_type,
                    resource_type,
                    intent,
                    trust_score,
                    value_usd
                )

                decision = result.get('decision', 'ERROR')
                color = {
                    'ALLOW': 'green',
                    'DENY': 'red',
                    'ESCALATE': 'orange',
                    'QUARANTINE': 'purple'
                }.get(decision, 'gray')

                st.markdown(f"### Decision: :{color}[{decision}]")
                st.write(f"**Rationale:** {result.get('rationale', 'N/A')}")
                st.write(f"**Risk Score:** {result.get('risk_score', 'N/A')}")
                st.write(f"**Harmonic Cost:** {result.get('harmonic_cost', 'N/A')}")

    # Footer
    st.markdown("---")
    st.markdown("""
    **Math Behind the Magic:**
    - **Poincaré Ball:** Hyperbolic space where boundary = infinite distance
    - **Decimal Drift:** Pythagorean comma (1.0136...) creates non-repeating spiral
    - **Harmonic Wall:** H(d) = exp(d²) - exponential cost for adversarial actions
    - **BFT Consensus:** 4-of-6 agents must agree (tolerates 2 failures)
    """)

if __name__ == "__main__":
    main()
