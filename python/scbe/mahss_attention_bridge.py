"""MAHSS attention bridge: a learnable primitive that lets a transformer
attend over the role-pinned HRR memory at training time.

Phase 2 showed that prompt-prefix injection of MAHSS-retrieved markers
does not lift LLM raw pass rate -- the model treats the prefix as
informational text, not a token-level requirement. Phase 3's hypothesis
is that if the model has a TRAINABLE pathway to query the MAHSS memory
mid-forward-pass, it will learn to use retrieved fillers when the
training signal rewards doing so.

This module is the architectural primitive. It is intentionally
framework-light (pure PyTorch, no transformers/peft dependency) so it
can be dropped into either:

  (a) a Qwen2.5-Coder-7B LoRA module (Phase 3a), OR
  (b) a from-zero model architecture (the user's eventual goal)

Math (one bridge call, single token):

    h ∈ R^d                              # hidden state at some layer
    M ∈ R^k                              # frozen HRR memory bundle
    V ∈ R^(|V|×k)                        # frozen filler vocabulary
    q = W_q h                            # learned project hidden -> role-space
    u = circular_correlation(q, M)       # HRR unbind from memory
    s_j = cos(u, V_j)                    # cosine similarity per filler
    a = Σ_j softmax(s)_j · V_j           # weighted retrieval
    h' = h + σ(W_g h) ⊙ W_v a            # learned gated residual

Trainable: W_q (d→k), W_v (k→d), W_g (d→d). At d=k=4096 with rank-r
factorizations, parameter count is O(d·r), not O(d²). Frozen:
M, V, role vectors, all derived deterministically from MAHSS spec.

Falsifiable Phase 3 prediction (small-scale): on a synthetic
role-conditioned token-prediction task where the answer is in MAHSS
memory, the bridged-MLP model achieves >=80% accuracy after training,
while a parameter-matched no-bridge MLP plateaus at chance level. If
true, the substrate works; the question becomes whether scale
(7B + real corpus) carries the same property."""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass(frozen=True)
class MAHSSBridgeConfig:
    """Configuration for one bridge instance.

    ``hidden_dim`` matches the model's per-token hidden state.
    ``memory_dim`` is the MAHSS HRR vector dimension. They can differ
    (the projections handle the conversion).

    ``rank`` controls W_q and W_v factorization: instead of full
    (hidden_dim x memory_dim), we use (hidden_dim x rank) @
    (rank x memory_dim). At rank=32 with both dims=4096, each projection
    is ~256K params instead of ~16M, matching LoRA scale."""

    hidden_dim: int = 4096
    memory_dim: int = 4096
    rank: int = 32
    softmax_temperature: float = 1.0
    gate_init_bias: float = -2.0  # σ(-2) ≈ 0.12, bridge starts mostly off
    eps: float = 1e-9

    def __post_init__(self) -> None:
        if self.hidden_dim < 8 or self.memory_dim < 8:
            raise ValueError("hidden_dim and memory_dim must be >= 8")
        if self.rank < 1 or self.rank > min(self.hidden_dim, self.memory_dim):
            raise ValueError(f"rank must be in [1, min(dims)]; got {self.rank}")
        if self.softmax_temperature <= 0:
            raise ValueError("softmax_temperature must be > 0")


def circular_correlation_torch(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """HRR unbinding via FFT, batched. Last-dim FFT.

    a, b shape: (..., d). Returns shape (..., d)."""

    A = torch.fft.fft(a, dim=-1)
    B = torch.fft.fft(b, dim=-1)
    return torch.fft.ifft(torch.conj(A) * B, dim=-1).real


class MAHSSAttentionBridge(nn.Module):
    """Trainable bridge: projects hidden state into role-space, unbinds
    from HRR memory, attends over filler vocabulary, and adds a gated
    residual back into the hidden state.

    Memory and vocabulary are passed at forward time so the same bridge
    instance can serve different MAHSS contexts (e.g. per-prompt
    memories built by the parser). Role vectors are NOT a parameter --
    they live inside the memory bundle, which is built externally."""

    def __init__(self, config: MAHSSBridgeConfig) -> None:
        super().__init__()
        self.config = config
        d, k, r = config.hidden_dim, config.memory_dim, config.rank
        # Low-rank query projection: hidden -> role-space
        self.W_q_a = nn.Parameter(torch.empty(d, r))
        self.W_q_b = nn.Parameter(torch.empty(r, k))
        # Low-rank value projection: role-space attended back to hidden
        self.W_v_a = nn.Parameter(torch.empty(k, r))
        self.W_v_b = nn.Parameter(torch.empty(r, d))
        # Gate from hidden state (full rank, small): controls how much bridge contributes
        self.W_g = nn.Parameter(torch.empty(d, d))
        self.b_g = nn.Parameter(torch.empty(d))
        self.reset_parameters()

    def reset_parameters(self) -> None:
        # Standard LoRA-style init: A is Kaiming uniform, B is zero so the
        # initial bridge output is exactly zero (preserves base model behavior
        # at training start).
        nn.init.kaiming_uniform_(self.W_q_a, a=math.sqrt(5))
        nn.init.zeros_(self.W_q_b)
        nn.init.kaiming_uniform_(self.W_v_a, a=math.sqrt(5))
        nn.init.zeros_(self.W_v_b)
        nn.init.kaiming_uniform_(self.W_g, a=math.sqrt(5))
        nn.init.constant_(self.b_g, self.config.gate_init_bias)

    def project_query(self, h: torch.Tensor) -> torch.Tensor:
        """Project hidden state h ∈ R^d to role-space q ∈ R^k via low-rank W_q."""

        return (h @ self.W_q_a) @ self.W_q_b

    def project_value(self, a: torch.Tensor) -> torch.Tensor:
        """Project attended role-space vector a ∈ R^k back to R^d via low-rank W_v."""

        return (a @ self.W_v_a) @ self.W_v_b

    def gate(self, h: torch.Tensor) -> torch.Tensor:
        """Compute σ(W_g h + b_g): per-coordinate gate in [0, 1]."""

        return torch.sigmoid(h @ self.W_g + self.b_g)

    def forward(
        self,
        hidden: torch.Tensor,
        memory: torch.Tensor,
        vocab: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Run the bridge.

        Args:
            hidden: (..., hidden_dim) hidden state at this layer
            memory: (..., memory_dim) MAHSS HRR bundle. Must broadcast with
                ``hidden`` over leading dims.
            vocab:  (..., V, memory_dim) filler vocabulary; the V dimension
                is the candidate count and may differ across calls.

        Returns:
            h_new: (..., hidden_dim) updated hidden state
            attn_weights: (..., V) softmax distribution over fillers, for
                interpretability and for the auxiliary retrieval loss.
        """

        cfg = self.config
        q = self.project_query(hidden)
        # Broadcast memory across the leading dims of q
        if memory.shape != q.shape:
            memory = memory.expand_as(q)
        u = circular_correlation_torch(q, memory)
        # Score u against each filler. vocab shape (..., V, k); u shape (..., k)
        u_norm = u / (u.norm(dim=-1, keepdim=True) + cfg.eps)
        v_norm = vocab / (vocab.norm(dim=-1, keepdim=True) + cfg.eps)
        # u_norm @ v_norm.T -> shape (..., V)
        scores = torch.einsum("...k,...vk->...v", u_norm, v_norm)
        attn = F.softmax(scores / cfg.softmax_temperature, dim=-1)
        # Attended retrieval: weighted sum of filler vectors
        attended = torch.einsum("...v,...vk->...k", attn, vocab)
        # Project back to hidden space and gate
        delta = self.project_value(attended)
        gate = self.gate(hidden)
        h_new = hidden + gate * delta
        return h_new, attn

    def num_trainable_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def build_role_pinned_memory_tensor(
    bindings: list[tuple[torch.Tensor, torch.Tensor]],
) -> torch.Tensor:
    """Construct an HRR memory bundle from a list of (role_vec, filler_vec) pairs.

    Each binding contributes circular_convolution(role, filler) to the
    superposition. Returns a tensor of shape (k,) where k is the common
    dimension. Uses torch FFT so the result is on the same device/dtype
    as the inputs."""

    if not bindings:
        raise ValueError("need at least one binding to build memory")
    out = None
    for role, filler in bindings:
        if role.shape != filler.shape:
            raise ValueError(f"role/filler shape mismatch: {role.shape} vs {filler.shape}")
        bound = torch.fft.ifft(torch.fft.fft(role) * torch.fft.fft(filler)).real
        out = bound if out is None else out + bound
    return out


__all__ = [
    "MAHSSAttentionBridge",
    "MAHSSBridgeConfig",
    "build_role_pinned_memory_tensor",
    "circular_correlation_torch",
]
