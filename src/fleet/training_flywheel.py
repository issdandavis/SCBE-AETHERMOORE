"""Training flywheel package for OctoArmor-generated observations."""

from __future__ import annotations

from src.fleet.octo_armor import TrainingFlywheel as _LegacyTrainingFlywheel


class TrainingFlywheel(_LegacyTrainingFlywheel):
    """Compatibility entry-point for the OctoArmor training pipeline.

    Keep this file as the canonical import path requested by system documentation.
    """

    pass


__all__ = ["TrainingFlywheel"]

