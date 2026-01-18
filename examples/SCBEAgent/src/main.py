"""
SCBE Agent - AgentCore Integration
==================================
An AI agent that provides access to the SCBE risk governance system.
Users can analyze contexts, check risk levels, and get decisions.
"""

import sys
import os

# Add the src folder to path so we can import SCBE
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import numpy as np
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

# Import the SCBE system
from scbe_cpse_unified import SCBESystem, SCBEConfig, Decision

# Initialize the app
app = BedrockAgentCoreApp()

# Initialize SCBE system globally
scbe_system = SCBESystem()


@tool
def analyze_risk(
    context_description: str,
    risk_level: str = "medium"
) -> dict:
    """
    Analyze a context and return SCBE risk assessment.
    
    Args:
        context_description: A description of the context to analyze
        risk_level: Hint about expected risk - 'low', 'medium', or 'high'
    
    Returns:
        Risk assessment with decision (ALLOW/QUARANTINE/DENY)
    """
    # Generate synthetic signals based on the context
    np.random.seed(hash(context_description) % 2**32)
    
    # Adjust signal generation based on risk hint
    if risk_level == "low":
        base_amp = 0.3
        noise = 0.1
    elif risk_level == "high":
        base_amp = 0.8
        noise = 0.4
    else:
        base_amp = 0.5
        noise = 0.2
    
    amplitudes = np.clip(np.random.rand(6) * base_amp + noise, 0, 1)
    phases = np.random.rand(6) * 2 * np.pi
    telemetry = np.sin(np.linspace(0, 4 * np.pi, 256)) + np.random.randn(256) * noise
    
    result = scbe_system.process_context(
        amplitudes=amplitudes,
        phases=phases,
        breathing_factor=1.0,
        phase_shift=0.0,
        telemetry_signal=telemetry
    )
    
    return {
        "context": context_description,
        "decision": result["decision"],
        "risk_score": round(result["risk_prime"], 4),
        "base_risk": round(result["risk_base"], 4),
        "coherence": {
            "spin": round(result["coherence"]["C_spin"], 4),
            "spectral": round(result["coherence"]["S_spec"], 4),
            "trust": round(result["coherence"]["tau_trust"], 4)
        },
        "hyperbolic_distance": round(result["d_star"], 4)
    }


@tool
def get_system_config() -> dict:
    """
    Get the current SCBE system configuration and thresholds.
    
    Returns:
        Current configuration parameters
    """
    cfg = scbe_system.cfg
    return {
        "dimensions": cfg.D,
        "realms": cfg.K,
        "thresholds": {
            "allow_below": cfg.theta1,
            "deny_above": cfg.theta2
        },
        "risk_weights": {
            "distance": cfg.w_d,
            "spin_coherence": cfg.w_c,
            "spectral_coherence": cfg.w_s,
            "trust": cfg.w_tau,
            "audio": cfg.w_a
        },
        "breathing_bounds": {
            "min": cfg.b_min,
            "max": cfg.b_max
        }
    }


@tool  
def explain_decision(decision: str) -> str:
    """
    Explain what an SCBE decision means.
    
    Args:
        decision: The decision to explain - ALLOW, QUARANTINE, or DENY
    
    Returns:
        Human-readable explanation
    """
    explanations = {
        "ALLOW": "✅ ALLOW: The context passed all risk checks. The risk score is below the first threshold (θ₁). Safe to proceed.",
        "QUARANTINE": "⚠️ QUARANTINE: The context has moderate risk. The score is between θ₁ and θ₂. Flagged for human review or additional verification.",
        "DENY": "🚫 DENY: The context exceeds acceptable risk levels. The score is above θ₂. Action should be blocked."
    }
    return explanations.get(decision.upper(), f"Unknown decision: {decision}")


# Create the agent with tools
model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")

agent = Agent(
    model=model,
    tools=[analyze_risk, get_system_config, explain_decision],
    system_prompt="""You are the SCBE Risk Governance Agent. You help users understand and use the 
Spectral Context-Bound Encryption (SCBE) system for risk assessment.

SCBE uses a 14-layer hyperbolic geometry pipeline to analyze contexts and make risk-based decisions:
- ALLOW: Safe to proceed
- QUARANTINE: Needs review  
- DENY: Block the action

You have access to tools to:
1. analyze_risk - Analyze any context and get a risk decision
2. get_system_config - Show current system configuration
3. explain_decision - Explain what ALLOW/QUARANTINE/DENY means

Be helpful and explain results in simple terms. When users describe a scenario, 
use analyze_risk to assess it and explain the outcome."""
)


@app.entrypoint
async def invoke(payload: dict) -> dict:
    """Main entrypoint for the agent."""
    prompt = payload.get("prompt", "Hello")
    
    # Run the agent
    response = agent(prompt)
    
    return {
        "response": str(response)
    }
