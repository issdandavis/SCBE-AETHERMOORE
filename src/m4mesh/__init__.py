"""M4 Mesh package: deterministic multi-nodal multi-modal pipeline primitives."""

from .manifest import FluxManifest

# Optional torch-backed modules.
try:
    from .mesh_graph import MeshOps, build_mesh_ops_grid2d
    from .cvl import BlockLayout, CVLFuser
    from .geometry import BlockGate, tanh_ball_projection, blockwise_tanh_ball_projection
    from .tie_kb import TIEKB, retrieve_tie
    from .wave import damped_wave
    from .smear import smear
    from .pipeline import M4Subsystem
except ImportError:  # pragma: no cover - allows environments without torch
    MeshOps = None
    build_mesh_ops_grid2d = None
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

__all__ = [
    "FluxManifest",
    "MeshOps",
    "build_mesh_ops_grid2d",
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
]
