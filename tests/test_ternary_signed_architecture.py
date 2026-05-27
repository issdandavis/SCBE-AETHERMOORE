"""
Tests for Ternary Signed Architecture and Node Fusion
=====================================================

Covers:
  - TritVector construction, validation, negation
  - SignedBinaryVector construction, polarity
  - Trit agreement & sibling coherence (Section 5)
  - Trit reconstruction fusion (Section 10)
  - Offset stability (Section 11)
  - Sacred Tongue Trit Bundle (Section 9)
  - Adversarial shadow branch (Section 12)
  - Negabase alternating accumulator (Section 7)
  - Ternary parental tree (Section 13-14)
  - TriFuse operator (Section 18)
  - Node state fusion
  - NodalStack 5-level pipeline (Section 17)
  - Fleet-level consensus and coherence matrix
  - Layer correction
  - Encoding bridges (TritVector <-> BalancedTernary <-> NegaBinary)
  - FleetTernaryFusion end-to-end

@module tests/test_ternary_signed_architecture
@layer L2-unit, L3-integration
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.ternary_signed_architecture import (
    TritVector,
    SignedBinaryVector,
    SacredTongueTritBundle,
    AdversarialShadow,
    GovernanceDecision,
    TernaryNode,
    BranchType,
    NodeState,
    NodalStack,
    NodalStackConfig,
    NodalStackResult,
    MissionChannel,
    trit_agreement,
    sibling_coherence,
    trit_reconstruction,
    offset_stability,
    negabase_alternating_sum,
    tri_fuse,
    fuse_node_states,
    build_ternary_tree,
    ternary_tree_node_count,
    TONGUE_WEIGHTS,
)

from symphonic_cipher.scbe_aethermoore.ternary_node_fusion import (
    AgentTritState,
    FleetFusionConfig,
    FleetTernaryFusion,
    compute_coherence_matrix,
    ternary_consensus,
    apply_layer_correction,
    trit_vector_to_balanced_ternary,
    balanced_ternary_to_trit_vector,
    trit_vector_to_negabinary,
    negabinary_to_trit_vector,
)

# ═══════════════════════════════════════════════════
#  TritVector
# ═══════════════════════════════════════════════════


class TestTritVector:
    def test_construction(self):
        tv = TritVector.from_list([1, 0, -1])
        assert tv.dim == 3
        assert tv.values == (1, 0, -1)

    def test_zeros(self):
        tv = TritVector.zeros(5)
        assert tv.values == (0, 0, 0, 0, 0)

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            TritVector((2, 0, -1))

    def test_negation(self):
        tv = TritVector.from_list([1, 0, -1])
        neg = -tv
        assert neg.values == (-1, 0, 1)

    def test_double_negation_identity(self):
        tv = TritVector.from_list([1, -1, 0, 1, -1, 0])
        assert (-(-tv)).values == tv.values

    def test_repr(self):
        tv = TritVector.from_list([1, 0, -1])
        assert "10T" in repr(tv)


# ═══════════════════════════════════════════════════
#  SignedBinaryVector
# ═══════════════════════════════════════════════════


class TestSignedBinaryVector:
    def test_construction(self):
        sb = SignedBinaryVector.from_list([1, -1, 1])
        assert sb.dim == 3
        assert sb.values == (1, -1, 1)

    def test_ones(self):
        sb = SignedBinaryVector.ones(4)
        assert sb.values == (1, 1, 1, 1)

    def test_invalid_zero_raises(self):
        with pytest.raises(ValueError):
            SignedBinaryVector((1, 0, -1))

    def test_polarity_score(self):
        sb = SignedBinaryVector.from_list([1, 1, -1])
        assert abs(sb.polarity_score() - 1 / 3) < 1e-10

    def test_negation(self):
        sb = SignedBinaryVector.from_list([1, -1])
        neg = -sb
        assert neg.values == (-1, 1)

    def test_fully_aligned(self):
        sb = SignedBinaryVector.ones(6)
        assert sb.polarity_score() == 1.0

    def test_fully_opposed(self):
        sb = -SignedBinaryVector.ones(6)
        assert sb.polarity_score() == -1.0


# ═══════════════════════════════════════════════════
#  Trit Agreement & Sibling Coherence
# ═══════════════════════════════════════════════════


class TestTritAgreement:
    def test_identical(self):
        assert trit_agreement(1, 1) == 1
        assert trit_agreement(-1, -1) == 1
        assert trit_agreement(0, 0) == 1

    def test_one_zero(self):
        assert trit_agreement(1, 0) == 0
        assert trit_agreement(0, -1) == 0

    def test_opposition(self):
        assert trit_agreement(1, -1) == -1
        assert trit_agreement(-1, 1) == -1


class TestSiblingCoherence:
    def test_identical_vectors(self):
        a = TritVector.from_list([1, -1, 0, 1])
        assert sibling_coherence(a, a) == 1.0

    def test_opposite_vectors(self):
        a = TritVector.from_list([1, -1, 1, -1])
        b = TritVector.from_list([-1, 1, -1, 1])
        assert sibling_coherence(a, b) == -1.0

    def test_orthogonal_vectors(self):
        a = TritVector.from_list([1, -1, 0])
        b = TritVector.from_list([0, 0, 1])
        c = sibling_coherence(a, b)
        assert -1.0 <= c <= 1.0

    def test_dimension_mismatch_raises(self):
        a = TritVector.from_list([1, 0])
        b = TritVector.from_list([1, 0, -1])
        with pytest.raises(ValueError):
            sibling_coherence(a, b)

    def test_all_zeros(self):
        a = TritVector.zeros(4)
        b = TritVector.zeros(4)
        assert sibling_coherence(a, b) == 1.0


# ═══════════════════════════════════════════════════
#  Trit Reconstruction
# ═══════════════════════════════════════════════════


class TestTritReconstruction:
    def test_unanimous_positive(self):
        vecs = [TritVector.from_list([1, 1, 1])] * 5
        result = trit_reconstruction(vecs, theta=0.5)
        assert result.values == (1, 1, 1)

    def test_unanimous_negative(self):
        vecs = [TritVector.from_list([-1, -1, -1])] * 5
        result = trit_reconstruction(vecs, theta=0.5)
        assert result.values == (-1, -1, -1)

    def test_mixed_produces_zero(self):
        vecs = [
            TritVector.from_list([1, -1, 0]),
            TritVector.from_list([-1, 1, 0]),
        ]
        result = trit_reconstruction(vecs, theta=0.5)
        assert result.values == (0, 0, 0)

    def test_weighted_reconstruction(self):
        vecs = [
            TritVector.from_list([1, -1]),
            TritVector.from_list([-1, 1]),
        ]
        result = trit_reconstruction(vecs, weights=[0.9, 0.1], theta=0.3)
        assert result.values == (1, -1)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            trit_reconstruction([])

    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError):
            trit_reconstruction([TritVector.from_list([1]), TritVector.from_list([1, 0])])


# ═══════════════════════════════════════════════════
#  Offset Stability
# ═══════════════════════════════════════════════════


class TestOffsetStability:
    def test_identical_bundles(self):
        z = TritVector.from_list([1, -1, 0, 1, 0, -1])
        assert offset_stability(z, z) == 1.0

    def test_maximally_different(self):
        z = TritVector.from_list([1, 1, 1])
        z_delta = TritVector.from_list([-1, -1, -1])
        assert offset_stability(z, z_delta) == 0.0

    def test_partial_difference(self):
        z = TritVector.from_list([1, 0, -1])
        z_delta = TritVector.from_list([1, 0, 0])
        s = offset_stability(z, z_delta)
        assert 0.0 < s < 1.0

    def test_range_bounded(self):
        z = TritVector.from_list([1, -1, 0, 1])
        z_delta = TritVector.from_list([0, 1, -1, -1])
        s = offset_stability(z, z_delta)
        assert 0.0 <= s <= 1.0


# ═══════════════════════════════════════════════════
#  Sacred Tongue Trit Bundle
# ═══════════════════════════════════════════════════


class TestSacredTongueTritBundle:
    def test_construction(self):
        b = SacredTongueTritBundle(ko=1, av=0, ru=1, ca=-1, um=0, dr=-1)
        assert b.ko == 1
        assert b.dr == -1

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            SacredTongueTritBundle(ko=2)

    def test_to_trit_vector(self):
        b = SacredTongueTritBundle(ko=1, av=0, ru=-1, ca=1, um=0, dr=-1)
        tv = b.to_trit_vector()
        assert tv.dim == 6
        assert tv.values == (1, 0, -1, 1, 0, -1)

    def test_round_trip(self):
        b = SacredTongueTritBundle(ko=1, av=-1, ru=0, ca=1, um=-1, dr=0)
        tv = b.to_trit_vector()
        b2 = SacredTongueTritBundle.from_trit_vector(tv)
        assert b2.ko == b.ko
        assert b2.dr == b.dr

    def test_weighted_score_positive(self):
        b = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=1, um=1, dr=1)
        ws = b.weighted_score()
        assert ws == pytest.approx(sum(TONGUE_WEIGHTS), rel=1e-6)

    def test_weighted_score_negative(self):
        b = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        ws = b.weighted_score()
        assert ws == pytest.approx(-sum(TONGUE_WEIGHTS), rel=1e-6)

    def test_semantic_report(self):
        b = SacredTongueTritBundle(ko=1, av=0, ru=-1, ca=1, um=0, dr=-1)
        report = b.semantic_report()
        assert report["KO"] == "intent_aligned"
        assert report["AV"] == "context_incomplete"
        assert report["RU"] == "witness_falsified"
        assert report["DR"] == "judgment_deny"

    def test_governance_deny_on_dr_minus(self):
        b = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=1, um=1, dr=-1)
        assert b.governance_decision() == GovernanceDecision.DENY

    def test_governance_allow_on_strong_positive(self):
        b = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=1, um=1, dr=1)
        assert b.governance_decision() == GovernanceDecision.ALLOW

    def test_ambiguity_count(self):
        b = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=1, um=-1, dr=0)
        assert b.ambiguity_count() == 4


# ═══════════════════════════════════════════════════
#  Adversarial Shadow
# ═══════════════════════════════════════════════════


class TestAdversarialShadow:
    def test_net_confidence_positive(self):
        s = AdversarialShadow(positive_score=1.0, negative_score=0.0, lambda_discount=0.5)
        assert s.net_confidence == 1.0

    def test_net_confidence_discounted(self):
        s = AdversarialShadow(positive_score=1.0, negative_score=1.0, lambda_discount=0.5)
        assert s.net_confidence == 0.5

    def test_polarity_positive(self):
        s = AdversarialShadow(positive_score=1.0, negative_score=0.5, lambda_discount=0.5)
        assert s.polarity == 1

    def test_polarity_negative(self):
        s = AdversarialShadow(positive_score=0.2, negative_score=1.0, lambda_discount=0.5)
        assert s.polarity == -1

    def test_contested(self):
        s = AdversarialShadow(positive_score=1.0, negative_score=1.0, lambda_discount=0.5)
        assert s.is_contested(threshold=0.3)

    def test_not_contested(self):
        s = AdversarialShadow(positive_score=1.0, negative_score=0.1, lambda_discount=0.5)
        assert not s.is_contested(threshold=0.3)


# ═══════════════════════════════════════════════════
#  Negabase Alternating Accumulator
# ═══════════════════════════════════════════════════


class TestNegabaseAlternatingSum:
    def test_single_layer(self):
        assert negabase_alternating_sum([5.0]) == 5.0

    def test_two_layers_cancel(self):
        result = negabase_alternating_sum([1.0, 1.0])
        assert result == 0.0

    def test_alternation(self):
        result = negabase_alternating_sum([1.0, 2.0, 3.0])
        assert result == 1.0 - 2.0 + 3.0

    def test_with_weights(self):
        result = negabase_alternating_sum([1.0, 1.0, 1.0], [2.0, 3.0, 4.0])
        assert result == 2.0 - 3.0 + 4.0


# ═══════════════════════════════════════════════════
#  Ternary Parental Tree
# ═══════════════════════════════════════════════════


class TestTernaryTree:
    def test_leaf_node(self):
        node = TernaryNode(name="leaf", depth=0)
        assert node.is_leaf
        assert node.node_count() == 1

    def test_build_depth_0(self):
        tree = build_ternary_tree("root", max_depth=0)
        assert tree.is_leaf
        assert tree.node_count() == 1

    def test_build_depth_1(self):
        tree = build_ternary_tree("root", max_depth=1)
        assert not tree.is_leaf
        assert len(tree.children) == 3
        assert tree.node_count() == 4

    def test_build_depth_2(self):
        tree = build_ternary_tree("root", max_depth=2)
        assert tree.node_count() == ternary_tree_node_count(2)

    def test_node_count_formula(self):
        for d in range(5):
            expected = (3 ** (d + 1) - 1) // 2
            assert ternary_tree_node_count(d) == expected

    def test_max_depth(self):
        tree = build_ternary_tree("root", max_depth=3)
        assert tree.max_depth() == 3

    def test_child_by_branch(self):
        tree = build_ternary_tree("root", max_depth=1)
        pos = tree.child_by_branch(BranchType.POSITIVE)
        wit = tree.child_by_branch(BranchType.WITNESS)
        neg = tree.child_by_branch(BranchType.NEGATIVE)
        assert pos is not None
        assert wit is not None
        assert neg is not None


# ═══════════════════════════════════════════════════
#  TriFuse
# ═══════════════════════════════════════════════════


class TestTriFuse:
    def test_positive(self):
        assert tri_fuse(0.8, theta=0.5) == 1

    def test_negative(self):
        assert tri_fuse(-0.8, theta=0.5) == -1

    def test_neutral(self):
        assert tri_fuse(0.3, theta=0.5) == 0

    def test_boundary_positive(self):
        assert tri_fuse(0.5, theta=0.5) == 0

    def test_boundary_negative(self):
        assert tri_fuse(-0.5, theta=0.5) == 0


# ═══════════════════════════════════════════════════
#  Node State Fusion
# ═══════════════════════════════════════════════════


class TestFuseNodeStates:
    def test_unanimous_children(self):
        tv = TritVector.from_list([1, 1, 1])
        states = [NodeState(ternary=tv)] * 3
        result = fuse_node_states(states, [1.0, 1.0, 1.0], theta=0.5)
        assert result.values == (1, 1, 1)

    def test_with_shadow(self):
        tv = TritVector.from_list([1, 0, -1])
        child = NodeState(ternary=tv)
        shadow_pol = SignedBinaryVector.from_list([-1, -1, -1])
        shadow = NodeState(polarity=shadow_pol)
        result = fuse_node_states([child], [1.0], [shadow], [0.5], theta=0.3)
        assert result.dim == 3

    def test_no_ternary_raises(self):
        with pytest.raises(ValueError):
            fuse_node_states([NodeState()], [1.0])


# ═══════════════════════════════════════════════════
#  Nodal Stack (5-level pipeline)
# ═══════════════════════════════════════════════════


class TestNodalStack:
    def test_full_allow(self):
        stack = NodalStack()
        pos = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=1, um=1, dr=1)
        wit = SacredTongueTritBundle(ko=1, av=1, ru=0, ca=0, um=1, dr=1)
        neg = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        result = stack.evaluate(MissionChannel.SYNTHESIS, pos, wit, neg)
        assert isinstance(result, NodalStackResult)
        assert result.decision in (GovernanceDecision.ALLOW, GovernanceDecision.QUARANTINE)

    def test_opposed_branches_escalate(self):
        """Exact opposites + contested shadow -> ESCALATE (correct behavior)."""
        stack = NodalStack()
        pos = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=1, um=1, dr=1)
        wit = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        neg = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        result = stack.evaluate(MissionChannel.SYNTHESIS, pos, wit, neg)
        assert result.decision == GovernanceDecision.ESCALATE

    def test_full_deny(self):
        stack = NodalStack()
        pos = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        wit = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        neg = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        result = stack.evaluate(MissionChannel.VERIFICATION, pos, wit, neg)
        assert result.decision == GovernanceDecision.DENY

    def test_shadow_contest_escalates(self):
        config = NodalStackConfig(shadow_lambda=1.0, shadow_contest_threshold=0.1)
        stack = NodalStack(config)
        pos = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=0, um=0, dr=0)
        wit = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        neg = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        result = stack.evaluate(MissionChannel.SYNTHESIS, pos, wit, neg)
        assert result.decision in (GovernanceDecision.QUARANTINE, GovernanceDecision.ESCALATE)

    def test_sibling_coherence_computed(self):
        stack = NodalStack()
        pos = SacredTongueTritBundle(ko=1, av=1, ru=1, ca=1, um=1, dr=1)
        wit = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        neg = SacredTongueTritBundle(ko=-1, av=-1, ru=-1, ca=-1, um=-1, dr=-1)
        result = stack.evaluate(MissionChannel.SYNTHESIS, pos, wit, neg)
        assert result.sibling_coherence_pos_neg == -1.0
        assert -1.0 <= result.sibling_coherence_pos_wit <= 1.0

    def test_offset_stability_computed(self):
        stack = NodalStack()
        pos = SacredTongueTritBundle(ko=1, av=0, ru=-1, ca=1, um=0, dr=1)
        wit = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        neg = SacredTongueTritBundle(ko=0, av=0, ru=0, ca=0, um=0, dr=0)
        result = stack.evaluate(MissionChannel.SYNTHESIS, pos, wit, neg)
        assert 0.0 <= result.offset_stability_score <= 1.0


# ═══════════════════════════════════════════════════
#  Coherence Matrix
# ═══════════════════════════════════════════════════


class TestCoherenceMatrix:
    def _make_agents(self) -> list:
        return [
            AgentTritState("a1", TritVector.from_list([1, 1, 0, -1])),
            AgentTritState("a2", TritVector.from_list([1, 1, 0, -1])),
            AgentTritState("a3", TritVector.from_list([-1, -1, 0, 1])),
        ]

    def test_self_coherence(self):
        agents = self._make_agents()
        cm = compute_coherence_matrix(agents)
        for i in range(cm.size):
            assert cm.matrix[i][i] == 1.0

    def test_identical_agents_perfect_coherence(self):
        agents = self._make_agents()[:2]
        cm = compute_coherence_matrix(agents)
        assert cm.matrix[0][1] == 1.0

    def test_opposed_agents_negative_coherence(self):
        agents = [self._make_agents()[0], self._make_agents()[2]]
        cm = compute_coherence_matrix(agents)
        assert cm.matrix[0][1] < 0

    def test_mean_coherence(self):
        agents = self._make_agents()
        cm = compute_coherence_matrix(agents)
        mc = cm.mean_coherence()
        assert -1.0 <= mc <= 1.0

    def test_faction_detection(self):
        agents = self._make_agents()
        cm = compute_coherence_matrix(agents)
        factions = cm.faction_detection(threshold=0.5)
        assert len(factions) >= 1

    def test_has_consensus_false_for_opposed(self):
        agents = self._make_agents()
        cm = compute_coherence_matrix(agents)
        assert not cm.has_consensus(threshold=0.5)


# ═══════════════════════════════════════════════════
#  Ternary Consensus
# ═══════════════════════════════════════════════════


class TestTernaryConsensus:
    def test_unanimous(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, 1, -1, 0, 1, -1])),
            AgentTritState("a2", TritVector.from_list([1, 1, -1, 0, 1, -1])),
            AgentTritState("a3", TritVector.from_list([1, 1, -1, 0, 1, -1])),
        ]
        result = ternary_consensus(agents)
        assert result.fused_vector.values == (1, 1, -1, 0, 1, -1)

    def test_split_produces_zeros(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, -1])),
            AgentTritState("a2", TritVector.from_list([-1, 1])),
        ]
        result = ternary_consensus(agents)
        assert result.fused_vector.values == (0, 0)

    def test_contested_dimensions_detected(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, -1])),
            AgentTritState("a2", TritVector.from_list([-1, 1])),
        ]
        result = ternary_consensus(agents)
        assert len(result.contested_dimensions) == 2

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            ternary_consensus([])

    def test_weighted_consensus(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, 1, 1, 1, 1, 1]), confidence=10.0),
            AgentTritState("a2", TritVector.from_list([-1, -1, -1, -1, -1, -1]), confidence=1.0),
        ]
        result = ternary_consensus(agents, theta=0.3)
        assert result.fused_vector.values[0] == 1


# ═══════════════════════════════════════════════════
#  Layer Correction
# ═══════════════════════════════════════════════════


class TestLayerCorrection:
    def test_alternating_cancellation(self):
        result = apply_layer_correction([1.0, 1.0, 1.0, 1.0])
        assert result.corrected_sum == pytest.approx(0.0)

    def test_single_layer(self):
        result = apply_layer_correction([5.0])
        assert result.corrected_sum == 5.0

    def test_stability_index_bounded(self):
        result = apply_layer_correction([1.0, 2.0, 3.0, 4.0, 5.0])
        assert 0.0 <= result.stability_index <= 1.0

    def test_polarity(self):
        result = apply_layer_correction([10.0, 1.0])
        assert result.dominant_polarity == "positive"


# ═══════════════════════════════════════════════════
#  Encoding Bridges
# ═══════════════════════════════════════════════════


class TestEncodingBridges:
    def test_trit_vector_balanced_ternary_roundtrip(self):
        tv = TritVector.from_list([1, 0, -1, 1])
        bt = trit_vector_to_balanced_ternary(tv)
        tv2 = balanced_ternary_to_trit_vector(bt, width=4)
        assert tv2.values == tv.values

    def test_trit_vector_negabinary_roundtrip(self):
        tv = TritVector.from_list([1, -1, 0])
        nb = trit_vector_to_negabinary(tv)
        tv2 = negabinary_to_trit_vector(nb, width=3)
        assert tv2.values == tv.values

    def test_zeros_roundtrip(self):
        tv = TritVector.zeros(4)
        bt = trit_vector_to_balanced_ternary(tv)
        tv2 = balanced_ternary_to_trit_vector(bt, width=4)
        assert tv2.values == (0, 0, 0, 0)


# ═══════════════════════════════════════════════════
#  Fleet Ternary Fusion (end-to-end)
# ═══════════════════════════════════════════════════


class TestFleetTernaryFusion:
    def test_aligned_fleet_allows(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, 1, 1, 1, 1, 1]), confidence=1.0),
            AgentTritState("a2", TritVector.from_list([1, 1, 1, 1, 1, 1]), confidence=1.0),
            AgentTritState("a3", TritVector.from_list([1, 1, 0, 1, 1, 1]), confidence=1.0),
        ]
        engine = FleetTernaryFusion()
        result = engine.fuse(agents)
        assert result.final_decision == GovernanceDecision.ALLOW
        assert len(result.adversarial_agents) == 0

    def test_opposed_fleet_quarantines(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, 1, 1, 1, 1, 1]), confidence=1.0),
            AgentTritState("a2", TritVector.from_list([-1, -1, -1, -1, -1, -1]), confidence=1.0),
        ]
        engine = FleetTernaryFusion()
        result = engine.fuse(agents)
        assert result.final_decision in (
            GovernanceDecision.QUARANTINE,
            GovernanceDecision.ESCALATE,
        )

    def test_adversarial_agents_detected(self):
        agents = [
            AgentTritState(
                "good",
                TritVector.from_list([1, 1, 1, 1, 1, 1]),
                polarity=SignedBinaryVector.from_list([1, 1, 1, 1, 1, 1]),
            ),
            AgentTritState(
                "evil",
                TritVector.from_list([-1, -1, -1, -1, -1, -1]),
                polarity=SignedBinaryVector.from_list([-1, -1, -1, -1, -1, -1]),
            ),
        ]
        engine = FleetTernaryFusion()
        result = engine.fuse(agents)
        assert "evil" in result.adversarial_agents

    def test_with_layer_correction(self):
        agents = [AgentTritState("a1", TritVector.from_list([1, 1, 1, 1, 1, 1]))]
        engine = FleetTernaryFusion()
        result = engine.fuse(agents, layer_outputs=[1.0, 2.0, 3.0])
        assert result.layer_correction is not None

    def test_empty_raises(self):
        engine = FleetTernaryFusion()
        with pytest.raises(ValueError):
            engine.fuse([])

    def test_warnings_on_low_coherence(self):
        agents = [
            AgentTritState("a1", TritVector.from_list([1, 1, 1, 1, 1, 1]), confidence=1.0),
            AgentTritState("a2", TritVector.from_list([-1, -1, -1, -1, -1, -1]), confidence=1.0),
        ]
        config = FleetFusionConfig(coherence_warning_threshold=0.9)
        engine = FleetTernaryFusion(config)
        result = engine.fuse(agents)
        assert any("coherence" in w.lower() for w in result.warnings)
