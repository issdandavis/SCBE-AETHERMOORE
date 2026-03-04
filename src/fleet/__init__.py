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

__all__ = [
    "ModelProvider",
    "ModelConfig",
    "ModelNode",
    "NodeBundle",
    "ModelMatrix",
    "TONGUE_NAMES",
    "TONGUE_ROLES",
]
