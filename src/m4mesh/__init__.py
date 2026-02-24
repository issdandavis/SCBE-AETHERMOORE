"""M4 Mesh package: deterministic multi-nodal multi-modal pipeline primitives."""

from .manifest import FluxManifest

# Optional torch-backed modules.
try:
    from .mesh_graph import MeshOps, build_mesh_ops_grid2d
    from .scbe_graph import build_phdm_mesh_ops
    from .cvl import BlockLayout, CVLFuser
    from .geometry import BlockGate, tanh_ball_projection, blockwise_tanh_ball_projection
    from .tie_kb import TIEKB, retrieve_tie
    from .wave import damped_wave
    from .smear import smear
    from .pipeline import M4Subsystem
    from .canonical_state import CanonicalState, validate_canonical_state
    from .canonical_bridge import run_governance_pipeline
except ImportError:  # pragma: no cover - allows environments without torch
    MeshOps = None
    build_mesh_ops_grid2d = None
    build_phdm_mesh_ops = None
    BlockLayout = None
    CVLFuser = None
    BlockGate = None
    tanh_ball_projection = None
    blockwise_tanh_ball_projection = None
    TIEKB = None
    retrieve_tie = None
    damped_wave = None
    smear = None
    M4Subsystem = None
    CanonicalState = None
    validate_canonical_state = None
    run_governance_pipeline = None

__all__ = [
    "FluxManifest",
    "MeshOps",
    "build_mesh_ops_grid2d",
    "build_phdm_mesh_ops",
    "BlockLayout",
    "CVLFuser",
    "BlockGate",
    "tanh_ball_projection",
    "blockwise_tanh_ball_projection",
    "TIEKB",
    "retrieve_tie",
    "damped_wave",
    "smear",
    "M4Subsystem",
    "CanonicalState",
    "validate_canonical_state",
    "run_governance_pipeline",
]
