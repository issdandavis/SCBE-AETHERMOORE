"""
Tests for Gate Swap Tri-Manifold Governance
============================================

Locks in the expected behavior for the 5 canonical FederatedNode types
from the simulation run after the map_gates_to_trimanifold MSD fix.

Pipeline under test:
  6-element gate vector -> 3 aggregated pairs -> negabinary ->
  balanced ternary -> MSD extraction -> governance decision

Decision logic:
  DENY:       t3 == -1 OR sum(t1, t2, t3) < 0
  QUARANTINE: sum(t1, t2, t3) == 0 AND t3 != -1
  ALLOW:      sum(t1, t2, t3) > 0 AND t3 != -1

@module tests/test_gate_swap_trimanifold
@layer Layer 9, Layer 12, Layer 13
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.gate_swap import (
    GateTriState,
    FederatedNode,
    map_gates_to_trimanifold,
    apply_tri_manifold_governance,
    evaluate_node,
    _extract_msd,
)
from symphonic_cipher.scbe_aethermoore.negabinary import (
    NegaBinary,
    negabinary_to_balanced_ternary,
)
from symphonic_cipher.scbe_aethermoore.trinary import BalancedTernary


# ═══════════════════════════════════════════════════
#  MSD Extraction (the fixed function)
# ═══════════════════════════════════════════════════

class TestMSDExtraction:
    """Verify the negabinary -> balanced ternary -> MSD pipeline."""

    def test_zero_msd(self):
        """0 -> balanced ternary '0' -> MSD = 0."""
        assert _extract_msd(0) == 0

    def test_one_msd(self):
        """1 -> balanced ternary '1' -> MSD = 1."""
        assert _extract_msd(1) == 1

    def test_negative_one_msd(self):
        """-1 -> balanced ternary 'T' -> MSD = -1."""
        assert _extract_msd(-1) == -1

    def test_two_msd(self):
        """2 -> negabinary '110' -> balanced ternary '1T' -> MSD = 1.

        This was the critical fix: 2's balanced ternary is '1T' (1*3 + (-1)*1).
        The MSD is 1, not -1.
        """
        assert _extract_msd(2) == 1

    def test_three_msd(self):
        """3 -> balanced ternary '10' -> MSD = 1."""
        assert _extract_msd(3) == 1

    def test_eight_msd(self):
        """8 -> balanced ternary '10T' (9 - 1) -> MSD = 1."""
        assert _extract_msd(8) == 1

    def test_ten_msd(self):
        """10 -> balanced ternary '101' -> MSD = 1."""
        assert _extract_msd(10) == 1

    def test_twenty_one_msd(self):
        """21 -> balanced ternary representation -> MSD = 1."""
        assert _extract_msd(21) == 1

    def test_negative_values_have_negative_msd(self):
        """Negative integers should have MSD = -1 in balanced ternary."""
        for n in [-1, -2, -3, -5, -10, -100]:
            assert _extract_msd(n) == -1, f"MSD of {n} should be -1"

    def test_positive_values_have_positive_msd(self):
        """Positive integers should have MSD = 1 in balanced ternary."""
        for n in [1, 2, 3, 5, 8, 10, 21, 42, 51, 100, 355, 1101]:
            assert _extract_msd(n) == 1, f"MSD of {n} should be 1"

    def test_msd_matches_balanced_ternary_sign(self):
        """MSD sign matches the number's sign for all non-zero values."""
        for n in range(-100, 101):
            msd = _extract_msd(n)
            if n > 0:
                assert msd == 1, f"Positive {n} should have MSD=1, got {msd}"
            elif n < 0:
                assert msd == -1, f"Negative {n} should have MSD=-1, got {msd}"
            else:
                assert msd == 0


# ═══════════════════════════════════════════════════
#  Canonical Node Tests (simulation lock-in)
# ═══════════════════════════════════════════════════

class TestNodeFibonacci:
    """Node_Fibonacci: [1, 2, 3, 5, 8, 13] -> ALLOWED.

    Aggregated: (3, 8, 21) -> all MSD = 1 -> sum = 3 > 0 -> ALLOW.
    """

    def test_gate_mapping(self):
        state = map_gates_to_trimanifold([1, 2, 3, 5, 8, 13])
        assert state.t1 == 1
        assert state.t2 == 1
        assert state.t3 == 1

    def test_governance_decision(self):
        state = map_gates_to_trimanifold([1, 2, 3, 5, 8, 13])
        assert apply_tri_manifold_governance(state) == "ALLOW"

    def test_trit_sum(self):
        state = map_gates_to_trimanifold([1, 2, 3, 5, 8, 13])
        assert state.trit_sum == 3

    def test_end_to_end(self):
        node = FederatedNode("Node_Fibonacci", [1, 2, 3, 5, 8, 13])
        state, decision = evaluate_node(node)
        assert decision == "ALLOW"
        assert state.to_tuple() == (1, 1, 1)


class TestNodeZeros:
    """Node_Zeros: [0, 0, 0, 0, 0, 0] -> QUARANTINED.

    Aggregated: (0, 0, 0) -> all MSD = 0 -> sum = 0 -> QUARANTINE.
    """

    def test_gate_mapping(self):
        state = map_gates_to_trimanifold([0, 0, 0, 0, 0, 0])
        assert state.t1 == 0
        assert state.t2 == 0
        assert state.t3 == 0

    def test_governance_decision(self):
        state = map_gates_to_trimanifold([0, 0, 0, 0, 0, 0])
        assert apply_tri_manifold_governance(state) == "QUARANTINE"

    def test_trit_sum(self):
        state = map_gates_to_trimanifold([0, 0, 0, 0, 0, 0])
        assert state.trit_sum == 0


class TestNodeSecurityRisk:
    """Node_Security_Risk: [0, 0, 0, 0, 2, 0] -> ALLOWED (post-fix).

    Aggregated: (0, 0, 2).
    dim3 = 2 -> negabinary '110' -> balanced ternary '1T' -> MSD = 1.
    State: (0, 0, 1) -> sum = 1 > 0, t3 != -1 -> ALLOW.

    Previously DENIED due to incorrect t3 extraction (pre-fix bug).
    """

    def test_gate_mapping(self):
        state = map_gates_to_trimanifold([0, 0, 0, 0, 2, 0])
        assert state.t1 == 0
        assert state.t2 == 0
        assert state.t3 == 1  # The fix: was incorrectly -1 before

    def test_governance_decision(self):
        state = map_gates_to_trimanifold([0, 0, 0, 0, 2, 0])
        assert apply_tri_manifold_governance(state) == "ALLOW"

    def test_the_msd_fix(self):
        """The core of the MSD fix: integer 2 -> balanced ternary '1T' -> MSD = 1.

        The negabinary representation of 2 is '110'.
        Converting through to balanced ternary: 2 = 1*3 + (-1)*1 = '1T'.
        The Most Significant Trit is 1 (positive), not -1.
        """
        # Verify the negabinary representation
        nb = NegaBinary.from_int(2)
        assert str(nb) == "110"

        # Verify the balanced ternary representation
        bt = BalancedTernary.from_int(2)
        assert str(bt) == "1T"

        # Verify MSD extraction
        assert bt.trits_msb[0].value == 1


class TestNodeHighEntropy:
    """Node_High_Entropy: [100, 255, 1024, 77, 42, 9] -> ALLOWED.

    Aggregated: (355, 1101, 51) -> all large positive -> all MSD = 1.
    State: (1, 1, 1) -> sum = 3 > 0 -> ALLOW.
    """

    def test_gate_mapping(self):
        state = map_gates_to_trimanifold([100, 255, 1024, 77, 42, 9])
        assert state.t1 == 1
        assert state.t2 == 1
        assert state.t3 == 1

    def test_governance_decision(self):
        state = map_gates_to_trimanifold([100, 255, 1024, 77, 42, 9])
        assert apply_tri_manifold_governance(state) == "ALLOW"

    def test_aggregated_values(self):
        """Verify the dimensional aggregation."""
        gv = [100, 255, 1024, 77, 42, 9]
        assert gv[0] + gv[1] == 355
        assert gv[2] + gv[3] == 1101
        assert gv[4] + gv[5] == 51


class TestNodeAlternating:
    """Node_Alternating: [10, 0, 10, 0, 10, 0] -> ALLOWED.

    Aggregated: (10, 10, 10) -> all MSD = 1.
    10 -> negabinary '11110' -> balanced ternary '101' -> MSD = 1.
    State: (1, 1, 1) -> sum = 3 > 0 -> ALLOW.
    """

    def test_gate_mapping(self):
        state = map_gates_to_trimanifold([10, 0, 10, 0, 10, 0])
        assert state.t1 == 1
        assert state.t2 == 1
        assert state.t3 == 1

    def test_governance_decision(self):
        state = map_gates_to_trimanifold([10, 0, 10, 0, 10, 0])
        assert apply_tri_manifold_governance(state) == "ALLOW"

    def test_ten_encoding_chain(self):
        """Verify the full encoding chain for value 10."""
        # Negabinary of 10
        nb = NegaBinary.from_int(10)
        assert nb.to_int() == 10

        # Balanced ternary of 10: 1*9 + 0*3 + 1*1 = '101'
        bt = BalancedTernary.from_int(10)
        assert str(bt) == "101"
        assert bt.trits_msb[0].value == 1  # MSD = 1


# ═══════════════════════════════════════════════════
#  Governance Decision Logic
# ═══════════════════════════════════════════════════

class TestGovernanceDecisionLogic:
    """Test the decision function across all governance boundaries."""

    def test_all_positive_allows(self):
        assert apply_tri_manifold_governance(GateTriState(1, 1, 1)) == "ALLOW"

    def test_all_zero_quarantines(self):
        assert apply_tri_manifold_governance(GateTriState(0, 0, 0)) == "QUARANTINE"

    def test_all_negative_denies(self):
        assert apply_tri_manifold_governance(GateTriState(-1, -1, -1)) == "DENY"

    def test_t3_negative_always_denies(self):
        """t3 = -1 is a hard-deny regardless of other dimensions."""
        assert apply_tri_manifold_governance(GateTriState(1, 1, -1)) == "DENY"
        assert apply_tri_manifold_governance(GateTriState(0, 0, -1)) == "DENY"
        assert apply_tri_manifold_governance(GateTriState(1, 0, -1)) == "DENY"

    def test_positive_sum_with_safe_t3_allows(self):
        assert apply_tri_manifold_governance(GateTriState(1, 0, 0)) == "ALLOW"
        assert apply_tri_manifold_governance(GateTriState(0, 1, 0)) == "ALLOW"
        assert apply_tri_manifold_governance(GateTriState(0, 0, 1)) == "ALLOW"
        assert apply_tri_manifold_governance(GateTriState(1, 1, 0)) == "ALLOW"

    def test_negative_sum_denies(self):
        assert apply_tri_manifold_governance(GateTriState(-1, -1, 0)) == "DENY"
        assert apply_tri_manifold_governance(GateTriState(-1, 0, 0)) == "DENY"
        assert apply_tri_manifold_governance(GateTriState(0, -1, 0)) == "DENY"

    def test_zero_sum_quarantines(self):
        assert apply_tri_manifold_governance(GateTriState(1, -1, 0)) == "QUARANTINE"
        assert apply_tri_manifold_governance(GateTriState(-1, 1, 0)) == "QUARANTINE"
        assert apply_tri_manifold_governance(GateTriState(1, 0, -1)) == "DENY"  # t3=-1 overrides

    def test_all_27_states(self):
        """Exhaustively verify all 27 possible trit combinations."""
        for t1 in [-1, 0, 1]:
            for t2 in [-1, 0, 1]:
                for t3 in [-1, 0, 1]:
                    state = GateTriState(t1, t2, t3)
                    decision = apply_tri_manifold_governance(state)
                    s = t1 + t2 + t3

                    if t3 == -1:
                        assert decision == "DENY", \
                            f"({t1},{t2},{t3}): t3=-1 should DENY, got {decision}"
                    elif s < 0:
                        assert decision == "DENY", \
                            f"({t1},{t2},{t3}): sum={s}<0 should DENY, got {decision}"
                    elif s == 0:
                        assert decision == "QUARANTINE", \
                            f"({t1},{t2},{t3}): sum=0 should QUARANTINE, got {decision}"
                    else:
                        assert decision == "ALLOW", \
                            f"({t1},{t2},{t3}): sum={s}>0 should ALLOW, got {decision}"


# ═══════════════════════════════════════════════════
#  Edge Cases & Validation
# ═══════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases for the gate swap pipeline."""

    def test_invalid_vector_length(self):
        with pytest.raises(ValueError, match="6 elements"):
            map_gates_to_trimanifold([1, 2, 3])

    def test_single_nonzero_element(self):
        """Only one nonzero gate element should still produce valid state."""
        for i in range(6):
            gv = [0] * 6
            gv[i] = 1
            state = map_gates_to_trimanifold(gv)
            decision = apply_tri_manifold_governance(state)
            assert decision in ("ALLOW", "QUARANTINE", "DENY")

    def test_large_values_dont_crash(self):
        """Very large gate values should not cause errors."""
        state = map_gates_to_trimanifold([10000, 20000, 30000, 40000, 50000, 60000])
        assert state.t1 == 1  # Large positive -> MSD = 1
        assert state.t2 == 1
        assert state.t3 == 1
        assert apply_tri_manifold_governance(state) == "ALLOW"

    def test_gate_tri_state_tuple(self):
        state = GateTriState(1, 0, -1)
        assert state.to_tuple() == (1, 0, -1)
        assert state.trit_sum == 0

    def test_federated_node_defaults(self):
        node = FederatedNode("test")
        assert node.gate_vector == [0, 0, 0, 0, 0, 0]
        state, decision = evaluate_node(node)
        assert decision == "QUARANTINE"


# ═══════════════════════════════════════════════════
#  Negabinary Pipeline Integrity
# ═══════════════════════════════════════════════════

class TestNegabinaryPipelineIntegrity:
    """Verify the negabinary -> balanced ternary -> MSD pipeline
    preserves sign information correctly (the core of the MSD fix)."""

    def test_pipeline_preserves_value(self):
        """Round-trip through negabinary and balanced ternary preserves the integer."""
        for n in range(-50, 51):
            nb = NegaBinary.from_int(n)
            bt = negabinary_to_balanced_ternary(nb)
            assert bt.to_int() == n, f"Pipeline corrupted value {n}"

    def test_msd_sign_agreement(self):
        """For non-zero values, MSD sign always matches the original integer's sign.

        This is the mathematical property the MSD fix restored.
        """
        for n in range(-200, 201):
            if n == 0:
                continue
            msd = _extract_msd(n)
            expected_sign = 1 if n > 0 else -1
            assert msd == expected_sign, \
                f"MSD of {n} is {msd}, expected {expected_sign}"

    def test_fibonacci_aggregates(self):
        """The specific values from the Fibonacci node simulation."""
        assert _extract_msd(3) == 1   # 1 + 2
        assert _extract_msd(8) == 1   # 3 + 5
        assert _extract_msd(21) == 1  # 8 + 13

    def test_high_entropy_aggregates(self):
        """The specific values from the High Entropy node simulation."""
        assert _extract_msd(355) == 1   # 100 + 255
        assert _extract_msd(1101) == 1  # 1024 + 77
        assert _extract_msd(51) == 1    # 42 + 9
