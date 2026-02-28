"""
GeoSeed Model — HuggingFace-Compatible Neural Network
=======================================================

PyTorch nn.Module wrapping the GeoSeed architecture:
- 6 learnable icosahedral sphere grids (Cl(6,0) basis)
- Bit-level dressing through 14-layer SCBE stack
- Product manifold composition with bivector interactions
- Hyperbolic convergence output

Compatible with HuggingFace transformers ecosystem:
- PreTrainedModel-style save/load
- push_to_hub support
- Configurable via GeoSeedConfig

@layer L1-L14
@component GeoSeed.Model
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from src.geoseed.sphere_grid import (
    TONGUE_NAMES,
    TONGUE_PHASES,
    PHI_WEIGHTS,
    PHI,
    CL6,
    icosahedral_subdivide,
)


@dataclass
class GeoSeedConfig:
    """Configuration for the GeoSeed Network model."""

    # Sphere grid parameters
    resolution: int = 3          # Icosahedral subdivision level (3 → 642 vertices)
    signal_dim: int = 64         # Cl(6,0) multivector dimension
    n_tongues: int = 6           # Number of Sacred Tongues

    # Architecture parameters
    hidden_dim: int = 256        # Hidden layer dimension
    output_dim: int = 384        # Output embedding dimension
    n_propagation_steps: int = 2 # Sphere grid propagation rounds
    n_heads: int = 6             # Attention heads (one per tongue)
    dropout: float = 0.1

    # Dressing parameters
    dressing_dim: int = 6        # Input dimension for L1 complex state
    use_full_dressing: bool = True  # F1 (full) vs F2 (lightweight)

    # Model metadata
    model_type: str = "geoseed"
    architectures: List[str] = None

    def __post_init__(self):
        if self.architectures is None:
            self.architectures = ["GeoSeedModel"]

    def save_pretrained(self, save_directory: str):
        os.makedirs(save_directory, exist_ok=True)
        with open(os.path.join(save_directory, "config.json"), "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def from_pretrained(cls, load_directory: str) -> "GeoSeedConfig":
        with open(os.path.join(load_directory, "config.json")) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


if HAS_TORCH:

    class SphereConv(nn.Module):
        """Learnable graph convolution on an icosahedral sphere grid.

        Replaces the numpy-based intra_convolve with a differentiable PyTorch version.
        Each vertex aggregates neighbor signals through a learned linear transform,
        weighted by geodesic distance.
        """

        def __init__(self, signal_dim: int, resolution: int = 3):
            super().__init__()
            self.signal_dim = signal_dim

            # Build the icosahedral mesh
            vertices, edges = icosahedral_subdivide(resolution)
            self.n_vertices = len(vertices)
            self.register_buffer("vertices", torch.tensor(vertices, dtype=torch.float32))

            # Build adjacency as sparse indices
            src_indices = []
            dst_indices = []
            weights = []
            for u, v in edges:
                # Geodesic weight
                dot = float(np.clip(np.dot(vertices[u], vertices[v]), -1.0, 1.0))
                w = math.exp(-math.acos(dot))
                src_indices.extend([u, v])
                dst_indices.extend([v, u])
                weights.extend([w, w])

            self.register_buffer("edge_src", torch.tensor(src_indices, dtype=torch.long))
            self.register_buffer("edge_dst", torch.tensor(dst_indices, dtype=torch.long))
            self.register_buffer("edge_weights", torch.tensor(weights, dtype=torch.float32))

            # Learnable transform
            self.linear = nn.Linear(signal_dim, signal_dim)
            self.norm = nn.LayerNorm(signal_dim)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Graph convolution on sphere grid.

            Args:
                x: (batch, n_vertices, signal_dim)

            Returns:
                (batch, n_vertices, signal_dim) convolved signals
            """
            batch_size = x.shape[0]

            # Transform signals
            h = self.linear(x)  # (batch, N, D)

            # Scatter-add neighbor messages
            # For each edge (src→dst), accumulate weighted signal from src to dst
            src_signals = h[:, self.edge_src]  # (batch, E, D)
            weighted = src_signals * self.edge_weights.unsqueeze(0).unsqueeze(-1)

            # Aggregate at destination vertices
            out = torch.zeros_like(h)
            out.scatter_add_(1, self.edge_dst.unsqueeze(0).unsqueeze(-1).expand(batch_size, -1, self.signal_dim), weighted)

            # Normalize by degree
            degree = torch.zeros(self.n_vertices, device=x.device)
            degree.scatter_add_(0, self.edge_dst, self.edge_weights)
            degree = degree.clamp(min=1e-6)
            out = out / degree.unsqueeze(0).unsqueeze(-1)

            # Self-loop + residual
            out = 0.5 * x + 0.5 * out
            out = self.norm(F.relu(out))

            return out


    class CrossTongueAttention(nn.Module):
        """Bivector-weighted cross-tongue attention.

        Implements the 15 interaction channels between 6 Sacred Tongues,
        where attention weights are modulated by Cl(6,0) bivector strengths.
        """

        def __init__(self, signal_dim: int, n_heads: int = 6):
            super().__init__()
            self.signal_dim = signal_dim
            self.n_heads = n_heads
            assert signal_dim % n_heads == 0
            self.head_dim = signal_dim // n_heads

            self.q_proj = nn.Linear(signal_dim, signal_dim)
            self.k_proj = nn.Linear(signal_dim, signal_dim)
            self.v_proj = nn.Linear(signal_dim, signal_dim)
            self.out_proj = nn.Linear(signal_dim, signal_dim)

            # Precompute bivector strengths as attention bias
            bias = torch.zeros(6, 6)
            for i, t1 in enumerate(TONGUE_NAMES):
                for j, t2 in enumerate(TONGUE_NAMES):
                    if i != j:
                        bias[i, j] = CL6.bivector_strength(t1, t2)
            self.register_buffer("bivector_bias", bias)

        def forward(self, tongue_signals: torch.Tensor) -> torch.Tensor:
            """Cross-tongue attention with bivector modulation.

            Args:
                tongue_signals: (batch, 6, signal_dim) — one embedding per tongue

            Returns:
                (batch, 6, signal_dim) — cross-attended signals
            """
            B, T, D = tongue_signals.shape  # T = 6 tongues

            q = self.q_proj(tongue_signals).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
            k = self.k_proj(tongue_signals).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
            v = self.v_proj(tongue_signals).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

            # Scaled dot-product attention
            scale = math.sqrt(self.head_dim)
            attn = torch.matmul(q, k.transpose(-2, -1)) / scale

            # Add bivector strength bias (broadcast across heads)
            attn = attn + self.bivector_bias.unsqueeze(0).unsqueeze(0)

            attn = F.softmax(attn, dim=-1)

            out = torch.matmul(attn, v)
            out = out.transpose(1, 2).contiguous().view(B, T, D)
            return self.out_proj(out)


    class PoincareConvergence(nn.Module):
        """Project composed signals into the Poincaré ball for final embedding.

        Uses the exponential map at origin to ensure the output stays
        within the unit ball (hyperbolic space).
        """

        def __init__(self, input_dim: int, output_dim: int, curvature: float = 1.0):
            super().__init__()
            self.linear = nn.Linear(input_dim, output_dim)
            self.curvature = curvature

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """Project to Poincaré ball.

            Args:
                x: (batch, input_dim)

            Returns:
                (batch, output_dim) in the Poincaré ball
            """
            h = self.linear(x)
            # Exponential map at origin: exp_0(v) = tanh(sqrt(c)||v||/2) * v / (sqrt(c)||v||)
            norm = torch.norm(h, dim=-1, keepdim=True).clamp(min=1e-8)
            sqrt_c = math.sqrt(self.curvature)
            return torch.tanh(sqrt_c * norm / 2) * h / (sqrt_c * norm)


    class GeoSeedModel(nn.Module):
        """GeoSeed Network — 6-sphere Cl(6,0) neural architecture.

        Full pipeline:
        1. Input embedding (raw data → per-tongue features)
        2. Sphere grid convolution (6 parallel icosahedral convs)
        3. Cross-tongue attention (15 bivector channels)
        4. Poincaré convergence (hyperbolic output)

        Compatible with HuggingFace save/load patterns.
        """

        def __init__(self, config: GeoSeedConfig):
            super().__init__()
            self.config = config

            # Input projection: raw features → signal_dim per tongue
            self.input_proj = nn.Linear(config.dressing_dim * 2, config.signal_dim)
            self.tongue_embed = nn.Embedding(config.n_tongues, config.signal_dim)

            # 6 sphere grid convolutions (one per tongue)
            self.sphere_convs = nn.ModuleList([
                SphereConv(config.signal_dim, config.resolution)
                for _ in range(config.n_tongues)
            ])

            # Cross-tongue attention
            self.cross_attention = CrossTongueAttention(
                config.signal_dim, config.n_heads
            )

            # Propagation layers
            self.propagation_layers = nn.ModuleList([
                nn.Sequential(
                    CrossTongueAttention(config.signal_dim, config.n_heads),
                    nn.LayerNorm(6 * config.signal_dim),
                )
                for _ in range(config.n_propagation_steps)
            ])

            # Aggregation: 6 tongue signals → single embedding
            self.aggregation = nn.Sequential(
                nn.Linear(6 * config.signal_dim, config.hidden_dim),
                nn.GELU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.hidden_dim, config.hidden_dim),
            )

            # Poincaré convergence layer
            self.convergence = PoincareConvergence(
                config.hidden_dim, config.output_dim
            )

        def forward(
            self,
            input_features: torch.Tensor,
            tongue_ids: Optional[torch.Tensor] = None,
        ) -> Dict[str, torch.Tensor]:
            """Forward pass through the GeoSeed Network.

            Args:
                input_features: (batch, seq_len, dressing_dim*2)
                    Pre-dressed features from the BitDresser
                tongue_ids: (batch, seq_len) tongue assignments (0-5)
                    If None, assigned round-robin by position

            Returns:
                Dict with:
                    "embedding": (batch, output_dim) in Poincaré ball
                    "tongue_signals": (batch, 6, signal_dim) per-tongue
                    "convergence": (batch, output_dim) final position
            """
            B, S, _ = input_features.shape

            # Assign tongues if not provided
            if tongue_ids is None:
                tongue_ids = torch.arange(S, device=input_features.device) % 6
                tongue_ids = tongue_ids.unsqueeze(0).expand(B, -1)

            # Project input features
            h = self.input_proj(input_features)  # (B, S, signal_dim)

            # Add tongue embeddings
            h = h + self.tongue_embed(tongue_ids)

            # Scatter to 6 tongue groups (take mean per tongue)
            tongue_signals = torch.zeros(B, 6, self.config.signal_dim, device=h.device)
            counts = torch.zeros(B, 6, 1, device=h.device)
            for t in range(6):
                mask = (tongue_ids == t).unsqueeze(-1).float()
                tongue_signals[:, t] = (h * mask).sum(dim=1)
                counts[:, t] = mask.sum(dim=1, keepdim=False)[:, :1]
            counts = counts.clamp(min=1)
            tongue_signals = tongue_signals / counts

            # Cross-tongue attention
            tongue_signals = tongue_signals + self.cross_attention(tongue_signals)

            # Propagation steps
            for layer in self.propagation_layers:
                cross_attn, norm = layer[0], layer[1]
                residual = tongue_signals
                tongue_signals = tongue_signals + cross_attn(tongue_signals)
                flat = tongue_signals.view(B, -1)
                flat = norm(flat)
                tongue_signals = flat.view(B, 6, self.config.signal_dim)

            # Aggregate all tongues
            flat = tongue_signals.view(B, -1)  # (B, 6*signal_dim)
            aggregated = self.aggregation(flat)

            # Poincaré convergence
            convergence = self.convergence(aggregated)

            return {
                "embedding": convergence,
                "tongue_signals": tongue_signals,
                "convergence": convergence,
            }

        def save_pretrained(self, save_directory: str):
            """Save model weights and config (HuggingFace-compatible)."""
            os.makedirs(save_directory, exist_ok=True)
            self.config.save_pretrained(save_directory)
            torch.save(self.state_dict(), os.path.join(save_directory, "pytorch_model.bin"))

        @classmethod
        def from_pretrained(cls, load_directory: str) -> "GeoSeedModel":
            """Load model from directory (HuggingFace-compatible)."""
            config = GeoSeedConfig.from_pretrained(load_directory)
            model = cls(config)
            weights_path = os.path.join(load_directory, "pytorch_model.bin")
            if os.path.exists(weights_path):
                model.load_state_dict(torch.load(weights_path, map_location="cpu"))
            return model

        @property
        def num_parameters(self) -> int:
            return sum(p.numel() for p in self.parameters())

        @property
        def num_trainable_parameters(self) -> int:
            return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ---------------------------------------------------------------------------
# Numpy-only fallback for environments without PyTorch
# ---------------------------------------------------------------------------

class GeoSeedModelNumpy:
    """Pure-numpy GeoSeed model for validation and testing.

    Implements the same architecture as GeoSeedModel but without
    learnable parameters — uses fixed geometric operations only.
    Uses the full geometric dressing/composition pipeline (F1 tier).
    """

    def __init__(self, config: Optional[GeoSeedConfig] = None):
        from src.geoseed.dressing_geometric import GeometricBitDresser, DressingTier
        from src.geoseed.composition_geometric import GeometricComposer

        self.config = config or GeoSeedConfig()
        self.dresser = GeometricBitDresser(tier=DressingTier.F1, dimension=self.config.dressing_dim)
        self.composer = GeometricComposer(
            resolution=self.config.resolution,
            signal_dim=self.config.signal_dim,
            n_propagation_steps=self.config.n_propagation_steps,
        )

    def forward(self, data: bytes) -> Dict[str, Any]:
        """Process raw bytes through the full GeoSeed pipeline.

        Args:
            data: raw input bytes

        Returns:
            Dict with embedding, tongue_signals, cross_terms, governance_ratio
        """
        # Dress
        dressed = self.dresser.dress_bytes(data)

        # Compose
        unit = self.composer.compose(dressed)

        # Convert to embedding
        embedding = unit.to_embedding(dim=self.config.output_dim)

        return {
            "embedding": embedding,
            "tongue_signals": unit.tongue_signals,
            "cross_terms": unit.cross_terms,
            "convergence": unit.convergence_point,
            "governance_ratio": unit.governance_ratio,
            "total_energy": unit.total_energy,
            "n_bits": unit.n_bits,
        }

    def forward_text(self, text: str) -> Dict[str, Any]:
        """Process a text string through the full GeoSeed pipeline."""
        return self.forward(text.encode("utf-8"))
