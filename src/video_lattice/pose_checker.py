"""
Pose checker — did the hand/body stay true to the control sketch?

Usage pattern:
  1. Produce a control sketch from reference landmarks.
  2. Run the generator / UE5 renderer to produce a frame.
  3. Run a pose estimator on the generated frame to get output landmarks.
  4. Call PoseChecker.check(reference, generated) to measure drift.
  5. If verdict != PASS, feed correction back into the generator.

The checker embeds both sets of landmarks into the same PoincareLattice
using the polygon feature vectors from pose_polygons.py, then computes
the hyperbolic distance between them. Per-chain (arm, leg, finger)
distances surface exactly which body part the generator got wrong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence

import numpy as np

from .poincare_lattice import PoincareLattice
from .pose_polygons import (
    BODY_CHAINS,
    HAND_FINGERS,
    BodyLandmark,
    HandLandmark,
    Landmark,
    angle_at,
    body_polygon_features,
    hand_polygon_features,
    polygon_points,
)

_PHI = (1 + math.sqrt(5)) / 2


class PoseVerdict(Enum):
    PASS = "pass"  # drift below soft threshold — generator is on track
    SOFT_FAIL = "soft"  # drift above soft but below hard — inject mild correction
    HARD_FAIL = "hard"  # drift above hard threshold — regenerate or use correction


@dataclass
class ChainCheck:
    """Per-body-part drift result."""

    name: str  # "left_arm", "thumb", etc.
    reference_angle: float  # joint angle in radians
    generated_angle: float
    angle_delta: float  # |ref - gen| in radians
    hyperbolic_distance: float  # full feature-vector distance in Poincaré ball


@dataclass
class PoseCheckResult:
    """Full result of one pose check comparison."""

    pose_type: str  # "hand" or "body"
    overall_drift: float  # hyperbolic distance between feature vectors
    cost_signal: float  # R^(d²) nonlinear scaling
    verdict: PoseVerdict
    chain_checks: List[ChainCheck] = field(default_factory=list)
    worst_chain: Optional[str] = None
    correction_vector: Optional[np.ndarray] = None  # ref_embedding - gen_embedding

    def to_dict(self) -> dict:
        return {
            "pose_type": self.pose_type,
            "overall_drift": round(self.overall_drift, 5),
            "cost_signal": round(self.cost_signal, 5),
            "verdict": self.verdict.value,
            "worst_chain": self.worst_chain,
            "chain_checks": [
                {
                    "chain": c.name,
                    "angle_delta_deg": round(math.degrees(c.angle_delta), 2),
                    "hyperbolic_distance": round(c.hyperbolic_distance, 5),
                }
                for c in sorted(self.chain_checks, key=lambda c: c.hyperbolic_distance, reverse=True)
            ],
        }


class PoseChecker:
    """Compares reference and generated pose landmarks using hyperbolic distance.

    Args:
        feature_dim: PoincareLattice dimension — set to the feature vector size.
                     hand_polygon_features → 17, body_polygon_features → 18.
                     Pass None to auto-detect from first check call.
        soft_threshold: aggregate drift below this → PASS
        hard_threshold: aggregate drift above this → HARD_FAIL
        cost_base: R in R^(d²) nonlinear cost
    """

    def __init__(
        self,
        feature_dim: Optional[int] = None,
        soft_threshold: float = 0.8,
        hard_threshold: float = 2.0,
        cost_base: float = _PHI,
    ) -> None:
        self.feature_dim = feature_dim
        self.soft_threshold = soft_threshold
        self.hard_threshold = hard_threshold
        self.cost_base = cost_base
        self._lattice: Optional[PoincareLattice] = None

    def _get_lattice(self, dim: int) -> PoincareLattice:
        if self._lattice is None or self._lattice.dim != dim:
            self._lattice = PoincareLattice(dim=dim, name="pose_check")
        return self._lattice

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def check_hand(
        self,
        reference: Sequence[Landmark],
        generated: Sequence[Landmark],
    ) -> PoseCheckResult:
        """Compare two hand landmark sets."""
        ref_feat = hand_polygon_features(reference)
        gen_feat = hand_polygon_features(generated)
        chain_checks = self._finger_chain_checks(reference, generated)
        return self._build_result("hand", ref_feat, gen_feat, chain_checks)

    def check_body(
        self,
        reference: Sequence[Landmark],
        generated: Sequence[Landmark],
    ) -> PoseCheckResult:
        """Compare two body landmark sets."""
        ref_feat = body_polygon_features(reference)
        gen_feat = body_polygon_features(generated)
        chain_checks = self._body_chain_checks(reference, generated)
        return self._build_result("body", ref_feat, gen_feat, chain_checks)

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_result(
        self,
        pose_type: str,
        ref_feat: np.ndarray,
        gen_feat: np.ndarray,
        chain_checks: List[ChainCheck],
    ) -> PoseCheckResult:
        dim = len(ref_feat)
        lattice = self._get_lattice(dim)
        ref_emb = lattice.embed(ref_feat)
        gen_emb = lattice.embed(gen_feat)
        dist = lattice.distance(ref_emb, gen_emb)
        cost = self.cost_base ** (dist * dist) if dist > 0 else 1.0

        if dist < self.soft_threshold:
            verdict = PoseVerdict.PASS
        elif dist < self.hard_threshold:
            verdict = PoseVerdict.SOFT_FAIL
        else:
            verdict = PoseVerdict.HARD_FAIL

        worst = max(chain_checks, key=lambda c: c.hyperbolic_distance, default=None)
        correction = ref_emb - gen_emb  # pull gen back toward ref

        return PoseCheckResult(
            pose_type=pose_type,
            overall_drift=dist,
            cost_signal=cost,
            verdict=verdict,
            chain_checks=chain_checks,
            worst_chain=worst.name if worst else None,
            correction_vector=correction,
        )

    def _finger_chain_checks(
        self,
        reference: Sequence[Landmark],
        generated: Sequence[Landmark],
    ) -> List[ChainCheck]:
        checks = []
        ref_mapped = {i: lm for i, lm in enumerate(reference)}
        gen_mapped = {i: lm for i, lm in enumerate(generated)}
        # Per-finger 2D lattice (just the chain segment vectors)
        chain_lattice = PoincareLattice(dim=2, name="finger_chain")
        for name, chain in HAND_FINGERS.items():
            if len(chain) < 3:
                continue
            ref_pts = np.array([ref_mapped[int(i)].xy() for i in chain])
            gen_pts = np.array([gen_mapped[int(i)].xy() for i in chain])
            ref_angle = angle_at(ref_pts[0], ref_pts[2], ref_pts[-1])
            gen_angle = angle_at(gen_pts[0], gen_pts[2], gen_pts[-1])
            # Embed the tip vector relative to MCP as a 2D point
            ref_tip_vec = ref_pts[-1] - ref_pts[1]
            gen_tip_vec = gen_pts[-1] - gen_pts[1]
            re = chain_lattice.embed(ref_tip_vec)
            ge = chain_lattice.embed(gen_tip_vec)
            checks.append(
                ChainCheck(
                    name=name,
                    reference_angle=ref_angle,
                    generated_angle=gen_angle,
                    angle_delta=abs(ref_angle - gen_angle),
                    hyperbolic_distance=chain_lattice.distance(re, ge),
                )
            )
        return checks

    def _body_chain_checks(
        self,
        reference: Sequence[Landmark],
        generated: Sequence[Landmark],
    ) -> List[ChainCheck]:
        checks = []
        ref_mapped = {i: lm for i, lm in enumerate(reference)}
        gen_mapped = {i: lm for i, lm in enumerate(generated)}
        chain_lattice = PoincareLattice(dim=2, name="body_chain")
        for name, chain in BODY_CHAINS.items():
            ref_pts = np.array([ref_mapped[int(i)].xy() for i in chain if int(i) in ref_mapped])
            gen_pts = np.array([gen_mapped[int(i)].xy() for i in chain if int(i) in gen_mapped])
            if len(ref_pts) < 3 or len(gen_pts) < 3:
                continue
            ref_angle = angle_at(ref_pts[0], ref_pts[1], ref_pts[2])
            gen_angle = angle_at(gen_pts[0], gen_pts[1], gen_pts[2])
            # Embed the distal-segment direction as 2D
            ref_seg = ref_pts[2] - ref_pts[1]
            gen_seg = gen_pts[2] - gen_pts[1]
            re = chain_lattice.embed(ref_seg)
            ge = chain_lattice.embed(gen_seg)
            checks.append(
                ChainCheck(
                    name=name,
                    reference_angle=ref_angle,
                    generated_angle=gen_angle,
                    angle_delta=abs(ref_angle - gen_angle),
                    hyperbolic_distance=chain_lattice.distance(re, ge),
                )
            )
        return checks
