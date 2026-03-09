"""
Concept Blocks — Nodal Navigation Primitives (Mr. Potato Head Architecture)
===========================================================================

Seven domain-agnostic building blocks that work across flight, web, and
game navigation.  Each block wraps a single mathematical primitive and
exposes the same tick/reset/configure lifecycle.

Like Mr. Potato Head, blocks are snap-on sense organs that attach to
sockets on an agent body (``PotatoHead``).  Each socket is gated by
Sacred Egg ring predicates and Sacred Tongue phase affinity.

Blocks (Sense Organs)
---------------------
- **DECIDE**     : Behaviour tree execution (Layer 7)
- **PLAN**       : A* path-finding over any graph (Layer 6)
- **SENSE**      : Kalman filter state estimation (Layer 9)
- **STEER**      : PID continuous correction (Layer 8)
- **COORDINATE** : BFT swarm consensus (Layer 12)
- **PROXIMITY**  : Decimal-drift 6th sense (Layer 14)

Body
----
- ``PotatoHead`` : agent body with typed sockets
- ``SocketSpec`` : socket definition (layer, ring, tongue)
- ``EggRing``    : Sacred Egg access control tiers

Shared
------
- ``ConceptBlock`` : abstract base class
- ``BlockResult``  : tick return value
- ``BlockStatus``  : SUCCESS / FAILURE / RUNNING
- ``TelemetryRecord``, ``TelemetryLog`` : unified telemetry
"""

from .base import BlockResult, BlockStatus, ConceptBlock
from .telemetry import TelemetryLog, TelemetryRecord

from .decide import (
    Action,
    Blackboard,
    Condition,
    DecideBlock,
    NodeStatus,
    Selector,
    Sequence,
    TreeNode,
)
from .plan import (
    GraphAdapter,
    GridAdapter,
    PlanBlock,
    URLGraphAdapter,
    a_star_search,
)
from .sense import (
    MultiDimKalmanFilter,
    SenseBlock,
    SimpleKalmanFilter,
)
from .steer import (
    PIDController,
    SteerBlock,
)
from .coordinate import (
    BFTConsensus,
    CoordinateBlock,
    SwarmNode,
)
from .proximity import (
    DriftShadowBuffer,
    ProximityBlock,
    ProximityLevel,
    ProximityReading,
    compute_drift_distance,
)
from .socket import (
    AttachmentRecord,
    EggRing,
    PotatoHead,
    SocketSpec,
)
from .aperiodic_phase import (
    AperiodicPhaseBlock,
    AperiodicPhaseController,
    GateVector,
    PenroseInterval,
    fibonacci_word,
    fibonacci_word_char,
    penrose_intervals,
)

__all__ = [
    # Base
    "ConceptBlock", "BlockResult", "BlockStatus",
    "TelemetryRecord", "TelemetryLog",
    # DECIDE
    "DecideBlock", "TreeNode", "Action", "Condition",
    "Sequence", "Selector", "Blackboard", "NodeStatus",
    # PLAN
    "PlanBlock", "GraphAdapter", "GridAdapter", "URLGraphAdapter", "a_star_search",
    # SENSE
    "SenseBlock", "SimpleKalmanFilter", "MultiDimKalmanFilter",
    # STEER
    "SteerBlock", "PIDController",
    # COORDINATE
    "CoordinateBlock", "BFTConsensus", "SwarmNode",
    # PROXIMITY (6th Sense)
    "ProximityBlock", "ProximityLevel", "ProximityReading",
    "DriftShadowBuffer", "compute_drift_distance",
    # SOCKET (Mr. Potato Head Body)
    "PotatoHead", "SocketSpec", "EggRing", "AttachmentRecord",
    # APERIODIC PHASE (Controlled Chaos)
    "AperiodicPhaseBlock", "AperiodicPhaseController", "GateVector",
    "PenroseInterval", "fibonacci_word", "fibonacci_word_char", "penrose_intervals",
]
