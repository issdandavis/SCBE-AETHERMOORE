"""
SCBE Security Module

Contains security patches and hardening utilities.
"""

from . import protobuf_patch
from .decision_envelope_predicate import (
    ActionState,
    EnvelopePredicateResult,
    ResourceState,
    TargetRef,
    evaluate_action_dict_inside_envelope,
    evaluate_action_inside_envelope,
)

__all__ = [
    "protobuf_patch",
    "ActionState",
    "EnvelopePredicateResult",
    "ResourceState",
    "TargetRef",
    "evaluate_action_inside_envelope",
    "evaluate_action_dict_inside_envelope",
]
