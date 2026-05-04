"""Hierarchical JEPA wrapper over the existing SCBE three-level stack.

Stacks the three encoders we already have:

- L1: tile     -> ``poly_embedded_jepa.build_poly_embedding``
- L2: tongue   -> ``tri_braid_embedding.tri_braid_signature``
- L3: chromatic -> ``tri_cone_embedding.tri_cone_signature``

H-JEPA (LeCun, "A Path Towards Autonomous Machine Intelligence", 2022)
proposes a stack of JEPAs where each higher level represents longer-
horizon / more abstract content, with predictors cascading lower-level
predictions into the higher-level latent space. The predictor at level
N produces the level-N representation given only level-(N-1)'s
predictor output (not its target) -- so the higher level is a function
of the prediction chain, not the encoder chain.

For each level we compute a hyperbolic loss in the Poincare ball, the
same arcosh formula SCBE uses at L5 and that GeoWorld (arXiv 2602.23058,
Feb 2026) uses for its hyperbolic JEPA training objective. The
exponential map at the origin -- exp_0(v) = tanh(||v||) * v / ||v|| --
maps any finite Euclidean vector into the open ball, so the d_H
denominator never collapses.

A triangle-inequality regulariser, also borrowed from GeoWorld's
geometric reinforcement-learning loss, projects each level's prediction
into a common chromatic 3D space and penalises the case where the
top-to-bottom geodesic exceeds the sum of intermediate geodesics. That
catches inconsistency in the hierarchy: if the chromatic-level
prediction lives somewhere the tile- and tongue-level predictions do
not jointly imply, the residual lights up.

The current SCBE stack is deterministic (hash-derived latents, neighbor-
graph smoothing). H-JEPA without learned weights does not optimise
anything yet; the losses are diagnostic numbers that travel with the
signature. The point of this module is the *scaffolding* -- when learned
predictors land, they slot into ``_predict_braid_components`` and
``_predict_cone_joint`` without touching the rest of the stack.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
from dataclasses import dataclass

from .poly_embedded_jepa import PolyEmbedding, build_poly_embedding
from .tri_braid_embedding import TriBraidSignature, tri_braid_signature
from .tri_cone_embedding import TriConeSignature, chromatic_project, tri_cone_signature

SCHEMA_VERSION = "scbe_hjepa_embedding_v1"

# Loss weights. L1 carries detail, L3 carries abstraction; the triangle
# residual gates whether the levels actually agree on the same concept.
DEFAULT_LOSS_WEIGHTS: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.5)

_BALL_EPSILON = 1e-9


# ---------------------------------------------------------------------------
# Hyperbolic helpers (Poincare ball, curvature c=1)
# ---------------------------------------------------------------------------


def _exp_map_origin(vec: tuple[float, ...]) -> tuple[float, ...]:
    """Map a Euclidean vector into the open Poincare ball at the origin.

    exp_0(v) = tanh(||v||) * v / ||v||. The output norm is < 1 for any
    finite input, which keeps ``_poincare_distance`` numerically stable.
    """

    norm = math.sqrt(sum(x * x for x in vec))
    if norm < _BALL_EPSILON:
        return tuple(0.0 for _ in vec)
    factor = math.tanh(norm) / norm
    return tuple(factor * x for x in vec)


def _poincare_distance(u: tuple[float, ...], v: tuple[float, ...]) -> float:
    """Hyperbolic distance in the Poincare ball with curvature c=1.

    Same formula SCBE uses at L5 of the 14-layer pipeline. Inputs must
    already lie inside the open ball (typically via ``_exp_map_origin``).
    """

    if len(u) != len(v):
        raise ValueError(f"dimension mismatch: |u|={len(u)} vs |v|={len(v)}")
    diff_sq = sum((a - b) * (a - b) for a, b in zip(u, v))
    norm_u_sq = sum(a * a for a in u)
    norm_v_sq = sum(a * a for a in v)
    denom = (1.0 - norm_u_sq) * (1.0 - norm_v_sq)
    if denom <= _BALL_EPSILON:
        # Either u or v reached the ball boundary; the geodesic diverges.
        return math.inf
    arg = 1.0 + 2.0 * diff_sq / denom
    return math.acosh(max(1.0, arg))


def _hyperbolic_loss(prediction: tuple[float, ...], target: tuple[float, ...]) -> float:
    """Hyperbolic loss after mapping both vectors into the ball."""

    return _poincare_distance(_exp_map_origin(prediction), _exp_map_origin(target))


# ---------------------------------------------------------------------------
# Predictors
# ---------------------------------------------------------------------------


def _predict_braid(poly: PolyEmbedding) -> TriBraidSignature:
    """L1 -> L2 predictor.

    Constructs a synthetic ``PolyEmbedding`` whose ``jepa_latent`` slot
    holds the L1 prediction (instead of the actual masked-tile latent),
    and runs it through ``tri_braid_signature``. The result is the
    higher-level representation we would see if only the L1 prediction
    were available.

    Governance is content-independent (depends only on coding-system
    provenance), so the predicted braid's governance channel matches the
    target braid's governance channel exactly. The L2 loss therefore
    reflects discrepancies on the fast and memory channels only -- which
    is the correct behavior: governance does not need to be predicted
    from content.
    """

    synthetic = dataclasses.replace(poly, jepa_latent=poly.jepa_prediction)
    return tri_braid_signature(synthetic)


def _predict_cone(predicted_braid: TriBraidSignature) -> TriConeSignature:
    """L2 -> L3 predictor.

    Reuses the L3 encoder (``tri_cone_signature``) on the predicted braid
    to obtain the chromatic prediction. Because the L2 predictor only
    swaps the latent slot for the prediction slot, the L3 prediction
    differs from the L3 target exactly to the degree that the L1
    prediction differs from the L1 target -- the error compounds upward.
    """

    return tri_cone_signature(predicted_braid)


# ---------------------------------------------------------------------------
# Cross-level chromatic projection (for the triangle regulariser)
# ---------------------------------------------------------------------------


def _tile_to_chromatic(latent: tuple[float, ...]) -> tuple[float, float, float]:
    """Bin a 6D tile latent into a 3D chromatic point.

    Dims (0,1) -> IR, (2,3) -> visible, (4,5) -> UV. Mean per pair so
    the result lives in the same approximate range as the chromatic
    projections of the higher levels.
    """

    if len(latent) < 6:
        raise ValueError("tile latent must be at least 6D for chromatic binning")
    return (
        (latent[0] + latent[1]) / 2.0,
        (latent[2] + latent[3]) / 2.0,
        (latent[4] + latent[5]) / 2.0,
    )


def _braid_to_chromatic(braid: TriBraidSignature) -> tuple[float, float, float]:
    """Centroid of the chromatic projection of the braid's six tongue points."""

    points = chromatic_project(braid)
    n = float(len(points))
    if n == 0.0:
        return (0.0, 0.0, 0.0)
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def _triangle_residual(
    chrom_l1: tuple[float, float, float],
    chrom_l2: tuple[float, float, float],
    chrom_l3: tuple[float, float, float],
) -> float:
    """Hyperbolic triangle-inequality residual across the three levels.

    GeoWorld (arXiv 2602.23058) penalises geodesics that violate the
    triangle inequality across consecutive predictions. Here we apply
    the same idea across abstraction levels rather than time steps:
    d_H(L1, L3) should not exceed d_H(L1, L2) + d_H(L2, L3) when the
    levels represent the same underlying concept. Residual is
    ``max(0, d13 - d12 - d23)`` and is identically zero when the points
    are co-linear on a geodesic.
    """

    p1 = _exp_map_origin(chrom_l1)
    p2 = _exp_map_origin(chrom_l2)
    p3 = _exp_map_origin(chrom_l3)
    d12 = _poincare_distance(p1, p2)
    d23 = _poincare_distance(p2, p3)
    d13 = _poincare_distance(p1, p3)
    if not (math.isfinite(d12) and math.isfinite(d23) and math.isfinite(d13)):
        return math.inf
    return max(0.0, d13 - d12 - d23)


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HJEPALevel:
    """Per-level encoder target, predictor output, and hyperbolic loss."""

    name: str
    target: tuple[float, ...]
    prediction: tuple[float, ...]
    loss: float


@dataclass(frozen=True)
class HJEPASignature:
    """Hierarchical JEPA signature over the SCBE poly/braid/cone stack."""

    schema_version: str
    poly: PolyEmbedding
    braid_target: TriBraidSignature
    braid_prediction: TriBraidSignature
    cone_target: TriConeSignature
    cone_prediction: TriConeSignature
    levels: tuple[HJEPALevel, HJEPALevel, HJEPALevel]
    triangle_residual: float
    total_loss: float
    loss_weights: tuple[float, float, float, float]
    hjepa_hash: str
    invariants: tuple[str, ...]


def _hjepa_hash(
    poly: PolyEmbedding,
    braid_target: TriBraidSignature,
    braid_prediction: TriBraidSignature,
    cone_target: TriConeSignature,
    cone_prediction: TriConeSignature,
) -> str:
    """SHA3-256 ordered hash of the full hierarchical signature.

    Includes one anchor per level (the binary packet hash, the ordered
    braid hash on each side, and the cone hash on each side) so a
    permutation of the level outputs is detectable.
    """

    hasher = hashlib.sha3_256()
    hasher.update(SCHEMA_VERSION.encode("utf-8"))
    hasher.update(b"|tile|")
    hasher.update(poly.binary_packet_sha256.encode("utf-8"))
    hasher.update(b"|tongue_target|")
    hasher.update(braid_target.ordered_hash.encode("utf-8"))
    hasher.update(b"|tongue_prediction|")
    hasher.update(braid_prediction.ordered_hash.encode("utf-8"))
    hasher.update(b"|chromatic_target|")
    hasher.update(cone_target.cone_hash.encode("utf-8"))
    hasher.update(b"|chromatic_prediction|")
    hasher.update(cone_prediction.cone_hash.encode("utf-8"))
    return hasher.hexdigest()


def hjepa_signature(
    content: str,
    *,
    masked_row: int = 0,
    masked_col: int = 0,
    loss_weights: tuple[float, float, float, float] = DEFAULT_LOSS_WEIGHTS,
) -> HJEPASignature:
    """Build the full three-level H-JEPA signature for a content string.

    Cascades the existing encoders and runs deterministic predictors at
    each level, computes hyperbolic losses against the next-level target,
    and adds a chromatic-space triangle-inequality residual.
    """

    if len(loss_weights) != 4:
        raise ValueError("loss_weights must be a 4-tuple (alpha, beta, gamma, delta)")
    alpha, beta, gamma, delta = (float(w) for w in loss_weights)

    poly = build_poly_embedding(content, masked_row=masked_row, masked_col=masked_col)
    braid_target = tri_braid_signature(poly)
    braid_prediction = _predict_braid(poly)
    cone_target = tri_cone_signature(braid_target)
    cone_prediction = _predict_cone(braid_prediction)

    # Level 1: 6D tile latent vs predicted tile latent.
    target_l1 = tuple(poly.jepa_latent)
    prediction_l1 = tuple(poly.jepa_prediction)
    loss_l1 = _hyperbolic_loss(prediction_l1, target_l1)

    # Level 2: concatenated (fast, memory, governance) vectors. Governance
    # contributes zero by construction (predictor preserves it).
    target_l2 = tuple(braid_target.fast) + tuple(braid_target.memory) + tuple(braid_target.governance)
    prediction_l2 = tuple(braid_prediction.fast) + tuple(braid_prediction.memory) + tuple(braid_prediction.governance)
    loss_l2 = _hyperbolic_loss(prediction_l2, target_l2)

    # Level 3: 3D chromatic joint embedding.
    target_l3 = tuple(cone_target.joint_embedding)
    prediction_l3 = tuple(cone_prediction.joint_embedding)
    loss_l3 = _hyperbolic_loss(prediction_l3, target_l3)

    # Triangle residual in chromatic 3D space using the predictions only.
    chrom_l1 = _tile_to_chromatic(prediction_l1)
    chrom_l2 = _braid_to_chromatic(braid_prediction)
    chrom_l3 = (
        float(prediction_l3[0]),
        float(prediction_l3[1]),
        float(prediction_l3[2]),
    )
    triangle = _triangle_residual(chrom_l1, chrom_l2, chrom_l3)

    total = alpha * loss_l1 + beta * loss_l2 + gamma * loss_l3 + delta * triangle

    levels = (
        HJEPALevel(name="tile", target=target_l1, prediction=prediction_l1, loss=round(loss_l1, 8)),
        HJEPALevel(name="tongue", target=target_l2, prediction=prediction_l2, loss=round(loss_l2, 8)),
        HJEPALevel(name="chromatic", target=target_l3, prediction=prediction_l3, loss=round(loss_l3, 8)),
    )

    return HJEPASignature(
        schema_version=SCHEMA_VERSION,
        poly=poly,
        braid_target=braid_target,
        braid_prediction=braid_prediction,
        cone_target=cone_target,
        cone_prediction=cone_prediction,
        levels=levels,
        triangle_residual=round(triangle, 8),
        total_loss=round(total, 8),
        loss_weights=(alpha, beta, gamma, delta),
        hjepa_hash=_hjepa_hash(poly, braid_target, braid_prediction, cone_target, cone_prediction),
        invariants=(
            "schema_version_matches",
            "three_levels_named_tile_tongue_chromatic",
            "level_1_dimension_is_6",
            "level_2_dimension_is_18",
            "level_3_dimension_is_3",
            "loss_at_each_level_is_non_negative",
            "loss_at_each_level_is_finite",
            "triangle_residual_is_non_negative",
            "predicted_braid_governance_matches_target_governance",
            "total_loss_is_weighted_sum_plus_triangle",
            "hjepa_hash_is_non_commutative",
        ),
    )


def verify_hjepa_signature(signature: HJEPASignature, content: str) -> dict[str, object]:
    """Verify that ``signature`` was produced from ``content`` and is consistent."""

    rebuilt = hjepa_signature(
        content,
        masked_row=signature.poly.tile_node.row,
        masked_col=signature.poly.tile_node.col,
        loss_weights=signature.loss_weights,
    )
    failed: list[str] = []
    if rebuilt.hjepa_hash != signature.hjepa_hash:
        failed.append("hjepa_hash_mismatch")
    if rebuilt.schema_version != signature.schema_version:
        failed.append("schema_version_mismatch")
    if abs(rebuilt.total_loss - signature.total_loss) > 1e-6:
        failed.append("total_loss_drift")
    if abs(rebuilt.triangle_residual - signature.triangle_residual) > 1e-6:
        failed.append("triangle_residual_drift")
    for actual, expected in zip(rebuilt.levels, signature.levels):
        if actual.name != expected.name:
            failed.append(f"level_name_mismatch_{expected.name}")
        if abs(actual.loss - expected.loss) > 1e-6:
            failed.append(f"loss_drift_{expected.name}")
    return {
        "ok": not failed,
        "failed": tuple(failed),
        "schema_version": signature.schema_version,
    }
