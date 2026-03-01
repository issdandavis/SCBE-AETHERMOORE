# Fibonacci Drift Tracker — Transversal Audio Verification
#
# Maps 14-layer governance outputs onto Fibonacci spiral paths,
# producing unique sonic/visual fingerprints as a BYPRODUCT of
# normal operations. Drift from expected spiral = anomaly.
#
# Patent: USPTO #63/961,403 (Pending)

from .tracker import FibonacciDriftTracker, SpiralPoint, DriftSignature, LayerSnapshot
from .sonifier import SpiralSonifier, AudioProof
from .transversal import TransversalEngine, TransversalMove, LayerBridge
from .decimal_paths import DecimalPathValidator, DriftPath, EpsilonDrift, UserInputEffect
from .binary_manifold import BinaryManifoldAnalyzer, BinaryManifold, LayerBitProfile

__all__ = [
    "FibonacciDriftTracker",
    "SpiralPoint",
    "DriftSignature",
    "LayerSnapshot",
    "SpiralSonifier",
    "AudioProof",
    "TransversalEngine",
    "TransversalMove",
    "LayerBridge",
    "DecimalPathValidator",
    "DriftPath",
    "EpsilonDrift",
    "UserInputEffect",
    "BinaryManifoldAnalyzer",
    "BinaryManifold",
    "LayerBitProfile",
]
