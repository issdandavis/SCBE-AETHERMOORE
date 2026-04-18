"""
fun_attractor.py

Fun as a training signal — fuzzy point attractors set OUTSIDE the tongue space.

Concept:
  The 6 tongue axes span a simplex inside the Poincaré ball:
    KO = [1,0,0,0,0,0]  (safe, φ-weight = 1.00)
    AV = [0,1,0,0,0,0]  (φ-weight = 1.62)
    ...
    DR = [0,0,0,0,0,1]  (adversarial, φ-weight = 11.09)

  "Fun" attractors live OUTSIDE the pure-tongue axes — in the interstitial
  cross-tongue space. They are Gaussian blobs centered on historically
  successful output profiles: cross-tongue blend points that appeared in
  examples the model completed correctly (sonar echo hits).

  The loss: when the model's hidden tongue profile is close to an attractor,
  the loss goes DOWN (reward signal). When it's far from all attractors,
  the loss goes UP (gentle push toward success zones).

  This is a soft attractor, not a hard wall. The model isn't forced toward
  fun — it's pulled by a gravity-free fuzzy well. It can still choose to
  operate near the adversarial pole; it just costs more and earns less.

  No gravity wells inside tongue space (by design — those would interfere
  with the existing KO-dominant safe attractor from GovernanceLoss).
  These attractors sit in the cross-tongue interstitial region:
    center_ij = (e_i + e_j) / 2   for i ≠ j   (15 pairs)
    center_ijk = (e_i + e_j + e_k) / 3  for i<j<k  (20 triples)

  Pre-filtered to only include combinations that include KO or AV
  (to avoid purely DR-heavy attractors that would conflict with governance).

Training demo:
  FunAttractorLoss can be added as a third term in the rotating dual loss:
    L = α·L_sonar + β·L_gov + γ·L_fun
  where γ is small (0.1) so fun is a bonus, not the objective.

  The fun score is logged to W&B as "fun/score" — productivity dashboard.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

PHI_WEIGHTS = torch.tensor([1.00, 1.62, 2.62, 4.24, 6.85, 11.09])
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]


# =============================================================================
# BUILD ATTRACTOR SET: cross-tongue interstitial points (outside pure axes)
# Only pairs/triples that include KO (0) or AV (1) — governance-safe blends
# =============================================================================


def _build_fun_attractors() -> torch.Tensor:
    """
    Generate fuzzy attractor centers in 6D tongue-profile space.

    Returns: (N, 6) tensor of attractor centers, each row sums to 1.

    Attractors are:
      - Pair blends (e_i + e_j) / 2  for pairs containing KO or AV
      - Triple blends (e_i + e_j + e_k) / 3  for triples containing KO

    These are OUTSIDE the pure tongue axes (which are the 6 standard basis
    vectors) but inside the 6D simplex.
    """
    n = 6
    centers = []

    # Pairs containing KO (idx 0) or AV (idx 1) — 9 pairs
    for i, j in combinations(range(n), 2):
        if i == 0 or i == 1:  # must include KO or AV
            c = torch.zeros(n)
            c[i] = 0.5
            c[j] = 0.5
            centers.append(c)

    # Triples containing KO (idx 0) — 10 triples
    for i, j, k in combinations(range(n), 3):
        if i == 0:  # must include KO
            c = torch.zeros(n)
            c[i] = 1 / 3
            c[j] = 1 / 3
            c[k] = 1 / 3
            centers.append(c)

    return torch.stack(centers)  # (N, 6)


# Pre-computed attractor centers: (N, 6)
FUN_ATTRACTORS = _build_fun_attractors()


# =============================================================================
# FUN ATTRACTOR LOSS
# =============================================================================


class FunAttractorLoss(nn.Module):
    """
    Fuzzy attractor reward: model gets a bonus for heading toward
    historically successful cross-tongue blend points.

    The "fun score" measures how close the model's hidden tongue profile
    is to the nearest fuzzy attractor. Score ∈ (0, 1]:
      - Score ≈ 1.0: model is near a success zone (fun, productive)
      - Score ≈ 0.0: model is in uncharted space (not necessarily bad, just unknown)

    Loss = -log(fun_score)  →  minimizing this pulls toward attractors.

    Args:
        hidden_dim: model hidden dimension (default 384)
        sigma: Gaussian width for attractor blobs (default 0.15)
            Smaller σ = tighter wells (model must be more precise)
            Larger σ = broader pull (more forgiving)
        fun_weight: scale factor for the loss term (default 0.1)
            Keep small — fun is a bonus, not the objective.
    """

    def __init__(
        self,
        hidden_dim: int = 384,
        sigma: float = 0.15,
        fun_weight: float = 0.1,
    ):
        super().__init__()
        self.sigma = sigma
        self.fun_weight = fun_weight

        # Project hidden state → 6D tongue profile (same as GovernanceLoss)
        self.profile_head = nn.Linear(hidden_dim, 6)

        # Register attractor centers as buffer (not trained, but moved with model)
        self.register_buffer("attractors", FUN_ATTRACTORS.clone())

    def fun_score(self, profile: torch.Tensor) -> torch.Tensor:
        """
        Compute fuzzy fun score for a batch of 6D tongue profiles.

        profile: (B, 6)  — softmax-normalized tongue profiles

        Returns: (B,) fun scores in (0, 1]
          max over all attractors of the Gaussian kernel:
            score_a = exp(-||profile - center_a||² / (2σ²))
          fun_score = max_a(score_a)
        """
        # Expand for broadcasting: (B, 1, 6) vs (1, N, 6)
        p = profile.unsqueeze(1)  # (B, 1, 6)
        a = self.attractors.unsqueeze(0)  # (1, N, 6)
        diff = p - a  # (B, N, 6)
        dist_sq = (diff**2).sum(dim=-1)  # (B, N)

        # Gaussian kernel per attractor
        k = torch.exp(-dist_sq / (2 * self.sigma**2))  # (B, N)

        # Max across attractors (closest well wins)
        score, _ = k.max(dim=-1)  # (B,)
        return score

    def forward(self, hidden_states: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        hidden_states: (B, S, D)

        Returns:
            loss: scalar, fun_weight * -log(mean_fun_score + ε)
            score: (B,) fun score per sample (for logging)
        """
        # Mean-pool sequence → (B, D)
        h = hidden_states.mean(dim=1)

        # Estimate tongue profile: (B, 6), sums to 1
        profile = F.softmax(self.profile_head(h), dim=-1)

        score = self.fun_score(profile)  # (B,)

        # Loss: -log(score + ε) — minimizing this = increasing fun score
        eps = 1e-8
        loss = self.fun_weight * (-torch.log(score + eps)).mean()

        return loss, score


# =============================================================================
# TRIPLE-ANCHOR DUAL LOSS (sonar + governance + fun)
# =============================================================================


def triple_loss(
    sonar_loss: torch.Tensor,
    gov_loss: torch.Tensor,
    fun_loss: torch.Tensor,
    step: int,
    rotation_period: int = 200,
    fun_weight: float = 0.1,
) -> Tuple[torch.Tensor, float, float]:
    """
    Blend sonar, governance, and fun losses.

    The sonar↔governance rotation is unchanged. Fun is additive:
      L = α·L_sonar + (1-α)·L_gov + fun_weight·L_fun

    Args:
        fun_weight: scale on fun loss (default 0.1 — bonus not objective)

    Returns:
        total_loss, alpha (sonar weight), fun_score_estimate
    """
    phase = 2 * math.pi * step / rotation_period
    alpha = (1.0 + math.cos(phase)) / 2.0
    total = alpha * sonar_loss + (1.0 - alpha) * gov_loss + fun_loss
    return total, alpha


# =============================================================================
# DEMO: VISUALIZE ATTRACTORS
# Run this file directly to see the attractor landscape.
# =============================================================================

if __name__ == "__main__":
    print("FUN ATTRACTOR DEMO")
    print("=" * 60)
    print(f"Attractor count: {len(FUN_ATTRACTORS)}")
    print()

    for i, center in enumerate(FUN_ATTRACTORS):
        nonzero = [(TONGUE_NAMES[j], f"{center[j]:.3f}") for j in range(6) if center[j] > 0]
        label = "+".join(f"{n}({v})" for n, v in nonzero)
        print(f"  Attractor {i:02d}: [{label}]")

    print()
    print("Governance cost at each attractor center:")
    for _i, center in enumerate(FUN_ATTRACTORS):
        phi_w = PHI_WEIGHTS
        d = (center * phi_w).sum() / 27.42
        R = 5.0
        cost = R ** (d.item() ** 2)
        nonzero = [TONGUE_NAMES[j] for j in range(6) if center[j] > 0]
        label = "+".join(nonzero)
        print(f"  {label:<20} d={d.item():.3f}  H(d,5)={cost:.3f}")

    print()

    # Test fun score for some profiles
    model = FunAttractorLoss(hidden_dim=384, sigma=0.15)
    test_profiles = [
        ("KO-dominant (safe)", [0.9, 0.05, 0.02, 0.01, 0.01, 0.01]),
        ("KO+AV blend (fun zone)", [0.5, 0.5, 0.0, 0.0, 0.0, 0.0]),
        ("KO+RU blend (fun zone)", [0.5, 0.0, 0.5, 0.0, 0.0, 0.0]),
        ("DR-dominant (adversarial)", [0.01, 0.01, 0.01, 0.01, 0.01, 0.95]),
        ("Uniform", [1 / 6] * 6),
        ("KO+AV+RU triple", [1 / 3, 1 / 3, 1 / 3, 0.0, 0.0, 0.0]),
    ]

    print("Fun score at test profiles (sigma=0.15):")
    for label, profile in test_profiles:
        p = torch.tensor(profile, dtype=torch.float32).unsqueeze(0)
        score = model.fun_score(p).item()
        bar = "#" * int(score * 20)
        print(f"  {label:<32}  fun={score:.4f}  {bar}")
