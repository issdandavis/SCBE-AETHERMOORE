"""
gyro_core.py

Non-Fixed Rotating Core for the 6-layer Code-Flow transformer.

Architecture metaphor:
  Suspension bridge with one fixed point on each end at a kids' park.
  - Left anchor: reconstruction accuracy (sonar echo)
  - Right anchor: governance cost H(d,R)
  - The middle hangs free and ROTATES — like a bridge that sways

  The core is a thin Möbius precession layer inserted between transformer
  layers 3 and 4 (the exact center of the 6-layer model). It rotates the
  residual stream by an angle proportional to the token's estimated position
  in the Poincaré ball. Safe tokens (KO-dominant) barely move. Adversarial
  tokens (DR-dominant) precess significantly.

  This is not a fixed transform — it's a ROTATING one. Each token gets a
  different rotation based on where it lives in governance space.

Sphere grid:
  Training samples are ordered by their position on the 6D tongue-profile
  unit sphere, traversed in a great-circle spiral from the safe pole (KO=1)
  outward to the adversarial pole (DR=1). Each epoch the spiral starts one
  step further — the curriculum rotates.

Learning disability pedagogy connection:
  Blank AI = student who cannot yet read, hear, or speak.
  Classical music training for learning disabilities:
    1. Rhythm first (temporal pulse) — Stage 0 binary patterns
    2. Same melody in different modes — mode_transfer samples
    3. Error as information not failure — sonar callback
    4. Two anchors, free middle — student attention swings between
       "hearing the note" and "understanding the theory" without
       having to do both at the same time
    5. Spiral curriculum (Bruner) — revisit at increasing depth
       each round with fewer residual "off notes" to correct

  The gyro core is the "free middle" — the transformer's internal
  representation can precess freely between the two loss anchors
  without being pinned to one fixed optimization target.

Dual-loss rotating weight:
  α(t) = (1 + cos(2π·t/T)) / 2   where T = rotation_period steps
  L_total = α·L_sonar + (1-α)·L_gov

  Sometimes the training is pulled toward echo accuracy.
  Sometimes toward governance cost.
  The pull rotates — the model learns both without getting stuck on one.
"""

from __future__ import annotations

import math
from typing import List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

PHI = 1.618033988749895


# =============================================================================
# GYRO CORE LAYER
# =============================================================================


class GyroCoreLayer(nn.Module):
    """
    Non-fixed rotating layer inserted at the center of the transformer.

    Given the current hidden state x ∈ R^(B, S, D):
    1. Project x → 1D governance estimate g ∈ [0, 1]  (proxy for d_H)
    2. Compute rotation angle θ = φ · g  (phi-scaled: safe tokens barely rotate)
    3. Apply 2D Givens rotation to pairs of dimensions in x
       Rotating PAIRS of residual-stream dimensions by angle θ
       is the discrete analog of a Möbius transformation on the ball.

    The rotation is non-fixed: θ changes per-token per-step.
    The core "hangs" between the two loss anchors and precesses freely.

    Sphere interpretation:
      The residual stream lives in R^D. We partition it into D/2 pairs.
      Each pair (x_{2i}, x_{2i+1}) is rotated by angle θ_i = θ + i·δ
      where δ = 2π / (D/2) distributes the rotation across all pairs.
      This creates a SPHERICAL ROTATION in R^D — not a flat one.
    """

    def __init__(self, hidden_dim: int = 384, phi_scale: float = PHI):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.phi_scale = phi_scale

        # Governance probe: projects hidden state → [0,1] d_H estimate
        # Lightweight: one linear + sigmoid
        self.gov_probe = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

        # Per-pair phase offset (D/2 learnable offsets — gives each pair a home angle)
        # These are the "fixed points on each end" of the bridge
        n_pairs = hidden_dim // 2
        self.pair_offsets = nn.Parameter(torch.linspace(0, 2 * math.pi, n_pairs))  # evenly spread around circle

        # Learnable scale on the rotation (starts at 1, can grow or shrink)
        self.rotation_scale = nn.Parameter(torch.ones(1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, S, D) — transformer hidden states

        Returns x with each (2i, 2i+1) dimension pair rotated by
        θ_i = rotation_scale · phi · gov_probe(x) + pair_offsets[i]
        """
        B, S, D = x.shape
        n_pairs = D // 2

        # Governance estimate per token: (B, S, 1)
        g = self.gov_probe(x)  # [0, 1] — proxy for d_H

        # Base rotation angle: φ · g  (safe tokens barely rotate, DR tokens precess)
        theta_base = self.rotation_scale * self.phi_scale * g  # (B, S, 1)

        # Per-pair angles: theta_base + offset_i for each pair i
        # Shape: (B, S, n_pairs)
        offsets = self.pair_offsets.unsqueeze(0).unsqueeze(0)  # (1, 1, n_pairs)
        theta = theta_base + offsets  # (B, S, n_pairs)

        cos_t = torch.cos(theta)  # (B, S, n_pairs)
        sin_t = torch.sin(theta)  # (B, S, n_pairs)

        # Apply Givens rotation to each pair
        # x_even = x[:, :, 0::2], x_odd = x[:, :, 1::2]  shape (B, S, n_pairs)
        x_even = x[:, :, 0::2]
        x_odd = x[:, :, 1::2]

        # Handle odd hidden_dim: truncate extra dim if needed
        if x_even.shape[-1] > n_pairs:
            x_even = x_even[:, :, :n_pairs]
            x_odd = x_odd[:, :, :n_pairs]

        # Givens: [cos -sin; sin cos] applied to [x_even; x_odd]
        x_even_rot = cos_t * x_even - sin_t * x_odd
        x_odd_rot = sin_t * x_even + cos_t * x_odd

        # Reassemble
        x_rot = torch.zeros_like(x)
        x_rot[:, :, 0::2] = x_even_rot
        x_rot[:, :, 1::2] = x_odd_rot

        # Residual: add rotation to original (don't replace — precess, not snap)
        return x + (x_rot - x) * 0.1  # 10% blend — starts subtle, learns its weight


# =============================================================================
# SPHERE GRID SAMPLE ORDERING
# =============================================================================


def compute_tongue_profile_unit(profile: List[float]) -> torch.Tensor:
    """Normalize a 6D tongue profile to the unit sphere."""
    p = torch.tensor(profile, dtype=torch.float32)
    norm = p.norm()
    if norm < 1e-8:
        return p
    return p / norm


def great_circle_spiral_order(
    profiles: List[List[float]],
    n_epochs: int = 1,
    epoch_offset: int = 0,
) -> List[int]:
    """
    Order sample indices by their position on the 6D tongue-profile unit sphere,
    traversed in a great-circle spiral from the safe pole (KO=1, rest=0) outward.

    Each epoch the spiral starts one step further around the sphere —
    the curriculum rotates. Same data, different angle each round.

    Safe pole: [1,0,0,0,0,0] (KO-dominant — ALLOW, lowest governance cost)
    Adversarial pole: [0,0,0,0,0,1] (DR-dominant — DENY, highest governance cost)

    Ordering: sort by angular distance from safe pole (KO axis).
    Angular distance = arccos(unit_profile · safe_pole) = arccos(unit_profile[0])
    Samples close to KO come first (safe, easy).
    Samples close to DR come last (adversarial, hard).

    The epoch_offset rotates which dimension is "north" each round —
    like the bridge swaying: sometimes KO is north, sometimes AV, etc.
    """
    safe_poles = [
        torch.tensor([1, 0, 0, 0, 0, 0], dtype=torch.float32),  # KO — epoch 0
        torch.tensor([0, 1, 0, 0, 0, 0], dtype=torch.float32),  # AV — epoch 1
        torch.tensor([0, 0, 1, 0, 0, 0], dtype=torch.float32),  # RU — epoch 2
        torch.tensor([0, 0, 0, 1, 0, 0], dtype=torch.float32),  # CA — epoch 3
        torch.tensor([0, 0, 0, 0, 1, 0], dtype=torch.float32),  # UM — epoch 4
        torch.tensor([0, 0, 0, 0, 0, 1], dtype=torch.float32),  # DR — epoch 5 (adversarial)
    ]
    pole = safe_poles[epoch_offset % 6]

    units = [compute_tongue_profile_unit(p) for p in profiles]

    def angular_distance(u: torch.Tensor) -> float:
        dot = (u @ pole).clamp(-1.0, 1.0).item()
        return math.acos(dot)

    indexed = list(enumerate(units))
    indexed.sort(key=lambda x: angular_distance(x[1]))
    return [i for i, _ in indexed]


# =============================================================================
# ROTATING DUAL LOSS
# =============================================================================


def rotating_alpha(step: int, rotation_period: int = 200) -> float:
    """
    Rotating blend weight between sonar loss and governance loss.

    α(t) = (1 + cos(2π·t/T)) / 2

    t=0:          α=1.0  → pure sonar (reconstruction accuracy)
    t=T/4:        α=0.5  → equal blend
    t=T/2:        α=0.0  → pure governance cost
    t=3T/4:       α=0.5  → equal blend again
    t=T:          α=1.0  → back to pure sonar

    The training never locks onto one objective — it keeps rotating.
    Like classical music: sometimes you practice the melody, sometimes
    the harmony, and together they become a piece.

    Args:
        step: current training step
        rotation_period: how many steps for one full rotation (default 200)
    """
    phase = 2 * math.pi * step / rotation_period
    return (1.0 + math.cos(phase)) / 2.0


def dual_loss(
    sonar_loss: torch.Tensor,
    gov_loss: torch.Tensor,
    step: int,
    rotation_period: int = 200,
) -> Tuple[torch.Tensor, float]:
    """
    Blend sonar (reconstruction) and governance losses with rotating weight.

    Returns:
        total_loss: α·L_sonar + (1-α)·L_gov
        alpha: the current blend weight (for logging)
    """
    alpha = rotating_alpha(step, rotation_period)
    total = alpha * sonar_loss + (1.0 - alpha) * gov_loss
    return total, alpha


# =============================================================================
# GOVERNANCE LOSS FROM HIDDEN STATE
# =============================================================================


class GovernanceLoss(nn.Module):
    """
    Compute a differentiable governance cost from the model's hidden states.

    Projects the final hidden state to a 6D tongue profile estimate,
    then computes the weighted dissonance d and hyperbolic cost H(d,R).

    This is the RIGHT anchor of the suspension bridge — pulling training
    toward low-cost (KO-dominant) representations.

    The sonar callback measures reconstruction accuracy (left anchor).
    This measures governance geometry (right anchor).
    The gyro core hangs between them.
    """

    PHI_WEIGHTS = torch.tensor([1.00, 1.62, 2.62, 4.24, 6.85, 11.09])
    MAX_R_VAL = 27.42

    def __init__(self, hidden_dim: int = 384, R: float = 5.0):
        super().__init__()
        self.R = R
        # Project hidden state → 6D tongue profile (softmax → sums to 1)
        self.profile_head = nn.Linear(hidden_dim, 6)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """
        hidden_states: (B, S, D) — last transformer layer outputs

        Returns scalar governance loss.
        High loss when model generates DR-dominant representations.
        Low loss when model stays near KO-dominant safe origin.
        """
        # Mean-pool across sequence: (B, D)
        h = hidden_states.mean(dim=1)

        # Estimate tongue profile: (B, 6), sums to 1
        profile = F.softmax(self.profile_head(h), dim=-1)

        # Weighted dissonance: d = sum(profile * phi_weight) / max_R
        phi_w = self.PHI_WEIGHTS.to(profile.device)
        d = (profile * phi_w).sum(dim=-1) / self.MAX_R_VAL  # (B,) in [0,1]

        # Hyperbolic cost: H = R^(d²)  — differentiable via log/exp
        # H = exp(d² * log(R))
        cost = torch.exp(d * d * math.log(self.R))  # (B,)

        # Loss = mean cost across batch (want cost ≈ 1.0, i.e. d ≈ 0)
        return (cost - 1.0).mean()


# =============================================================================
# PATCHING INTO GPT-2 MODEL
# =============================================================================


def patch_model_with_gyro_core(model: nn.Module, hidden_dim: int = 384) -> nn.Module:
    """
    Insert a GyroCoreLayer between transformer blocks 3 and 4 (center of 6 layers).

    The patched model's forward pass:
      [embed] → [block 0] → [block 1] → [block 2]
              → [GYRO CORE]  ← non-fixed rotating center
              → [block 3] → [block 4] → [block 5] → [lm_head]

    Wraps the model in a GyroPatchedModel that injects the core mid-forward.
    """
    gyro = GyroCoreLayer(hidden_dim=hidden_dim)
    gov_loss_fn = GovernanceLoss(hidden_dim=hidden_dim)
    return GyroPatchedModel(model, gyro, gov_loss_fn, insert_after_layer=2)


class GyroPatchedModel(nn.Module):
    """
    Wraps a GPT-2 model and injects the GyroCoreLayer at the center.

    Works by running the transformer blocks in two halves:
      first_half  = blocks [0, insert_after_layer]
      gyro_core   = rotation layer
      second_half = blocks [insert_after_layer+1, n_layers-1]
    """

    def __init__(
        self,
        base_model: nn.Module,
        gyro: GyroCoreLayer,
        gov_loss_fn: GovernanceLoss,
        insert_after_layer: int = 2,
    ):
        super().__init__()
        self.base_model = base_model
        self.gyro = gyro
        self.gov_loss_fn = gov_loss_fn
        self.insert_after_layer = insert_after_layer

        # Store reference to config for HF compatibility
        self.config = base_model.config

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        labels=None,
        return_governance_loss: bool = False,
        **kwargs,
    ):
        transformer = self.base_model.transformer

        # Embed
        hidden = transformer.wte(input_ids)
        if hasattr(transformer, "wpe"):
            position_ids = torch.arange(input_ids.shape[1], device=input_ids.device).unsqueeze(0)
            hidden = hidden + transformer.wpe(position_ids)
        hidden = transformer.drop(hidden)

        # First half: blocks 0..insert_after_layer
        for _i, block in enumerate(transformer.h[: self.insert_after_layer + 1]):
            outputs = block(hidden, attention_mask=attention_mask)
            hidden = outputs[0]

        # GYRO CORE — the non-fixed rotating center
        hidden = self.gyro(hidden)

        # Second half: blocks insert_after_layer+1..end
        for block in transformer.h[self.insert_after_layer + 1 :]:
            outputs = block(hidden, attention_mask=attention_mask)
            hidden = outputs[0]

        hidden = transformer.ln_f(hidden)

        # LM head → logits
        logits = self.base_model.lm_head(hidden)

        # Compute losses
        lm_loss = None
        gov_loss = None
        if labels is not None:
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = labels[:, 1:].contiguous()
            lm_loss = F.cross_entropy(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1),
                ignore_index=-100,
            )
            gov_loss = self.gov_loss_fn(hidden)

        if return_governance_loss:
            return logits, lm_loss, gov_loss

        # Standard HF output: return loss + logits
        from transformers.modeling_outputs import CausalLMOutputWithCrossAttentions

        return CausalLMOutputWithCrossAttentions(
            loss=lm_loss,
            logits=logits,
        )

    def save_pretrained(self, path: str, **kwargs):
        """Save base model + gyro core separately."""
        import os, json

        os.makedirs(path, exist_ok=True)
        self.base_model.save_pretrained(path, **kwargs)
        torch.save(self.gyro.state_dict(), os.path.join(path, "gyro_core.pt"))
        torch.save(self.gov_loss_fn.state_dict(), os.path.join(path, "gov_loss.pt"))
        with open(os.path.join(path, "gyro_config.json"), "w") as f:
            json.dump(
                {
                    "insert_after_layer": self.insert_after_layer,
                    "hidden_dim": self.gyro.hidden_dim,
                    "phi_scale": self.gyro.phi_scale,
                },
                f,
            )

    @classmethod
    def load_pretrained(cls, path: str, base_model_cls=None) -> "GyroPatchedModel":
        import json
        from transformers import GPT2LMHeadModel

        base_cls = base_model_cls or GPT2LMHeadModel
        base = base_cls.from_pretrained(path)
        with open(f"{path}/gyro_config.json") as f:
            cfg = json.load(f)
        gyro = GyroCoreLayer(hidden_dim=cfg["hidden_dim"], phi_scale=cfg["phi_scale"])
        gyro.load_state_dict(torch.load(f"{path}/gyro_core.pt", map_location="cpu"))
        gov = GovernanceLoss(hidden_dim=cfg["hidden_dim"])
        gov.load_state_dict(torch.load(f"{path}/gov_loss.pt", map_location="cpu"))
        return cls(base, gyro, gov, insert_after_layer=cfg["insert_after_layer"])

    def generate(self, *args, **kwargs):
        """Delegate generation to base model (gyro core is training-path only)."""
        return self.base_model.generate(*args, **kwargs)

    @property
    def device(self):
        return next(self.parameters()).device
