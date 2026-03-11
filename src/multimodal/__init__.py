"""
SCBE Multimodal Training System
=================================

Matrix-first multimodal alignment with SCBE governance integration.

Modules:
    encoders — Per-modality encoders (text, image, audio, code, state)
    multimodal_matrix — Trainable alignment matrix A [B, M, M]
    fusion — Matrix-weighted and gated fusion strategies
    losses — Contrastive + conflict + harmonic governance losses
    model — End-to-end SCBEMultiModalModel
    trainer — Training loop with phase scheduling

Usage:
    from multimodal.model import SCBEMultiModalModel
    from multimodal.trainer import MultiModalTrainer, TrainConfig

    model = SCBEMultiModalModel(d_model=512)
    trainer = MultiModalTrainer(model, TrainConfig(epochs=10))
    trainer.train(dataloader)
"""

from .encoders import (
    SimpleAudioEncoder,
    SimpleCodeEncoder,
    SimpleImageEncoder,
    SimpleTextEncoder,
    StateEncoder,
)
from .fusion import GatedFusion, MatrixWeightedFusion
from .losses import clip_contrastive_loss, combined_loss, conflict_penalty, harmonic_governance_loss
from .model import MultiModalOutput, SCBEMultiModalModel
from .multimodal_matrix import MultiModalMatrix
from .trainer import MultiModalTrainer, TrainConfig, TrainMetrics

__all__ = [
    # Encoders
    "SimpleTextEncoder",
    "SimpleImageEncoder",
    "SimpleAudioEncoder",
    "SimpleCodeEncoder",
    "StateEncoder",
    # Matrix
    "MultiModalMatrix",
    # Fusion
    "MatrixWeightedFusion",
    "GatedFusion",
    # Losses
    "clip_contrastive_loss",
    "conflict_penalty",
    "harmonic_governance_loss",
    "combined_loss",
    # Model
    "SCBEMultiModalModel",
    "MultiModalOutput",
    # Trainer
    "MultiModalTrainer",
    "TrainConfig",
    "TrainMetrics",
]
