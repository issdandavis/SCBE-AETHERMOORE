"""Tri-chromatic cone embedding layer with signed shadow projections.

Sits between ``tri_braid_embedding`` (topological fingerprint with
fast/memory/governance vectors) and ``src/governance/trichromatic_governance.py``
(IR / visible / UV per-tongue band scoring). This module realises the
"three-circle Venn / soap-bubble" geometric reading the operator asked
for, with the refinement that every projection has both a positive
(lit) and negative (shadow) representation — borrowed from the existing
``src/governance/negative_tongue_lattice.py`` and the academic Shadow
Cones framework (Yu, Sala, Re; ICLR 2024).

Pipeline:

1. Project the 6-tongue tri-braid into a 3D chromatic space whose axes
   are the trichromatic bands (infrared / visible / ultraviolet). The
   channel-to-band mapping mirrors the trichromatic governance article:
   memory ↔ IR, governance ↔ visible, fast ↔ UV.
2. Sign-flip each chromatic component to obtain a *negative shadow* set
   of points (``neg = 1 - pos``) — the same lazy negative-space trick
   used by ``NegativeTongueLattice``. No additional storage; the shadow
   evaporates after the signature is computed.
3. Build six cones: one positive entailment cone per band (lit side)
   and one negative shadow cone per band (anti-lit side). Each cone has
   an apex at its centroid, an axis along its band, and a half-aperture
   that tightens as the band's activation grows.
4. Read the soap-bubble overlap structure:
   - ``triple_intersection_score`` = depth of the joint (positive)
     embedding inside all three positive cones (max concept contact).
   - ``triple_shadow_score`` = depth of the joint shadow inside all
     three negative shadow cones (max anti-concept contact).
   - ``interference_score`` = signed product of the two — high positive
     when positive and shadow simultaneously activate, the classic
     adversarial-tension signal of the negative tongue lattice.
5. Governance reads the (positive count, shadow count) tuple:
   - 3 positive ∧ 0 shadow → ALLOW (clean concept, no anti-evidence)
   - 3 positive ∧ ≥1 shadow → QUARANTINE (interference / tension)
   - 0 positive ∧ 3 shadow → DENY (clean anti-concept)
   - everything else → ESCALATE (mixed signal, needs human/quorum)
6. Plateau imbalance measures how far the three cone activations stray
   from a perfectly symmetric soap bubble (equal magnitudes). Zero
   imbalance = minimum-surface equilibrium where the three cones meet
   at 120-degree dihedrals.

The module is pure stdlib: it avoids numpy so it can run in the same
constrained sandbox as the rest of the SCBE python core.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .tri_braid_embedding import TriBraidSignature

SCHEMA_VERSION = "scbe_tri_cone_embedding_v1"

ALLOW = "ALLOW"
QUARANTINE = "QUARANTINE"
ESCALATE = "ESCALATE"
DENY = "DENY"

_BANDS: tuple[str, str, str] = ("infrared", "visible", "ultraviolet")
_BAND_AXES: dict[str, tuple[float, float, float]] = {
    "infrared": (1.0, 0.0, 0.0),
    "visible": (0.0, 1.0, 0.0),
    "ultraviolet": (0.0, 0.0, 1.0),
}

# Each tri-braid channel maps to one chromatic band. The mapping mirrors
# the existing trichromatic_governance article:
#   memory     -> infrared  (slow, accumulated state)
#   governance -> visible   (explicit policy lane)
#   fast       -> ultraviolet (emergent / spike state)
_CHANNEL_TO_BAND: dict[str, str] = {
    "memory": "infrared",
    "governance": "visible",
    "fast": "ultraviolet",
}

# Cone aperture rule. Aperture grows with activation: a bright (high
# activation) band casts a wide entailment cone, a dim band claims a
# narrow strip. The range straddles the soap-bubble equilibrium angle
# arccos(1/sqrt(3)) ≈ 54.74° so that activations near 0.5 give cones
# that just meet at the cube diagonal — the geometric realisation of
# the operator's "minimum contact / maximum concept contact" intuition.
_MIN_HALF_APERTURE_RAD = math.radians(25.0)
_MAX_HALF_APERTURE_RAD = math.radians(80.0)


@dataclass(frozen=True)
class ChromaticCone:
    """One band-aligned hyperbolic-style entailment cone.

    A signed cone: ``polarity == "+1"`` is the positive entailment
    (lit) side, ``polarity == "-1"`` is the negative shadow side. The
    pair of (positive, negative) cones for a single band approximates
    the Shadow Cones umbra/penumbra reading on a 3D chromatic axis.
    """

    band: str
    polarity: int  # +1 = positive (lit), -1 = negative (shadow)
    apex: tuple[float, float, float]
    axis: tuple[float, float, float]
    half_aperture_rad: float
    activation: float
    membership: bool  # whether the joint embedding for this polarity is inside


@dataclass(frozen=True)
class TriConeSignature:
    """Soap-bubble triple-overlap reading of a tri-braid signature.

    Carries six cones (three positive entailment + three negative
    shadow), the two joint embeddings (lit centroid and shadow centroid),
    and the four scores that summarise their interaction: triple
    intersection (lit), triple shadow (anti-lit), interference (their
    signed product), and Plateau imbalance.
    """

    schema_version: str
    cones: tuple[ChromaticCone, ...]  # 6 entries: pos_IR, pos_vis, pos_UV, neg_IR, neg_vis, neg_UV
    chromatic_points: tuple[tuple[float, float, float], ...]
    chromatic_shadow_points: tuple[tuple[float, float, float], ...]
    joint_embedding: tuple[float, float, float]
    joint_shadow: tuple[float, float, float]
    triple_intersection_score: float  # positive cones at joint_embedding
    triple_shadow_score: float  # negative cones at joint_shadow
    interference_score: float  # signed product, > 0 = adversarial tension
    pairwise_overlap: tuple[float, float, float]  # positive (IR-vis, vis-UV, UV-IR)
    pairwise_shadow_overlap: tuple[float, float, float]  # negative shadow
    plateau_imbalance: float
    positive_membership_count: int
    shadow_membership_count: int
    cone_governance: str
    cone_hash: str
    invariants: tuple[str, ...]


# ---------------------------------------------------------------------------
# Chromatic projection
# ---------------------------------------------------------------------------


def _sigmoid(x: float) -> float:
    """Numerically-stable sigmoid in (0, 1)."""

    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def chromatic_project(
    braid: TriBraidSignature,
) -> tuple[tuple[float, float, float], ...]:
    """Project a tri-braid signature into 6 positive (lit) chromatic points.

    Each tongue index ``i`` maps to a (ir, visible, uv) triple via the
    fixed channel-to-band mapping. Components are squashed through a
    sigmoid so each chromatic axis lives in (0, 1) — the same range used
    by the existing trichromatic governance scorer.
    """

    if not (len(braid.fast) == len(braid.memory) == len(braid.governance)):
        raise ValueError("tri-braid channel vectors must share length")

    points: list[tuple[float, float, float]] = []
    for idx in range(len(braid.fast)):
        ir = _sigmoid(braid.memory[idx])
        vis = _sigmoid(braid.governance[idx])
        uv = _sigmoid(braid.fast[idx])
        points.append((ir, vis, uv))
    return tuple(points)


def chromatic_shadow(
    chromatic_points: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], ...]:
    """Sign-flip each chromatic component to obtain the negative-shadow points.

    Reuses the lazy negative-space trick from
    ``src/governance/negative_tongue_lattice.py``: ``neg_p = 1 - p``.
    No additional storage; callers are expected to discard the shadow
    after the signature is built.
    """

    return tuple((1.0 - p[0], 1.0 - p[1], 1.0 - p[2]) for p in chromatic_points)


# ---------------------------------------------------------------------------
# Cone construction
# ---------------------------------------------------------------------------


def _centroid(
    points: tuple[tuple[float, float, float], ...],
) -> tuple[float, float, float]:
    if not points:
        return (0.0, 0.0, 0.0)
    n = float(len(points))
    sx = sum(p[0] for p in points) / n
    sy = sum(p[1] for p in points) / n
    sz = sum(p[2] for p in points) / n
    return (sx, sy, sz)


def _band_activation(points: tuple[tuple[float, float, float], ...], band_index: int) -> float:
    """Mean activation of a chromatic band across the 6 tongue points."""

    if not points:
        return 0.0
    return sum(p[band_index] for p in points) / float(len(points))


def _half_aperture_from_activation(activation: float) -> float:
    """Map an activation in [0, 1] to a half-aperture in radians.

    Higher activation -> tighter cone (band is committed). Lower
    activation -> wider cone (band is tentative). The interpolation is
    linear in radians for predictability under property tests.
    """

    a = max(0.0, min(1.0, activation))
    return _MAX_HALF_APERTURE_RAD - a * (_MAX_HALF_APERTURE_RAD - _MIN_HALF_APERTURE_RAD)


def _build_cone(
    band: str,
    polarity: int,
    apex: tuple[float, float, float],
    activation: float,
    joint: tuple[float, float, float],
) -> ChromaticCone:
    """Construct a signed entailment cone for ``band`` and ``polarity``.

    ``polarity = +1`` builds the positive (lit) cone whose axis points
    along the band direction; ``polarity = -1`` builds the negative
    shadow cone with the axis flipped, modelling the umbra cast by the
    sign-flipped tongue cloud. The activation drives the half-aperture
    identically for both sides so the soap-bubble symmetry holds.
    """

    if polarity not in (1, -1):
        raise ValueError(f"polarity must be +1 or -1, got {polarity!r}")
    base_axis = _BAND_AXES[band]
    axis = (
        base_axis[0] * polarity,
        base_axis[1] * polarity,
        base_axis[2] * polarity,
    )
    half_aperture = _half_aperture_from_activation(activation)
    margin = _cone_margin(joint, apex, axis, half_aperture)
    return ChromaticCone(
        band=band,
        polarity=polarity,
        apex=apex,
        axis=axis,
        half_aperture_rad=round(half_aperture, 8),
        activation=round(activation, 8),
        membership=margin >= 0.0,
    )


# ---------------------------------------------------------------------------
# Cone containment math
# ---------------------------------------------------------------------------


def _vec_sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vec_norm(v: tuple[float, float, float]) -> float:
    return math.sqrt(_vec_dot(v, v))


def _cone_margin(
    point: tuple[float, float, float],
    apex: tuple[float, float, float],
    axis: tuple[float, float, float],
    half_aperture_rad: float,
) -> float:
    """Signed cone-membership margin.

    Positive = strictly inside the cone (the smaller the value the
    closer to the boundary). Zero = on the boundary. Negative = outside.

    The margin is measured in cosine space: ``cos(angle) - cos(half_aperture)``.
    A point at the apex returns 0.0 by convention (the apex is on every
    cone boundary simultaneously; it is treated as "just outside" so the
    decision is symmetric across all three bands).
    """

    rel = _vec_sub(point, apex)
    rel_norm = _vec_norm(rel)
    if rel_norm == 0.0:
        return 0.0
    cos_angle = _vec_dot(rel, axis) / rel_norm
    return cos_angle - math.cos(half_aperture_rad)


# ---------------------------------------------------------------------------
# Joint embedding + soap-bubble plateau metrics
# ---------------------------------------------------------------------------


def _joint_embedding(
    chromatic_points: tuple[tuple[float, float, float], ...],
    activations: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Activation-weighted centroid of the chromatic points.

    Each point contributes proportionally to the sum of the three
    activations evaluated at its chromatic coordinates: a tongue that
    lights up strongly across all bands pulls the joint embedding
    toward its position. This is the "maximum concept contact" centroid
    the operator asked for.
    """

    if not chromatic_points:
        return (0.0, 0.0, 0.0)

    weights = []
    for ir, vis, uv in chromatic_points:
        # Weight = sum of band intensities at this tongue, scaled by the
        # band's overall activation. A band with low activation cannot
        # drag the joint embedding toward an outlier tongue.
        w = ir * activations[0] + vis * activations[1] + uv * activations[2]
        weights.append(max(w, 0.0))

    total = sum(weights)
    if total == 0.0:
        return _centroid(chromatic_points)

    sx = sum(p[0] * w for p, w in zip(chromatic_points, weights)) / total
    sy = sum(p[1] * w for p, w in zip(chromatic_points, weights)) / total
    sz = sum(p[2] * w for p, w in zip(chromatic_points, weights)) / total
    return (sx, sy, sz)


def _pairwise_overlap(
    cones: tuple[ChromaticCone, ChromaticCone, ChromaticCone],
    joint: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Pairwise cone-membership overlap depth at ``joint``.

    Returns a triple ``(band0-band1, band1-band2, band2-band0)`` of
    harmonic-mean margins. Each entry is positive when ``joint`` lies
    inside both cones in the pair; the smaller the binding margin, the
    closer the pair is to a "minimal contact" rim touch (the soap-film
    triple-junction limit). Works for either polarity tuple.
    """

    overlaps: list[float] = []
    pairs = ((0, 1), (1, 2), (2, 0))
    for i, j in pairs:
        m_i = _cone_margin(joint, cones[i].apex, cones[i].axis, cones[i].half_aperture_rad)
        m_j = _cone_margin(joint, cones[j].apex, cones[j].axis, cones[j].half_aperture_rad)
        if m_i <= 0.0 or m_j <= 0.0:
            overlaps.append(min(m_i, m_j))
        else:
            # Harmonic mean rewards balanced overlap (soap bubble likes
            # equal radii) and penalises asymmetric pair contact.
            overlaps.append(2.0 * m_i * m_j / (m_i + m_j))
    return tuple(overlaps)  # type: ignore[return-value]


def _plateau_imbalance(activations: tuple[float, float, float]) -> float:
    """How far the three band activations are from a soap-bubble equilibrium.

    A perfectly symmetric soap bubble has equal radii on each face
    (all activations equal). Imbalance is the standard deviation of the
    three activations, scaled by the maximum possible deviation so the
    output is in [0, 1].
    """

    a, b, c = activations
    mean = (a + b + c) / 3.0
    var = ((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2) / 3.0
    sd = math.sqrt(var)
    # Maximum sd at activations like (1, 0, 0) is sqrt(2/9) = ~0.4714.
    max_sd = math.sqrt(2.0 / 9.0)
    return min(1.0, sd / max_sd) if max_sd > 0.0 else 0.0


def _triple_intersection_score(
    cones: tuple[ChromaticCone, ChromaticCone, ChromaticCone],
    joint: tuple[float, float, float],
) -> float:
    """Soap-bubble triple-overlap depth at ``joint`` for any 3-cone slice.

    Returns the minimum cone margin: positive ⇒ joint embedding is
    inside all three cones (the "maximum concept contact" core).
    Negative ⇒ at least one cone has rejected the joint embedding.
    Used for both the positive (lit) triple and the negative (shadow)
    triple.
    """

    margins = [_cone_margin(joint, c.apex, c.axis, c.half_aperture_rad) for c in cones]
    return min(margins)


def _interference_score(triple_intersection_score: float, triple_shadow_score: float) -> float:
    """Signed product of the lit and shadow triple-overlap depths.

    Mirrors ``NegativeTongueLattice.lattice_energy`` semantically: when
    both the positive and negative cone interiors simultaneously admit
    the joint embedding, the product is positive — the adversarial
    tension signal where a concept reads as both endorsed and
    anti-endorsed at once. When one side rejects, the product is
    non-positive and the system should fall back to the per-side
    membership counts for the governance decision.
    """

    return round(triple_intersection_score * triple_shadow_score, 10)


def _signed_governance(positive_membership_count: int, shadow_membership_count: int) -> str:
    """Map (positive, shadow) cone-membership counts to a governance class.

    The reading is:

    - 3 positive ∧ 0 shadow → ALLOW (clean concept, no anti-evidence).
    - 3 positive ∧ ≥1 shadow → QUARANTINE (interference / tension).
    - 0 positive ∧ 3 shadow → DENY (clean anti-concept).
    - 0 positive ∧ 0..2 shadow → ESCALATE (under-supported).
    - everything else (≥1 positive or ≥1 shadow but not the above) →
      ESCALATE (mixed signal, needs quorum).
    """

    if positive_membership_count == 3 and shadow_membership_count == 0:
        return ALLOW
    if positive_membership_count == 3 and shadow_membership_count >= 1:
        return QUARANTINE
    if positive_membership_count == 0 and shadow_membership_count == 3:
        return DENY
    return ESCALATE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _cone_hash(
    cones: tuple[ChromaticCone, ...],
    joint: tuple[float, float, float],
    joint_shadow: tuple[float, float, float],
) -> str:
    """Order-dependent SHA3-256 of all cones plus both joint embeddings.

    Uses the same non-commutative digest discipline as the tri-braid
    ``ordered_hash`` so a permutation of cones (or swapping the lit and
    shadow joints) is detectable.
    """

    hasher = hashlib.sha3_256()
    for cone in cones:
        hasher.update(cone.band.encode("utf-8"))
        hasher.update(repr(cone.polarity).encode("utf-8"))
        for value in (
            *cone.apex,
            *cone.axis,
            cone.half_aperture_rad,
            cone.activation,
        ):
            hasher.update(repr(round(float(value), 10)).encode("utf-8"))
    for value in joint:
        hasher.update(repr(round(float(value), 10)).encode("utf-8"))
    hasher.update(b"|shadow|")
    for value in joint_shadow:
        hasher.update(repr(round(float(value), 10)).encode("utf-8"))
    return hasher.hexdigest()


def tri_cone_signature(braid: TriBraidSignature) -> TriConeSignature:
    """Build the tri-chromatic signed-cone signature for a tri-braid fingerprint.

    The pipeline:

    1. Project the tri-braid signature into 6 chromatic points (one per
       Sacred Tongue) using the fast/memory/governance ↔ UV/IR/visible
       mapping.
    2. Sign-flip each component to obtain the 6 negative-shadow points
       (lazy, evaporates after this call).
    3. Compute per-band activations on each side as the mean chromatic
       component.
    4. Form activation-weighted joint embeddings — one for the lit
       cloud (the "maximum concept contact" centroid) and one for the
       shadow cloud.
    5. Build six entailment cones (3 positive, 3 negative shadow). Each
       cone's membership is checked against its own polarity's joint.
    6. Read soap-bubble overlap structure: triple intersection on the
       lit side, triple shadow on the dark side, interference score as
       the signed product of the two.
    7. Aggregate membership into a governance class via the signed
       Venn-of-three reading (3-positive ∧ 0-shadow = ALLOW, etc.).
    """

    chromatic_points = chromatic_project(braid)
    shadow_points = chromatic_shadow(chromatic_points)

    # Positive cones emanate from the origin of chromatic space (the
    # "no-signal" corner) along each band axis. Shadow cones emanate
    # from the opposite corner (1, 1, 1) — the saturated anti-signal
    # corner — and point back toward the origin along the negated axis.
    # This matches the Shadow Cones umbra formulation: the cone interior
    # is the region of space the band's "light source" illuminates.
    APEX_POSITIVE = (0.0, 0.0, 0.0)
    APEX_SHADOW = (1.0, 1.0, 1.0)

    activations_pos = (
        _band_activation(chromatic_points, 0),
        _band_activation(chromatic_points, 1),
        _band_activation(chromatic_points, 2),
    )
    activations_neg = (
        _band_activation(shadow_points, 0),
        _band_activation(shadow_points, 1),
        _band_activation(shadow_points, 2),
    )

    joint = _joint_embedding(chromatic_points, activations_pos)
    joint_shadow = _joint_embedding(shadow_points, activations_neg)

    positive_cones = (
        _build_cone("infrared", +1, APEX_POSITIVE, activations_pos[0], joint),
        _build_cone("visible", +1, APEX_POSITIVE, activations_pos[1], joint),
        _build_cone("ultraviolet", +1, APEX_POSITIVE, activations_pos[2], joint),
    )
    shadow_cones = (
        _build_cone("infrared", -1, APEX_SHADOW, activations_neg[0], joint_shadow),
        _build_cone("visible", -1, APEX_SHADOW, activations_neg[1], joint_shadow),
        _build_cone("ultraviolet", -1, APEX_SHADOW, activations_neg[2], joint_shadow),
    )

    triple_score = _triple_intersection_score(positive_cones, joint)
    triple_shadow_score = _triple_intersection_score(shadow_cones, joint_shadow)
    interference = _interference_score(triple_score, triple_shadow_score)

    pairwise_pos = _pairwise_overlap(positive_cones, joint)
    pairwise_neg = _pairwise_overlap(shadow_cones, joint_shadow)
    plateau = _plateau_imbalance(activations_pos)

    positive_count = sum(1 for c in positive_cones if c.membership)
    shadow_count = sum(1 for c in shadow_cones if c.membership)
    governance = _signed_governance(positive_count, shadow_count)

    all_cones = positive_cones + shadow_cones
    cone_hash = _cone_hash(all_cones, joint, joint_shadow)

    return TriConeSignature(
        schema_version=SCHEMA_VERSION,
        cones=all_cones,
        chromatic_points=chromatic_points,
        chromatic_shadow_points=shadow_points,
        joint_embedding=tuple(round(v, 8) for v in joint),  # type: ignore[arg-type]
        joint_shadow=tuple(round(v, 8) for v in joint_shadow),  # type: ignore[arg-type]
        triple_intersection_score=round(triple_score, 8),
        triple_shadow_score=round(triple_shadow_score, 8),
        interference_score=interference,
        pairwise_overlap=tuple(round(v, 8) for v in pairwise_pos),  # type: ignore[arg-type]
        pairwise_shadow_overlap=tuple(round(v, 8) for v in pairwise_neg),  # type: ignore[arg-type]
        plateau_imbalance=round(plateau, 8),
        positive_membership_count=positive_count,
        shadow_membership_count=shadow_count,
        cone_governance=governance,
        cone_hash=cone_hash,
        invariants=(
            "channels_to_bands_fast_uv_memory_ir_governance_visible",
            "shadow_is_one_minus_positive_per_axis",
            "joint_embedding_in_unit_cube_when_inputs_finite",
            "positive_and_shadow_membership_each_in_zero_to_three",
            "governance_in_allow_quarantine_escalate_deny",
            "allow_requires_three_positive_and_zero_shadow",
            "deny_requires_zero_positive_and_three_shadow",
            "plateau_imbalance_in_zero_to_one",
            "cone_hash_is_non_commutative",
            "triple_intersection_score_is_min_of_band_margins",
            "interference_score_is_lit_times_shadow_triple_score",
        ),
    )


def verify_tri_cone_signature(signature: TriConeSignature, braid: TriBraidSignature) -> dict[str, object]:
    """Verify that ``signature`` was produced from ``braid`` and is internally consistent."""

    rebuilt = tri_cone_signature(braid)
    failed: list[str] = []
    if rebuilt.cone_hash != signature.cone_hash:
        failed.append("cone_hash_mismatch")
    if rebuilt.cone_governance != signature.cone_governance:
        failed.append("cone_governance_mismatch")
    if rebuilt.positive_membership_count != signature.positive_membership_count:
        failed.append("positive_membership_count_mismatch")
    if rebuilt.shadow_membership_count != signature.shadow_membership_count:
        failed.append("shadow_membership_count_mismatch")
    if abs(rebuilt.triple_intersection_score - signature.triple_intersection_score) > 1e-6:
        failed.append("triple_intersection_score_drift")
    if abs(rebuilt.triple_shadow_score - signature.triple_shadow_score) > 1e-6:
        failed.append("triple_shadow_score_drift")
    if abs(rebuilt.interference_score - signature.interference_score) > 1e-6:
        failed.append("interference_score_drift")
    if abs(rebuilt.plateau_imbalance - signature.plateau_imbalance) > 1e-6:
        failed.append("plateau_imbalance_drift")
    return {
        "ok": not failed,
        "failed": tuple(failed),
        "schema_version": signature.schema_version,
    }


def signed_cone_governance(positive_membership_count: int, shadow_membership_count: int) -> str:
    """Public helper exposing the signed governance map for callers."""

    if not (0 <= positive_membership_count <= 3):
        raise ValueError(f"positive_membership_count must be 0..3, got {positive_membership_count}")
    if not (0 <= shadow_membership_count <= 3):
        raise ValueError(f"shadow_membership_count must be 0..3, got {shadow_membership_count}")
    return _signed_governance(positive_membership_count, shadow_membership_count)


def tri_cone_signature_from_content(content: str) -> TriConeSignature:
    """Build a tri-chromatic cone signature directly from a content string.

    Wires the production stack so external callers (n8n bridge, CLI tools,
    governance receipts) can go from raw text to a signed cone reading in
    a single call without having to import poly_embedded_jepa and
    tri_braid_embedding themselves.
    """

    from .poly_embedded_jepa import build_poly_embedding
    from .tri_braid_embedding import tri_braid_signature

    embedding = build_poly_embedding(content or "empty content")
    braid = tri_braid_signature(embedding)
    return tri_cone_signature(braid)
