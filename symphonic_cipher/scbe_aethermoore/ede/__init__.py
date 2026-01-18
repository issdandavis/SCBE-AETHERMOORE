"""
EDE - Entropic Defense Engine

Information-theoretic security via exponential expansion.

Components:
- SpiralRing-64: Deterministic entropic expansion ring
- EDE Protocol: Zero-latency Mars-ready communication
- Chemistry Agent: Immune system-inspired threat response

Key Features:
- Quantum-Resistant: Based on lattice-hard problems
- Zero-Latency: No handshakes needed (pre-shared keys + timestamps)
- Physics-Ready: Accounts for light delay and time dilation
- Self-Healing: Chemical equilibrium-based recovery

Usage:
    # Mars communication
    from symphonic_cipher.scbe_aethermoore.ede import (
        MarsLink, EDEStation, quick_mars_encode, quick_mars_decode
    )

    link = MarsLink.establish(shared_seed)
    msg, decoded, delay = link.simulate_earth_to_mars(b"Hello Mars!")

    # Threat defense
    from symphonic_cipher.scbe_aethermoore.ede import (
        ChemistryAgent, run_threat_simulation
    )

    agent = ChemistryAgent("defender")
    agent.set_threat_level(7)
    processed, blocked, energy = agent.process_input(suspicious_value)

Document ID: EDE-MAIN-2026-001
Version: 1.0.0
"""

# SpiralRing-64
from .spiral_ring import (
    # Core
    SpiralRing,
    SpiralPosition,
    RingConfig,
    RingState,
    SynchronizedRingPair,

    # Stream
    create_entropy_stream,

    # Constants
    RING_SIZE,
    EXPANSION_RATE,
    TIME_QUANTUM,
    SPIRAL_PHI,
    SPIRAL_R,
    SPIRAL_TWIST,
    LIGHT_SPEED,
    MARS_DISTANCE_MIN,
    MARS_DISTANCE_MAX,
    MARS_LIGHT_TIME_MIN,
    MARS_LIGHT_TIME_MAX,

    # Utilities
    calculate_light_delay,
    mars_light_delay,
)

# EDE Protocol
from .ede_protocol import (
    # Protocol
    EDEHeader,
    EDEMessage,
    EDEStation,
    MessageType,
    PROTOCOL_VERSION,
    HEADER_SIZE,
    MAC_SIZE,

    # Mars Link
    MarsLink,

    # Error Detection
    add_error_detection,
    verify_error_detection,

    # Time Dilation
    lorentz_factor,
    apply_time_dilation,

    # Quick Functions
    quick_mars_encode,
    quick_mars_decode,
)

# Chemistry Agent
from .chemistry_agent import (
    # Core
    ChemistryAgent,
    AgentState,
    ThreatType,

    # Energy Model
    squared_energy,
    reaction_rate,

    # Defense
    ray_refraction,
    harmonic_sink,

    # Healing
    self_heal,
    equilibrium_force,

    # Wave Simulation
    Unit,
    WaveSimulation,

    # Constants
    THREAT_LEVEL_MIN,
    THREAT_LEVEL_MAX,
    DEFAULT_THREAT_LEVEL,
    REFRACTION_BASE,
    ANTIBODY_EFFICIENCY_BASE,

    # Quick Functions
    quick_defense_check,
    run_threat_simulation,
)

__all__ = [
    # SpiralRing-64
    "SpiralRing",
    "SpiralPosition",
    "RingConfig",
    "RingState",
    "SynchronizedRingPair",
    "create_entropy_stream",
    "RING_SIZE",
    "EXPANSION_RATE",
    "TIME_QUANTUM",
    "SPIRAL_PHI",
    "SPIRAL_R",
    "SPIRAL_TWIST",
    "LIGHT_SPEED",
    "MARS_DISTANCE_MIN",
    "MARS_DISTANCE_MAX",
    "MARS_LIGHT_TIME_MIN",
    "MARS_LIGHT_TIME_MAX",
    "calculate_light_delay",
    "mars_light_delay",

    # EDE Protocol
    "EDEHeader",
    "EDEMessage",
    "EDEStation",
    "MessageType",
    "PROTOCOL_VERSION",
    "HEADER_SIZE",
    "MAC_SIZE",
    "MarsLink",
    "add_error_detection",
    "verify_error_detection",
    "lorentz_factor",
    "apply_time_dilation",
    "quick_mars_encode",
    "quick_mars_decode",

    # Chemistry Agent
    "ChemistryAgent",
    "AgentState",
    "ThreatType",
    "squared_energy",
    "reaction_rate",
    "ray_refraction",
    "harmonic_sink",
    "self_heal",
    "equilibrium_force",
    "Unit",
    "WaveSimulation",
    "THREAT_LEVEL_MIN",
    "THREAT_LEVEL_MAX",
    "DEFAULT_THREAT_LEVEL",
    "REFRACTION_BASE",
    "ANTIBODY_EFFICIENCY_BASE",
    "quick_defense_check",
    "run_threat_simulation",
]

__version__ = "1.0.0"
__author__ = "SCBE-AETHERMOORE Team"
