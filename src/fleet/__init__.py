"""
fleet — Multi-agent orchestration for SCBE-AETHERMOORE.

Public API from this package:

  ModelProvider, ModelConfig, ModelNode, NodeBundle, ModelMatrix
  Switchboard, NoticeBoard, OctoArmor, TrainingFlywheel

Quick start::

    from src.fleet import ModelMatrix, OctoArmor

    matrix = ModelMatrix.create_default_scbe_matrix()
    armor = OctoArmor()
    print(armor.diagnostics())
"""

from src.fleet.model_matrix import (
    ModelProvider,
    ModelConfig,
    ModelNode,
    NodeBundle,
    ConversationPhoton,
    TunnelState,
    ModelMatrix,
    TONGUE_NAMES,
    TONGUE_ROLES,
)

from src.fleet.switchboard import (
    Switchboard,
    NoticeBoard,
    TaskType,
    CostTier,
    TaskPriority,
    classify_task,
)

from src.fleet.octo_armor import (
    OctoArmor,
    Tentacle,
    TentacleConfig,
    PollyLog,
    TokenizerGateway,
    hydra_ask,
    list_free_models,
    tentacle_dashboard,
    TENTACLE_REGISTRY,
)

from src.fleet.training_flywheel import TrainingFlywheel

__all__ = [
    # Model Matrix
    "ModelProvider",
    "ModelConfig",
    "ModelNode",
    "NodeBundle",
    "ConversationPhoton",
    "TunnelState",
    "ModelMatrix",
    "TONGUE_NAMES",
    "TONGUE_ROLES",
    # Switchboard
    "Switchboard",
    "NoticeBoard",
    "TaskType",
    "CostTier",
    "TaskPriority",
    "classify_task",
    # OctoArmor
    "OctoArmor",
    "Tentacle",
    "TentacleConfig",
    "PollyLog",
    "TrainingFlywheel",
    "TokenizerGateway",
    "hydra_ask",
    "list_free_models",
    "tentacle_dashboard",
    "TENTACLE_REGISTRY",
]
