"""
video_lattice — Hyperbolic multi-lattice video coherence engine.

Uses Poincaré ball geometry to track temporal drift across video frames,
model perspective depth, and drive error-correction decisions.

Architecture:
  Each frame is embedded into N independent Poincaré balls (lattices),
  one per semantic axis (identity, motion, scene, color, depth, structure).
  Drift from the running lattice centroid drives correction triggers,
  exactly as session-centroid drift drives governance decisions in RuntimeGate.

Modules:
  poincare_lattice   — single Poincaré ball: embed, distance, centroid
  multi_lattice      — N-ball fleet with per-axis weights
  temporal_tracker   — per-frame drift tracking + error-recycling trigger
  perspective_map    — depth → radial position in Poincaré ball
  frame_corrector    — correction signal generator from drift vector
  pose_polygons      — hand/body landmark polygons → lattice vectors
  sketch_pad         — SVG/PNG pose sketch rendering API
  realtime_perception — multi-view input/depth uncertainty bridge
  vector_index      — local cosine search over multimodal embeddings
  tiny_engine       — compact pocket-dimension world/render state
  gpt_world         — GPT director + round-table multi-model coherence
"""
from .poincare_lattice import PoincareLattice
from .multi_lattice import MultiLattice, LatticeAxis
from .temporal_tracker import TemporalTracker, FrameState, IntentAnchor
from .perspective_map import PerspectiveMap, PerspectivePoint
from .frame_corrector import FrameCorrector, CorrectionSignal
from .pose_polygons import (
    BodyLandmark,
    HandLandmark,
    Landmark,
    body_polygon_features,
    hand_polygon_features,
)
from .sketch_pad import SketchPad, render_body_sketch, render_hand_sketch
from .pose_checker import PoseChecker, PoseCheckResult, PoseVerdict, ChainCheck
from .ue5_bridge import UE5Bridge, BridgeResponse, UE5BridgeError
from .realtime_perception import (
    CameraView,
    FusedLandmark,
    LandmarkObservation,
    MultiViewPerception,
    MultiViewState,
    ViewFrame,
    make_view_frame,
)
from .vector_index import LocalVectorIndex, SearchResult, VectorRecord, cosine_similarity, normalize_vector
from .tiny_engine import Entity, Sprite, Tile, TinyWorld, demo_world
from .gpt_world import WorldDirector, WorldDelta, WorldCommand, RoundTableDirector, RoundTableReport

__all__ = [
    "PoincareLattice",
    "MultiLattice",
    "LatticeAxis",
    "TemporalTracker",
    "FrameState",
    "IntentAnchor",
    "PerspectiveMap",
    "PerspectivePoint",
    "FrameCorrector",
    "CorrectionSignal",
    "Landmark",
    "HandLandmark",
    "BodyLandmark",
    "hand_polygon_features",
    "body_polygon_features",
    "SketchPad",
    "render_hand_sketch",
    "render_body_sketch",
    "PoseChecker",
    "PoseCheckResult",
    "PoseVerdict",
    "ChainCheck",
    "UE5Bridge",
    "BridgeResponse",
    "UE5BridgeError",
    "CameraView",
    "LandmarkObservation",
    "ViewFrame",
    "FusedLandmark",
    "MultiViewState",
    "MultiViewPerception",
    "make_view_frame",
    "VectorRecord",
    "SearchResult",
    "LocalVectorIndex",
    "normalize_vector",
    "cosine_similarity",
    "Tile",
    "Sprite",
    "Entity",
    "TinyWorld",
    "demo_world",
    "WorldDirector",
    "WorldDelta",
    "WorldCommand",
    "RoundTableDirector",
    "RoundTableReport",
]
