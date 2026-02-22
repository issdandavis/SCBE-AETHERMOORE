"""
Concept Blocks — Nodal Navigation Primitives
=============================================

Six domain-agnostic building blocks that work across flight, web, and
game navigation.  Each block wraps a single mathematical primitive and
exposes the same tick/reset/configure lifecycle.

Blocks
------
- **DECIDE**     : Behaviour tree execution (Layer 7)
- **PLAN**       : A* path-finding over any graph (Layer 6)
- **SENSE**      : Kalman filter state estimation (Layer 9)
- **STEER**      : PID continuous correction (Layer 8)
- **COORDINATE** : BFT swarm consensus (Layer 12)

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
]
