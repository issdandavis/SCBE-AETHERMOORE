"""
Multimodal Encoders
====================

Modality-specific encoders that produce fixed-dimension embeddings
suitable for the MultiModal Matrix alignment system.

Phase 1: Simple encoders (MLP, tiny CNN).
Phase 3: Swap for real transformers / ViT / audio models.

@module multimodal/encoders
@layer Layer 1-2 (Complex Context → Realification)
"""

from __future__ import annotations

import torch
import torch.nn as nn


class SimpleTextEncoder(nn.Module):
    """
    Token-ID text encoder with embedding + mean pooling.

    In Phase 3, replace with a transformer-based encoder.
    """

    def __init__(self, vocab_size: int = 50_000, d_model: int = 512):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, d_model)
        self.pool = nn.Linear(d_model, d_model)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            token_ids: [B, T] integer token indices.
        Returns:
            [B, D] text embedding.
        """
        x = self.emb(token_ids)  # [B, T, D]
        x = x.mean(dim=1)  # mean pool over sequence
        return self.pool(x)  # [B, D]


class SimpleImageEncoder(nn.Module):
    """
    Tiny CNN image encoder with adaptive pooling → projection.

    In Phase 3, replace with ViT or CLIP vision encoder.
    """

    def __init__(self, d_model: int = 512, in_channels: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.GELU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.proj = nn.Linear(64, d_model)

    def forward(self, img: torch.Tensor) -> torch.Tensor:
        """
        Args:
            img: [B, C, H, W] image tensor.
        Returns:
            [B, D] image embedding.
        """
        x = self.net(img).squeeze(-1).squeeze(-1)  # [B, 64]
        return self.proj(x)  # [B, D]


class SimpleAudioEncoder(nn.Module):
    """
    1D CNN encoder for mel-spectrogram / waveform input.

    In Phase 3, replace with Whisper encoder or audio transformer.
    """

    def __init__(self, d_model: int = 512, n_mels: int = 80):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(n_mels, 64, 3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv1d(64, 128, 3, stride=2, padding=1),
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.proj = nn.Linear(128, d_model)

    def forward(self, mel: torch.Tensor) -> torch.Tensor:
        """
        Args:
            mel: [B, n_mels, T] mel spectrogram.
        Returns:
            [B, D] audio embedding.
        """
        x = self.net(mel).squeeze(-1)  # [B, 128]
        return self.proj(x)  # [B, D]


class SimpleCodeEncoder(nn.Module):
    """
    Token-ID code encoder (shared architecture with text, separate weights).

    In Phase 3, replace with CodeBERT or StarCoder encoder.
    """

    def __init__(self, vocab_size: int = 50_000, d_model: int = 512):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, d_model)
        self.pool = nn.Linear(d_model, d_model)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            token_ids: [B, T] integer token indices.
        Returns:
            [B, D] code embedding.
        """
        x = self.emb(token_ids)
        x = x.mean(dim=1)
        return self.pool(x)


class StateEncoder(nn.Module):
    """
    Encodes SCBE governance state vectors (Sacred Tongue / 9D state).

    Maps a fixed-size state vector through MLP → d_model.
    """

    def __init__(self, state_dim: int = 9, d_model: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Args:
            state: [B, state_dim] governance state vector.
        Returns:
            [B, D] state embedding.
        """
        return self.net(state)
