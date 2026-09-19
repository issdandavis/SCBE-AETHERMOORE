"""
fleet — Multi-agent orchestration for SCBE-AETHERMOORE.

Public API from this package:

  ModelProvider, ModelConfig, ModelNode, NodeBundle, ModelMatrix

Quick start::

    from src.fleet import ModelMatrix

    matrix = ModelMatrix.create_default_scbe_matrix()
    status = matrix.get_matrix_status()
"""

from src.fleet.model_matrix import (
    ModelProvider,
    ModelConfig,
    ModelNode,
    NodeBundle,
    ModelMatrix,
    TONGUE_NAMES,
    TONGUE_ROLES,
)
from src.fleet.composition_coordinator import (
    CoordinationPolicy,
    FleetComposition,
    FleetCompositionCoordinator,
    FleetMember,
    FleetTask,
    NetworkCondition,
    composition_geometry,
    simulate_mission,
    task_fit,
    transition_measure,
)
from src.fleet.bijective_frequency_transport import (
    BijectiveTransportError,
    FrequencyLane,
    MultiplexedCommandBundle,
    PayloadRecovery,
    ProgramRecovery,
    bundle_metrics,
    encode_payload,
    encode_program,
    prove_lane_token_bijections,
    recover_payload,
    recover_program,
)

__all__ = [
    "ModelProvider",
    "ModelConfig",
    "ModelNode",
    "NodeBundle",
    "ModelMatrix",
    "TONGUE_NAMES",
    "TONGUE_ROLES",
    "CoordinationPolicy",
    "FleetComposition",
    "FleetCompositionCoordinator",
    "FleetMember",
    "FleetTask",
    "NetworkCondition",
    "composition_geometry",
    "simulate_mission",
    "task_fit",
    "transition_measure",
    "BijectiveTransportError",
    "FrequencyLane",
    "MultiplexedCommandBundle",
    "PayloadRecovery",
    "ProgramRecovery",
    "bundle_metrics",
    "encode_payload",
    "encode_program",
    "prove_lane_token_bijections",
    "recover_payload",
    "recover_program",
]
