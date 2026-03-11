"""
SCBE Multimodal Trainer
========================

Training loop for the SCBE multimodal model.

Phase 1: freeze encoders for 1 epoch, train matrix + fusion head.
Phase 2: unfreeze all, reduce LR for encoders.

Supports:
- Contrastive alignment (text ↔ image)
- Conflict penalty (penalize disagreement)
- SCBE governance loss (harmonic wall cost)
- Gradient clipping + cosine annealing

@module multimodal/trainer
@layer Full pipeline
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from .losses import combined_loss
from .model import SCBEMultiModalModel

logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    """Training configuration."""

    # Optimiser
    lr: float = 1e-4
    encoder_lr: float = 1e-5
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0

    # Schedule
    epochs: int = 10
    warmup_epochs: int = 1
    freeze_encoders_epochs: int = 1

    # Loss weights
    contrastive_weight: float = 1.0
    conflict_weight: float = 0.5
    governance_weight: float = 0.1
    temperature: float = 0.07
    conflict_margin: float = 0.0

    # Logging
    log_interval: int = 50

    # Checkpointing
    save_dir: str = "checkpoints"
    save_every_epoch: bool = True


@dataclass
class TrainMetrics:
    """Metrics from a training epoch."""

    epoch: int
    avg_loss: float
    avg_contrastive: float
    avg_conflict: float
    avg_governance: float
    avg_coherence: float
    avg_drift: float
    duration_s: float
    steps: int


class MultiModalTrainer:
    """
    Trainer for SCBEMultiModalModel.

    Handles Phase 1 (frozen encoders) → Phase 2 (full fine-tuning)
    automatically based on epoch count.
    """

    def __init__(self, model: SCBEMultiModalModel, config: TrainConfig | None = None):
        self.model = model
        self.config = config or TrainConfig()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        # Build parameter groups
        self._setup_optimiser()

        # Scheduler
        self.scheduler = CosineAnnealingLR(
            self.optimizer,
            T_max=max(1, self.config.epochs - self.config.warmup_epochs),
        )

        self.global_step = 0
        self.history: list[TrainMetrics] = []

    def train_epoch(
        self,
        dataloader: Any,
        epoch: int,
    ) -> TrainMetrics:
        """
        Train one epoch.

        Args:
            dataloader: Iterable of batch dicts with modality tensors.
            epoch: Current epoch number (0-indexed).

        Returns:
            TrainMetrics for this epoch.
        """
        self.model.train()
        start = time.time()

        # Phase 1: freeze encoders
        if epoch < self.config.freeze_encoders_epochs:
            self._freeze_encoders()
        else:
            self._unfreeze_encoders()

        running = {"total": 0.0, "contrastive": 0.0, "conflict": 0.0, "governance": 0.0}
        running_coherence = 0.0
        running_drift = 0.0
        steps = 0

        for batch in dataloader:
            batch = {k: v.to(self.device) for k, v in batch.items()}

            # Forward
            output = self.model(batch)

            # Loss (requires at least text + image)
            if output.z_text is not None and output.z_image is not None:
                losses = combined_loss(
                    z_text=output.z_text,
                    z_image=output.z_image,
                    A=output.A,
                    contrastive_weight=self.config.contrastive_weight,
                    conflict_weight=self.config.conflict_weight,
                    governance_weight=self.config.governance_weight,
                    temperature=self.config.temperature,
                    conflict_margin=self.config.conflict_margin,
                )
            else:
                # Fallback: just conflict + governance
                from .losses import conflict_penalty, harmonic_governance_loss

                l_conflict = conflict_penalty(output.A, self.config.conflict_margin)
                l_governance = harmonic_governance_loss(output.A)
                losses = {
                    "total": l_conflict + l_governance,
                    "contrastive": torch.tensor(0.0),
                    "conflict": l_conflict,
                    "governance": l_governance,
                }

            # Backward
            self.optimizer.zero_grad()
            losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
            self.optimizer.step()

            # Accumulate
            for k in running:
                running[k] += losses[k].item()
            if output.coherence is not None:
                running_coherence += output.coherence.mean().item()
            if output.drift is not None:
                running_drift += output.drift.mean().item()

            steps += 1
            self.global_step += 1

            if steps % self.config.log_interval == 0:
                logger.info(
                    f"[epoch={epoch} step={steps}] "
                    f"loss={running['total'] / steps:.4f} "
                    f"coherence={running_coherence / steps:.4f}"
                )

        # Step scheduler
        if epoch >= self.config.warmup_epochs:
            self.scheduler.step()

        duration = time.time() - start
        n = max(steps, 1)

        metrics = TrainMetrics(
            epoch=epoch,
            avg_loss=running["total"] / n,
            avg_contrastive=running["contrastive"] / n,
            avg_conflict=running["conflict"] / n,
            avg_governance=running["governance"] / n,
            avg_coherence=running_coherence / n,
            avg_drift=running_drift / n,
            duration_s=duration,
            steps=steps,
        )

        self.history.append(metrics)
        logger.info(
            f"Epoch {epoch} complete: loss={metrics.avg_loss:.4f} "
            f"coherence={metrics.avg_coherence:.4f} "
            f"drift={metrics.avg_drift:.6f} "
            f"({metrics.duration_s:.1f}s)"
        )

        return metrics

    def train(self, dataloader: Any) -> list[TrainMetrics]:
        """Run full training loop."""
        for epoch in range(self.config.epochs):
            metrics = self.train_epoch(dataloader, epoch)
        return self.history

    def save_checkpoint(self, path: str) -> None:
        """Save model + optimiser state."""
        torch.save(
            {
                "model": self.model.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "scheduler": self.scheduler.state_dict(),
                "global_step": self.global_step,
                "history": self.history,
            },
            path,
        )
        logger.info(f"Checkpoint saved to {path}")

    def load_checkpoint(self, path: str) -> None:
        """Load model + optimiser state."""
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
        self.scheduler.load_state_dict(ckpt["scheduler"])
        self.global_step = ckpt["global_step"]
        self.history = ckpt.get("history", [])
        logger.info(f"Checkpoint loaded from {path}")

    # --------------------------------------------------------------------------
    # Internal
    # --------------------------------------------------------------------------

    def _setup_optimiser(self) -> None:
        encoder_params = []
        head_params = []

        encoder_modules = {
            self.model.text_encoder,
            self.model.image_encoder,
            self.model.audio_encoder,
            self.model.code_encoder,
            self.model.state_encoder,
        }

        for name, param in self.model.named_parameters():
            is_encoder = any(
                name.startswith(prefix)
                for prefix in [
                    "text_encoder",
                    "image_encoder",
                    "audio_encoder",
                    "code_encoder",
                    "state_encoder",
                ]
            )
            if is_encoder:
                encoder_params.append(param)
            else:
                head_params.append(param)

        self.optimizer = AdamW(
            [
                {"params": head_params, "lr": self.config.lr},
                {"params": encoder_params, "lr": self.config.encoder_lr},
            ],
            weight_decay=self.config.weight_decay,
        )

    def _freeze_encoders(self) -> None:
        for name, param in self.model.named_parameters():
            if any(
                name.startswith(p)
                for p in ["text_encoder", "image_encoder", "audio_encoder", "code_encoder", "state_encoder"]
            ):
                param.requires_grad = False

    def _unfreeze_encoders(self) -> None:
        for param in self.model.parameters():
            param.requires_grad = True
