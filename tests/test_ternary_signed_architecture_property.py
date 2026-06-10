"""
Property-Based Tests for Ternary Signed Architecture
====================================================

Random-input proofs (L4-property tier) for the ternary/signed-binary
state algebra.  Uses Hypothesis to verify algebraic invariants that the
example-based suite cannot exhaustively cover.

Invariants checked:
  - Negation is an involution: -(-z) == z
  - sibling_coherence is symmetric, self-coherent, and bounded in [-1, 1]
  - sibling_coherence(z, -z) == -1 for fully non-zero vectors
  - offset_stability is symmetric and bounded in [0, 1], 1 iff identical
  - trit_reconstruction always yields valid trits {-1, 0, +1}
  - tri_fuse output is always a valid trit
  - Encoding round-trip: TritVector -> BalancedTernary -> TritVector
  - Encoding round-trip: TritVector -> NegaBinary -> TritVector
  - ternary_consensus output dimension matches input, decision is valid

@module tests/test_ternary_signed_architecture_property
@layer L4-property
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, strategies as st

from symphonic_cipher.scbe_aethermoore.ternary_signed_architecture import (
    TritVector,
    GovernanceDecision,
    sibling_coherence,
    offset_stability,
    trit_reconstruction,
    tri_fuse,
)
from symphonic_cipher.scbe_aethermoore.ternary_node_fusion import (
    AgentTritState,
    ternary_consensus,
    trit_vector_to_balanced_ternary,
    balanced_ternary_to_trit_vector,
    trit_vector_to_negabinary,
    negabinary_to_trit_vector,
)

# Strategies ----------------------------------------------------------------

trits = st.sampled_from([-1, 0, 1])
nonzero_trits = st.sampled_from([-1, 1])


def trit_vectors(min_size=1, max_size=8):
    return st.lists(trits, min_size=min_size, max_size=max_size).map(TritVector.from_list)


def nonzero_trit_vectors(min_size=1, max_size=8):
    return st.lists(nonzero_trits, min_size=min_size, max_size=max_size).map(TritVector.from_list)


# Negation ------------------------------------------------------------------


class TestNegationInvolution:
    @given(trit_vectors())
    def test_double_negation_identity(self, z):
        assert (-(-z)).values == z.values

    @given(trit_vectors())
    def test_negation_valid_trits(self, z):
        assert all(v in (-1, 0, 1) for v in z.negate().values)


# Sibling coherence ---------------------------------------------------------


class TestSiblingCoherenceProperties:
    @given(trit_vectors(), trit_vectors())
    def test_symmetric_and_bounded(self, a, b):
        if a.dim != b.dim:
            return
        c_ab = sibling_coherence(a, b)
        c_ba = sibling_coherence(b, a)
        assert abs(c_ab - c_ba) < 1e-12
        assert -1.0 <= c_ab <= 1.0

    @given(trit_vectors())
    def test_self_coherence_is_one(self, z):
        assert sibling_coherence(z, z) == 1.0

    @given(nonzero_trit_vectors())
    def test_opposite_coherence_is_minus_one(self, z):
        assert sibling_coherence(z, z.negate()) == -1.0


# Offset stability ----------------------------------------------------------


class TestOffsetStabilityProperties:
    @given(trit_vectors(), trit_vectors())
    def test_symmetric_and_bounded(self, a, b):
        if a.dim != b.dim:
            return
        s_ab = offset_stability(a, b)
        s_ba = offset_stability(b, a)
        assert abs(s_ab - s_ba) < 1e-12
        assert 0.0 <= s_ab <= 1.0

    @given(trit_vectors())
    def test_identity_is_one(self, z):
        assert offset_stability(z, z) == 1.0

    @given(trit_vectors(), trit_vectors())
    def test_one_iff_identical(self, a, b):
        if a.dim != b.dim:
            return
        if offset_stability(a, b) == 1.0:
            assert a.values == b.values


# Reconstruction & fusion ---------------------------------------------------


class TestReconstructionProperties:
    @given(st.lists(trit_vectors(min_size=3, max_size=3), min_size=1, max_size=6))
    def test_output_is_valid_trits(self, vecs):
        result = trit_reconstruction(vecs)
        assert all(v in (-1, 0, 1) for v in result.values)
        assert result.dim == 3

    @given(st.floats(min_value=-5.0, max_value=5.0), st.floats(min_value=0.0, max_value=2.0))
    def test_tri_fuse_valid_trit(self, x, theta):
        assert tri_fuse(x, theta) in (-1, 0, 1)


# Encoding round-trips ------------------------------------------------------


class TestEncodingRoundTrips:
    @given(trit_vectors(min_size=1, max_size=6))
    def test_balanced_ternary_roundtrip(self, z):
        bt = trit_vector_to_balanced_ternary(z)
        back = balanced_ternary_to_trit_vector(bt, width=z.dim)
        assert back.values == z.values

    @given(trit_vectors(min_size=1, max_size=6))
    def test_negabinary_roundtrip(self, z):
        nb = trit_vector_to_negabinary(z)
        back = negabinary_to_trit_vector(nb, width=z.dim)
        assert back.values == z.values


# Consensus -----------------------------------------------------------------


class TestConsensusProperties:
    @given(st.lists(trit_vectors(min_size=6, max_size=6), min_size=1, max_size=8))
    def test_dimension_preserved_and_decision_valid(self, vecs):
        agents = [AgentTritState(f"a{i}", v) for i, v in enumerate(vecs)]
        result = ternary_consensus(agents)
        assert result.fused_vector.dim == 6
        assert isinstance(result.decision, GovernanceDecision)
        assert all(v in (-1, 0, 1) for v in result.fused_vector.values)
