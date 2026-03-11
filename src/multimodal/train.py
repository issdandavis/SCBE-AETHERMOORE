#!/usr/bin/env python3
"""
SCBE Multimodal Training Script
=================================

Single-file runnable training script.

Usage:
    python -m src.multimodal.train              # Train on dummy data
    python -m src.multimodal.train --real-data   # Train on real data (TODO)

Phases:
    1. Freeze encoders, train matrix + fusion (1 epoch)
    2. Unfreeze all, cosine-anneal LR (remaining epochs)

@module multimodal/train
"""

from __future__ import annotations

import argparse
import logging
import os

import torch
from torch.utils.data import DataLoader, Dataset

from .model import SCBEMultiModalModel
from .trainer import MultiModalTrainer, TrainConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("scbe-multimodal-train")


# =============================================================================
# Dummy Dataset (Phase 1 — verify pipeline)
# =============================================================================


class DummyMultiModalDataset(Dataset):
    """
    Generates random text tokens + images for pipeline validation.

    In Phase 3, replace with real data from training-data/ JSONL files.
    """

    def __init__(self, size: int = 1000, seq_len: int = 32, img_size: int = 64, vocab_size: int = 50_000):
        self.size = size
        self.seq_len = seq_len
        self.img_size = img_size
        self.vocab_size = vocab_size

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "text_tokens": torch.randint(0, self.vocab_size, (self.seq_len,)),
            "image": torch.randn(3, self.img_size, self.img_size),
        }


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="SCBE Multimodal Training")
    parser.add_argument("--d-model", type=int, default=256, help="Embedding dimension")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--dataset-size", type=int, default=1000, help="Dummy dataset size")
    parser.add_argument("--save-dir", type=str, default="checkpoints", help="Checkpoint directory")
    parser.add_argument("--real-data", action="store_true", help="Use real data (NYI)")
    args = parser.parse_args()

    logger.info(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    # Model
    model = SCBEMultiModalModel(
        d_model=args.d_model,
        vocab_size=50_000,
        use_reliability=True,
        fusion_type="matrix_weighted",
    )
    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"Model params: {param_count:,}")

    # Config
    config = TrainConfig(
        lr=args.lr,
        encoder_lr=args.lr * 0.1,
        epochs=args.epochs,
        freeze_encoders_epochs=1,
        save_dir=args.save_dir,
    )

    # Dataset
    if args.real_data:
        logger.warning("Real data loading not yet implemented — falling back to dummy")

    dataset = DummyMultiModalDataset(
        size=args.dataset_size,
        img_size=64,
        vocab_size=50_000,
    )
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)

    # Train
    trainer = MultiModalTrainer(model, config)
    history = trainer.train(dataloader)

    # Save
    os.makedirs(args.save_dir, exist_ok=True)
    ckpt_path = os.path.join(args.save_dir, "scbe_multimodal_final.pt")
    trainer.save_checkpoint(ckpt_path)

    # Summary
    logger.info("Training complete:")
    for m in history:
        logger.info(
            f"  Epoch {m.epoch}: loss={m.avg_loss:.4f} "
            f"coherence={m.avg_coherence:.4f} "
            f"drift={m.avg_drift:.6f}"
        )


if __name__ == "__main__":
    main()
