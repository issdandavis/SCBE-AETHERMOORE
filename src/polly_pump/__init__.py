"""Polly Pump scaffold: orientation packets, dual overlays, and zoom-anchor transitions."""

from .anchors import AnchorTransition, SymbolicLocator, ZoomAnchor
from .dual_overlay import (
    BallProjection,
    BallSpec,
    DualOverlayConfig,
    DualVerificationResult,
    LoopMetrics,
    NEG_ZERO_FREEZE,
    OverlayAction,
    project_dual_state,
    verify_dual_overlay,
)
from .packet import ModalityProfile, PumpPacket
from .stabilizer import PumpStabilizer

__all__ = [
    "AnchorTransition",
    "BallProjection",
    "BallSpec",
    "DualOverlayConfig",
    "DualVerificationResult",
    "LoopMetrics",
    "ModalityProfile",
    "NEG_ZERO_FREEZE",
    "OverlayAction",
    "PumpPacket",
    "PumpStabilizer",
    "SymbolicLocator",
    "ZoomAnchor",
    "project_dual_state",
    "verify_dual_overlay",
]
