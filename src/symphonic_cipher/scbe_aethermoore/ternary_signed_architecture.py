"""
Ternary Signed Architecture — Core Primitives
==============================================

Expands binary parental trees into balanced ternary, signed binary,
and negative-base encoding for SCBE governance.

Binary is too small for ambiguity, witness states, deferred judgment,
inversion/adversarial polarity, and reconstruction under partial
information.  This module provides the richer state algebra:

    Balanced ternary {-1, 0, +1}  — core semantic state
    Signed binary   {-1, +1}     — adversarial/support polarity
    Ordinary binary {0, 1}       — cheap routing and execution control
    Base -2 negabinary            — alternating-layer correction

Architecture (Section 17 of spec):

    Level 1  binary mission split     (synthesis / verification)
    Level 2  ternary semantic fork    (positive / witness / adversarial)
    Level 3  sacred tongue bundle     (6-tongue trit output)
    Level 4  signed shadow branch     ({-1,+1} adversarial mirror)
    Level 5  reconstruction fusion    (permit / hold / deny)

Key types:
    TritVector              — d-dimensional balanced ternary vector
    SignedBinaryVector      — d-dimensional {-1,+1} polarity vector
    TernaryNode             — ternary parental tree node (3 children)
    SacredTongueTritBundle  — 6-tongue ternary output bundle
    AdversarialShadow       — signed-binary adversarial mirror branch
    NodalStack              — full 5-level architecture from spec

@module ternary_signed_architecture
@layer Layer 9 (Spectral), Layer 12 (Entropy), Layer 13 (Governance)
@axiom A4: Symmetry (balanced ternary is zero-centered)
@axiom A5: Composition (pipeline integrity across levels)
@version 1.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from .trinary import trit_consensus  # noqa: F401 — re-exported for downstream

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2

SACRED_TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

TONGUE_WEIGHTS = [PHI**k for k in range(6)]

TONGUE_SEMANTICS = {
    "KO": {+1: "intent_aligned", 0: "intent_unclear", -1: "intent_hostile"},
    "AV": {+1: "context_coherent", 0: "context_incomplete", -1: "context_contradictory"},
    "RU": {+1: "witness_validated", 0: "witness_absent", -1: "witness_falsified"},
    "CA": {+1: "logic_consistent", 0: "logic_underdetermined", -1: "logic_broken"},
    "UM": {+1: "execution_safe", 0: "execution_deferred", -1: "execution_restricted"},
    "DR": {+1: "judgment_allow", 0: "judgment_suspend", -1: "judgment_deny"},
}


# ---------------------------------------------------------------------------
# Governance decisions
# ---------------------------------------------------------------------------


class GovernanceDecision(Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


# ---------------------------------------------------------------------------
# TritVector — d-dimensional balanced ternary semantic vector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TritVector:
    """Balanced ternary vector z in {-1, 0, +1}^d."""

    values: Tuple[int, ...]

    def __post_init__(self) -> None:
        for v in self.values:
            if v not in (-1, 0, 1):
                raise ValueError(f"Trit value must be -1, 0, or +1, got {v}")

    @staticmethod
    def from_list(vals: Sequence[int]) -> TritVector:
        return TritVector(tuple(vals))

    @staticmethod
    def zeros(d: int) -> TritVector:
        return TritVector((0,) * d)

    @property
    def dim(self) -> int:
        return len(self.values)

    def negate(self) -> TritVector:
        return TritVector(tuple(-v for v in self.values))

    def __neg__(self) -> TritVector:
        return self.negate()

    def __repr__(self) -> str:
        chars = "".join({-1: "T", 0: "0", 1: "1"}[v] for v in self.values)
        return f"TritVec({chars})"


# ---------------------------------------------------------------------------
# SignedBinaryVector — d-dimensional {-1, +1} polarity vector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignedBinaryVector:
    """Signed binary vector p in {-1, +1}^d.

    Pure polarity: aligned/anti-aligned.  No neutral state.
    """

    values: Tuple[int, ...]

    def __post_init__(self) -> None:
        for v in self.values:
            if v not in (-1, 1):
                raise ValueError(f"Signed binary value must be -1 or +1, got {v}")

    @staticmethod
    def from_list(vals: Sequence[int]) -> SignedBinaryVector:
        return SignedBinaryVector(tuple(vals))

    @staticmethod
    def ones(d: int) -> SignedBinaryVector:
        return SignedBinaryVector((1,) * d)

    @property
    def dim(self) -> int:
        return len(self.values)

    def negate(self) -> SignedBinaryVector:
        return SignedBinaryVector(tuple(-v for v in self.values))

    def __neg__(self) -> SignedBinaryVector:
        return self.negate()

    def polarity_score(self) -> float:
        return sum(self.values) / len(self.values)

    def __repr__(self) -> str:
        chars = "".join("+" if v == 1 else "-" for v in self.values)
        return f"SignedBin({chars})"


# ---------------------------------------------------------------------------
# Trit agreement & sibling coherence (Section 5)
# ---------------------------------------------------------------------------


def trit_agreement(a: int, b: int) -> int:
    """Coordinate-level agreement: +1 identical, 0 one-zero, -1 opposed."""
    if a == b:
        return 1
    if a == 0 or b == 0:
        return 0
    if a == -b:
        return -1
    return 0


def sibling_coherence(za: TritVector, zb: TritVector) -> float:
    """C_ab = (1/d) * sum(agr(z_a,k, z_b,k)).  Range [-1, +1]."""
    if za.dim != zb.dim:
        raise ValueError(f"Dimension mismatch: {za.dim} vs {zb.dim}")
    d = za.dim
    return sum(trit_agreement(za.values[k], zb.values[k]) for k in range(d)) / d


# ---------------------------------------------------------------------------
# Trit reconstruction (Section 10)
# ---------------------------------------------------------------------------


def trit_reconstruction(
    vectors: Sequence[TritVector],
    weights: Optional[Sequence[float]] = None,
    theta: float = 0.5,
) -> TritVector:
    """Weighted ternary fusion: R_k = sum(w_i * z_ik), then threshold."""
    if not vectors:
        raise ValueError("Need at least one vector for reconstruction")
    d = vectors[0].dim
    for v in vectors:
        if v.dim != d:
            raise ValueError(f"All vectors must have same dimension, got {v.dim} vs {d}")

    n = len(vectors)
    w = list(weights) if weights else [1.0 / n] * n

    result = []
    for k in range(d):
        r_k = sum(w[i] * vectors[i].values[k] for i in range(n))
        if r_k > theta:
            result.append(1)
        elif r_k < -theta:
            result.append(-1)
        else:
            result.append(0)

    return TritVector(tuple(result))


# ---------------------------------------------------------------------------
# Offset stability (Section 11)
# ---------------------------------------------------------------------------


def offset_stability(z: TritVector, z_delta: TritVector) -> float:
    """S_delta = 1 - (1/d) * sum(|z_k - z_k^delta| / 2).  Range [0, 1]."""
    if z.dim != z_delta.dim:
        raise ValueError(f"Dimension mismatch: {z.dim} vs {z_delta.dim}")
    d = z.dim
    total_diff = sum(abs(z.values[k] - z_delta.values[k]) for k in range(d))
    return 1.0 - total_diff / (2.0 * d)


# ---------------------------------------------------------------------------
# Sacred Tongue Trit Bundle (Section 9)
# ---------------------------------------------------------------------------


@dataclass
class SacredTongueTritBundle:
    """6-tongue ternary output: tau = (tau_KO, tau_AV, tau_RU, tau_CA, tau_UM, tau_DR)."""

    ko: int = 0
    av: int = 0
    ru: int = 0
    ca: int = 0
    um: int = 0
    dr: int = 0

    def __post_init__(self) -> None:
        for name, val in self._items():
            if val not in (-1, 0, 1):
                raise ValueError(f"Tongue {name} must be -1, 0, or +1, got {val}")

    def _items(self) -> List[Tuple[str, int]]:
        return [
            ("KO", self.ko),
            ("AV", self.av),
            ("RU", self.ru),
            ("CA", self.ca),
            ("UM", self.um),
            ("DR", self.dr),
        ]

    def to_trit_vector(self) -> TritVector:
        return TritVector((self.ko, self.av, self.ru, self.ca, self.um, self.dr))

    @staticmethod
    def from_trit_vector(tv: TritVector) -> SacredTongueTritBundle:
        if tv.dim != 6:
            raise ValueError(f"Sacred tongue bundle requires exactly 6 dimensions, got {tv.dim}")
        v = tv.values
        return SacredTongueTritBundle(ko=v[0], av=v[1], ru=v[2], ca=v[3], um=v[4], dr=v[5])

    def weighted_score(self) -> float:
        """Phi-weighted tongue score: sum(w_l * tau_l)."""
        values = [self.ko, self.av, self.ru, self.ca, self.um, self.dr]
        return sum(TONGUE_WEIGHTS[i] * values[i] for i in range(6))

    def semantic_report(self) -> Dict[str, str]:
        report = {}
        for name, val in self._items():
            report[name] = TONGUE_SEMANTICS[name][val]
        return report

    def governance_decision(self) -> GovernanceDecision:
        """DR is hard gate; weighted score is tiebreaker."""
        if self.dr == -1:
            return GovernanceDecision.DENY

        ws = self.weighted_score()
        if ws > 2.0:
            return GovernanceDecision.ALLOW
        elif ws < -2.0:
            return GovernanceDecision.DENY
        elif ws < 0:
            return GovernanceDecision.ESCALATE
        else:
            return GovernanceDecision.QUARANTINE

    def ambiguity_count(self) -> int:
        return sum(1 for _, v in self._items() if v == 0)


# ---------------------------------------------------------------------------
# Adversarial Shadow Branch (Section 12)
# ---------------------------------------------------------------------------


@dataclass
class AdversarialShadow:
    """Signed-binary adversarial mirror.  C*(v) = C+(v) - lambda * C-(v)."""

    positive_score: float = 0.0
    negative_score: float = 0.0
    lambda_discount: float = 0.5

    @property
    def net_confidence(self) -> float:
        return self.positive_score - self.lambda_discount * self.negative_score

    @property
    def polarity(self) -> int:
        return 1 if self.net_confidence >= 0 else -1

    def to_signed_binary(self) -> SignedBinaryVector:
        return SignedBinaryVector((self.polarity,))

    def is_contested(self, threshold: float = 0.3) -> bool:
        if self.positive_score == 0:
            return self.negative_score > 0
        return (self.lambda_discount * self.negative_score / self.positive_score) > threshold


# ---------------------------------------------------------------------------
# Negative-Base Alternating Accumulator (Section 7)
# ---------------------------------------------------------------------------


def negabase_alternating_sum(layer_values: Sequence[float], layer_weights: Optional[Sequence[float]] = None) -> float:
    """S = sum((-1)^d * w_d * x_d).  Alternates polarity across depth."""
    if layer_weights is None:
        layer_weights = [1.0] * len(layer_values)

    total = 0.0
    for d, (x_d, w_d) in enumerate(zip(layer_values, layer_weights)):
        sigma_d = (-1) ** d
        total += sigma_d * w_d * x_d
    return total


# ---------------------------------------------------------------------------
# Ternary Parental Tree Node (Section 13)
# ---------------------------------------------------------------------------


class BranchType(Enum):
    POSITIVE = "positive"
    WITNESS = "witness"
    NEGATIVE = "negative"


@dataclass
class TernaryNode:
    """Ternary parental tree node: v_p -> {v_-, v_0, v_+}."""

    name: str
    depth: int = 0
    trit_output: Optional[TritVector] = None
    tongue_bundle: Optional[SacredTongueTritBundle] = None
    shadow: Optional[AdversarialShadow] = None
    child_positive: Optional[TernaryNode] = None
    child_witness: Optional[TernaryNode] = None
    child_negative: Optional[TernaryNode] = None

    @property
    def is_leaf(self) -> bool:
        return self.child_positive is None and self.child_witness is None and self.child_negative is None

    @property
    def children(self) -> List[TernaryNode]:
        result = []
        if self.child_positive is not None:
            result.append(self.child_positive)
        if self.child_witness is not None:
            result.append(self.child_witness)
        if self.child_negative is not None:
            result.append(self.child_negative)
        return result

    def child_by_branch(self, branch: BranchType) -> Optional[TernaryNode]:
        if branch == BranchType.POSITIVE:
            return self.child_positive
        elif branch == BranchType.WITNESS:
            return self.child_witness
        elif branch == BranchType.NEGATIVE:
            return self.child_negative
        return None

    def set_child(self, branch: BranchType, node: TernaryNode) -> None:
        if branch == BranchType.POSITIVE:
            self.child_positive = node
        elif branch == BranchType.WITNESS:
            self.child_witness = node
        elif branch == BranchType.NEGATIVE:
            self.child_negative = node

    def node_count(self) -> int:
        count = 1
        for child in self.children:
            count += child.node_count()
        return count

    def max_depth(self) -> int:
        if self.is_leaf:
            return self.depth
        return max(c.max_depth() for c in self.children)

    def resolve(self, theta: float = 0.5) -> TritVector:
        """Recursively fuse this subtree into a single resolved TritVector.

        Leaf nodes resolve to their own ``trit_output`` (or, if absent, to
        their tongue bundle).  Internal nodes fuse their children with
        branch-typed semantics:

          - positive child  -> constructive evidence (contributes as-is)
          - witness child   -> tentative, ambiguity-preserving (low weight)
          - negative child  -> adversarial probe; its resolved claim is
            *negated* before fusion, so a strong adversarial finding pulls
            the parent toward the opposite verdict (embedded red-team).

        Branch weights decay by phi so the constructive branch dominates
        unless the adversary finds strong counter-evidence.  A node's own
        ``trit_output``, if set, is included as an anchor.

        Raises:
            ValueError: if the subtree carries no trit data to resolve.
        """
        own = self.trit_output
        if own is None and self.tongue_bundle is not None:
            own = self.tongue_bundle.to_trit_vector()

        if self.is_leaf:
            if own is None:
                raise ValueError(f"Leaf node '{self.name}' has no trit data to resolve")
            return own

        contributions: List[TritVector] = []
        weights: List[float] = []

        if own is not None:
            contributions.append(own)
            weights.append(1.0)

        branch_weights = {
            BranchType.POSITIVE: 1.0,
            BranchType.WITNESS: 1.0 / PHI,
            BranchType.NEGATIVE: 1.0 / (PHI**2),
        }
        for branch in (BranchType.POSITIVE, BranchType.WITNESS, BranchType.NEGATIVE):
            child = self.child_by_branch(branch)
            if child is None:
                continue
            resolved = child.resolve(theta)
            if branch == BranchType.NEGATIVE:
                resolved = resolved.negate()
            contributions.append(resolved)
            weights.append(branch_weights[branch])

        if not contributions:
            raise ValueError(f"Internal node '{self.name}' has no resolvable children")

        dims = {c.dim for c in contributions}
        if len(dims) != 1:
            raise ValueError(f"Node '{self.name}' children have mismatched dimensions: {dims}")

        return trit_reconstruction(contributions, weights=weights, theta=theta)


def build_ternary_tree(name_prefix: str, max_depth: int, current_depth: int = 0) -> TernaryNode:
    """Build a complete ternary tree.  N_L = (3^(L+1) - 1) / 2 nodes."""
    node = TernaryNode(name=f"{name_prefix}_d{current_depth}", depth=current_depth)
    if current_depth < max_depth:
        node.child_positive = build_ternary_tree(f"{name_prefix}_pos", max_depth, current_depth + 1)
        node.child_witness = build_ternary_tree(f"{name_prefix}_wit", max_depth, current_depth + 1)
        node.child_negative = build_ternary_tree(f"{name_prefix}_neg", max_depth, current_depth + 1)
    return node


def ternary_tree_node_count(depth: int) -> int:
    return (3 ** (depth + 1) - 1) // 2


# ---------------------------------------------------------------------------
# Node State (Section 18)
# ---------------------------------------------------------------------------


@dataclass
class NodeState:
    """x_i = (h_i, tau_i, pi_i, mu_i)."""

    hidden: List[float] = field(default_factory=list)
    ternary: Optional[TritVector] = None
    polarity: Optional[SignedBinaryVector] = None
    memory: List[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# TriFuse — Ternary Fusion Operator (Section 18)
# ---------------------------------------------------------------------------


def tri_fuse(weighted_sum: float, theta: float = 0.5) -> int:
    """TriFuse(x) = +1 if x > theta, -1 if x < -theta, else 0."""
    if weighted_sum > theta:
        return 1
    elif weighted_sum < -theta:
        return -1
    return 0


def fuse_node_states(
    child_states: Sequence[NodeState],
    child_weights: Sequence[float],
    shadow_states: Optional[Sequence[NodeState]] = None,
    shadow_weights: Optional[Sequence[float]] = None,
    theta: float = 0.5,
) -> TritVector:
    """F(P) = TriFuse(sum(w_i * tau_i) + sum(lambda_j * pi_j))."""
    if not child_states:
        raise ValueError("Need at least one child state")

    d = None
    for cs in child_states:
        if cs.ternary is not None:
            d = cs.ternary.dim
            break
    if d is None:
        raise ValueError("At least one child must have a ternary vector")

    accum = [0.0] * d
    for i, cs in enumerate(child_states):
        if cs.ternary is not None:
            for k in range(d):
                accum[k] += child_weights[i] * cs.ternary.values[k]

    if shadow_states and shadow_weights:
        for j, ss in enumerate(shadow_states):
            if ss.polarity is not None:
                for k in range(min(d, ss.polarity.dim)):
                    accum[k] += shadow_weights[j] * ss.polarity.values[k]

    return TritVector(tuple(tri_fuse(accum[k], theta) for k in range(d)))


# ---------------------------------------------------------------------------
# Nodal Stack — Full 5-Level Architecture (Section 17)
# ---------------------------------------------------------------------------


class MissionChannel(Enum):
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"


@dataclass
class NodalStackConfig:
    reconstruction_theta: float = 0.5
    shadow_lambda: float = 0.5
    shadow_contest_threshold: float = 0.3
    tongue_allow_threshold: float = 2.0
    tongue_deny_threshold: float = -2.0


DEFAULT_NODAL_CONFIG = NodalStackConfig()


@dataclass
class NodalStackResult:
    channel: MissionChannel
    positive_bundle: SacredTongueTritBundle
    witness_bundle: SacredTongueTritBundle
    negative_bundle: SacredTongueTritBundle
    shadow: AdversarialShadow
    fused_bundle: SacredTongueTritBundle
    decision: GovernanceDecision
    sibling_coherence_pos_neg: float
    sibling_coherence_pos_wit: float
    offset_stability_score: float


class NodalStack:
    """Full 5-level ternary-signed nodal architecture.

    Level 1: Binary mission split (synthesis / verification)
    Level 2: Ternary semantic fork (positive / witness / negative)
    Level 3: Sacred tongue bundle (6-tongue trit output per fork)
    Level 4: Signed shadow branch ({-1,+1} adversarial mirror)
    Level 5: Reconstruction fusion (permit / hold / deny)
    """

    def __init__(self, config: Optional[NodalStackConfig] = None) -> None:
        self.config = config or DEFAULT_NODAL_CONFIG

    def evaluate(
        self,
        channel: MissionChannel,
        positive_tongues: SacredTongueTritBundle,
        witness_tongues: SacredTongueTritBundle,
        negative_tongues: SacredTongueTritBundle,
    ) -> NodalStackResult:
        tv_pos = positive_tongues.to_trit_vector()
        tv_wit = witness_tongues.to_trit_vector()
        tv_neg = negative_tongues.to_trit_vector()

        coh_pos_neg = sibling_coherence(tv_pos, tv_neg)
        coh_pos_wit = sibling_coherence(tv_pos, tv_wit)

        pos_score = max(0.0, positive_tongues.weighted_score())
        neg_score = max(0.0, -negative_tongues.weighted_score())
        shadow = AdversarialShadow(
            positive_score=pos_score,
            negative_score=neg_score,
            lambda_discount=self.config.shadow_lambda,
        )

        fused = trit_reconstruction(
            [tv_pos, tv_wit, tv_neg],
            weights=[1.0 / PHI, 1.0 / (PHI**2), 1.0 / (PHI**3)],
            theta=self.config.reconstruction_theta,
        )

        fused_bundle = SacredTongueTritBundle.from_trit_vector(fused)
        ofs = offset_stability(tv_pos, fused)
        decision = fused_bundle.governance_decision()

        if shadow.is_contested(self.config.shadow_contest_threshold):
            if decision == GovernanceDecision.ALLOW:
                decision = GovernanceDecision.QUARANTINE
            elif decision == GovernanceDecision.QUARANTINE:
                decision = GovernanceDecision.ESCALATE

        return NodalStackResult(
            channel=channel,
            positive_bundle=positive_tongues,
            witness_bundle=witness_tongues,
            negative_bundle=negative_tongues,
            shadow=shadow,
            fused_bundle=fused_bundle,
            decision=decision,
            sibling_coherence_pos_neg=coh_pos_neg,
            sibling_coherence_pos_wit=coh_pos_wit,
            offset_stability_score=ofs,
        )
