"""
SCBE Multimodal Model
======================

End-to-end model combining modality encoders, the MultiModal
alignment matrix, and fusion. Produces fused embeddings plus
governance-relevant metrics (coherence, drift, alignment matrix).

Phase 1: text + image (2 modalities)
Phase 2: + state (Sacred Tongue / 9D SCBE vector)
Phase 3: + audio + code (5 modalities, real encoders)

@module multimodal/model
@layer Layer 1-14 (full pipeline)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn

from .encoders import (
    SimpleAudioEncoder,
    SimpleCodeEncoder,
    SimpleImageEncoder,
    SimpleTextEncoder,
    StateEncoder,
)
from .fusion import GatedFusion, MatrixWeightedFusion
from .multimodal_matrix import MultiModalMatrix


@dataclass
class MultiModalOutput:
    """Output from the SCBE multimodal model."""

    # Core outputs
    z_fused: torch.Tensor  # [B, D] fused embedding
    E: torch.Tensor  # [B, M, D] stacked modality embeddings
    A: torch.Tensor  # [B, M, M] alignment matrix
    w: torch.Tensor | None  # [B, M] reliability weights

    # Per-modality embeddings (only populated for active modalities)
    z_text: torch.Tensor | None = None
    z_image: torch.Tensor | None = None
    z_audio: torch.Tensor | None = None
    z_code: torch.Tensor | None = None
    z_state: torch.Tensor | None = None

    # Governance metrics
    coherence: torch.Tensor | None = None  # [B] mean off-diag(A)
    drift: torch.Tensor | None = None  # [B] var off-diag(A)


class SCBEMultiModalModel(nn.Module):
    """
    SCBE Multimodal Model.

    Encodes available modalities, computes alignment matrix,
    and produces fused representation with governance metrics.
    """

    def __init__(
        self,
        d_model: int = 512,
        vocab_size: int = 50_000,
        n_mels: int = 80,
        state_dim: int = 9,
        use_reliability: bool = True,
        fusion_type: str = "matrix_weighted",
    ):
        super().__init__()
        self.d_model = d_model

        # Modality encoders
        self.text_encoder = SimpleTextEncoder(vocab_size, d_model)
        self.image_encoder = SimpleImageEncoder(d_model)
        self.audio_encoder = SimpleAudioEncoder(d_model, n_mels)
        self.code_encoder = SimpleCodeEncoder(vocab_size, d_model)
        self.state_encoder = StateEncoder(state_dim, d_model)

        # Alignment matrix
        self.mm = MultiModalMatrix(d_model, use_reliability)

        # Fusion
        if fusion_type == "gated":
            self.fuse = GatedFusion(d_model)
        else:
            self.fuse = MatrixWeightedFusion(d_model)

    def forward(self, batch: dict[str, torch.Tensor]) -> MultiModalOutput:
        """
        Forward pass. Batch keys determine which modalities are active.

        Expected batch keys:
            text_tokens: [B, T] — text token IDs
            image: [B, C, H, W] — image tensor
            audio_mel: [B, n_mels, T] — mel spectrogram
            code_tokens: [B, T] — code token IDs
            state: [B, state_dim] — SCBE governance state vector

        At least 2 modalities must be present.
        """
        embeddings: list[torch.Tensor] = []
        z_text = z_image = z_audio = z_code = z_state = None

        if "text_tokens" in batch:
            z_text = self.text_encoder(batch["text_tokens"])
            embeddings.append(z_text)

        if "image" in batch:
            z_image = self.image_encoder(batch["image"])
            embeddings.append(z_image)

        if "audio_mel" in batch:
            z_audio = self.audio_encoder(batch["audio_mel"])
            embeddings.append(z_audio)

        if "code_tokens" in batch:
            z_code = self.code_encoder(batch["code_tokens"])
            embeddings.append(z_code)

        if "state" in batch:
            z_state = self.state_encoder(batch["state"])
            embeddings.append(z_state)

        if len(embeddings) < 2:
            raise ValueError(f"Need >= 2 modalities, got {len(embeddings)}")

        # Stack modalities → [B, M, D]
        E = torch.stack(embeddings, dim=1)

        # Alignment matrix
        A, w = self.mm(E)

        # Fusion
        z_fused = self.fuse(E, A, w)

        # Governance metrics
        coherence = self.mm.coherence(A)
        drift = self.mm.drift(A)

        return MultiModalOutput(
            z_fused=z_fused,
            E=E,
            A=A,
            w=w,
            z_text=z_text,
            z_image=z_image,
            z_audio=z_audio,
            z_code=z_code,
            z_state=z_state,
            coherence=coherence,
            drift=drift,
        )
