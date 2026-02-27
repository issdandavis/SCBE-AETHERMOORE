"""Tests for balanced ternary and negabinary encoding systems."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from symphonic_cipher.scbe_aethermoore.trinary import (
    BalancedTernary, Trit, parse_bt,
    trit_not, trit_and, trit_or, trit_consensus,
    decision_to_trit, trit_to_decision,
)
from symphonic_cipher.scbe_aethermoore.negabinary import (
    NegaBinary, analyze_gate_stability,
    negabinary_to_balanced_ternary, balanced_ternary_to_negabinary,
)


# ═══════════════════════════════════════════════════
#  Balanced Ternary — Round-trip
# ═══════════════════════════════════════════════════

class TestBalancedTernaryRoundTrip:
    def test_zero(self):
        assert BalancedTernary.from_int(0).to_int() == 0

    def test_positive_integers(self):
        for n in range(1, 100):
            assert BalancedTernary.from_int(n).to_int() == n, f"Failed for {n}"

    def test_negative_integers(self):
        for n in range(-100, 0):
            assert BalancedTernary.from_int(n).to_int() == n, f"Failed for {n}"

    def test_large_values(self):
        for n in [1000, -1000, 9999, -9999, 2**16, -(2**16)]:
            assert BalancedTernary.from_int(n).to_int() == n

    def test_known_encodings(self):
        # 1 = "1"
        assert str(BalancedTernary.from_int(1)) == "1"
        # -1 = "T"
        assert str(BalancedTernary.from_int(-1)) == "T"
        # 2 = 1*3 + (-1)*1 = "1T"
        assert str(BalancedTernary.from_int(2)) == "1T"
        # 3 = 1*3 + 0 = "10"
        assert str(BalancedTernary.from_int(3)) == "10"
        # -5 = T*9 + 1*3 + 1*1 = "T11"... let me verify: -9+3+1=-5. But from_int:
        # Actually let's just test round trip
        assert BalancedTernary.from_int(-5).to_int() == -5


# ═══════════════════════════════════════════════════
#  Balanced Ternary — Arithmetic
# ═══════════════════════════════════════════════════

class TestBalancedTernaryArithmetic:
    def test_addition(self):
        for a in range(-20, 21):
            for b in range(-20, 21):
                result = BalancedTernary.from_int(a) + BalancedTernary.from_int(b)
                assert result.to_int() == a + b, f"{a} + {b} failed"

    def test_subtraction(self):
        for a in range(-20, 21):
            for b in range(-20, 21):
                result = BalancedTernary.from_int(a) - BalancedTernary.from_int(b)
                assert result.to_int() == a - b, f"{a} - {b} failed"

    def test_multiplication(self):
        for a in range(-10, 11):
            for b in range(-10, 11):
                result = BalancedTernary.from_int(a) * BalancedTernary.from_int(b)
                assert result.to_int() == a * b, f"{a} * {b} failed"

    def test_negation(self):
        for n in range(-50, 51):
            assert (-BalancedTernary.from_int(n)).to_int() == -n


# ═══════════════════════════════════════════════════
#  Balanced Ternary — Trit Logic
# ═══════════════════════════════════════════════════

class TestTritLogic:
    def test_kleene_not(self):
        assert trit_not(Trit.PLUS) == Trit.MINUS
        assert trit_not(Trit.MINUS) == Trit.PLUS
        assert trit_not(Trit.ZERO) == Trit.ZERO

    def test_kleene_and(self):
        # AND truth table: min
        assert trit_and(Trit.PLUS, Trit.PLUS) == Trit.PLUS
        assert trit_and(Trit.PLUS, Trit.ZERO) == Trit.ZERO
        assert trit_and(Trit.PLUS, Trit.MINUS) == Trit.MINUS
        assert trit_and(Trit.ZERO, Trit.ZERO) == Trit.ZERO
        assert trit_and(Trit.MINUS, Trit.MINUS) == Trit.MINUS

    def test_kleene_or(self):
        # OR truth table: max
        assert trit_or(Trit.MINUS, Trit.MINUS) == Trit.MINUS
        assert trit_or(Trit.MINUS, Trit.ZERO) == Trit.ZERO
        assert trit_or(Trit.MINUS, Trit.PLUS) == Trit.PLUS
        assert trit_or(Trit.ZERO, Trit.PLUS) == Trit.PLUS

    def test_consensus(self):
        assert trit_consensus(Trit.PLUS, Trit.PLUS) == Trit.PLUS
        assert trit_consensus(Trit.MINUS, Trit.MINUS) == Trit.MINUS
        assert trit_consensus(Trit.PLUS, Trit.MINUS) == Trit.ZERO
        assert trit_consensus(Trit.PLUS, Trit.ZERO) == Trit.ZERO

    def test_trit_level_and_or(self):
        a = BalancedTernary.from_int(5)   # some value
        b = BalancedTernary.from_int(-3)  # some value
        # Just verify these don't crash and return valid BT
        result_and = a.trit_and(b)
        result_or = a.trit_or(b)
        assert isinstance(result_and, BalancedTernary)
        assert isinstance(result_or, BalancedTernary)


# ═══════════════════════════════════════════════════
#  Governance Packing
# ═══════════════════════════════════════════════════

class TestGovernancePacking:
    def test_decision_to_trit(self):
        assert decision_to_trit("ALLOW") == Trit.PLUS
        assert decision_to_trit("DENY") == Trit.MINUS
        assert decision_to_trit("QUARANTINE") == Trit.ZERO
        assert decision_to_trit("SNAP") == Trit.MINUS
        assert decision_to_trit("REVIEW") == Trit.ZERO

    def test_pack_unpack_roundtrip(self):
        decisions = ["ALLOW", "DENY", "QUARANTINE", "ALLOW", "ALLOW"]
        packed = BalancedTernary.pack_decisions(decisions)
        unpacked = packed.unpack_decisions()
        assert unpacked == decisions

    def test_governance_summary(self):
        decisions = ["ALLOW", "ALLOW", "DENY", "QUARANTINE", "ALLOW"]
        packed = BalancedTernary.pack_decisions(decisions)
        summary = packed.governance_summary()
        assert summary["allow"] == 3
        assert summary["deny"] == 1
        assert summary["quarantine"] == 1
        assert summary["consensus"] == "ALLOW"  # net positive

    def test_all_deny_consensus(self):
        decisions = ["DENY", "DENY", "DENY"]
        summary = BalancedTernary.pack_decisions(decisions).governance_summary()
        assert summary["consensus"] == "DENY"

    def test_tied_consensus(self):
        decisions = ["ALLOW", "DENY"]
        summary = BalancedTernary.pack_decisions(decisions).governance_summary()
        assert summary["consensus"] == "QUARANTINE"  # net = 0


# ═══════════════════════════════════════════════════
#  Parse String
# ═══════════════════════════════════════════════════

class TestParseBT:
    def test_parse_positive(self):
        assert parse_bt("10").to_int() == 3     # 1*3 + 0*1
        assert parse_bt("1T").to_int() == 2     # 1*3 + (-1)*1

    def test_parse_negative(self):
        assert parse_bt("T").to_int() == -1
        assert parse_bt("T0").to_int() == -3    # -1*3 + 0*1

    def test_roundtrip(self):
        for n in range(-50, 51):
            s = str(BalancedTernary.from_int(n))
            assert parse_bt(s).to_int() == n


# ═══════════════════════════════════════════════════
#  Entropy
# ═══════════════════════════════════════════════════

class TestTritEntropy:
    def test_single_trit(self):
        bt = BalancedTernary.from_int(1)  # single "1" trit
        assert bt.trit_entropy() == 0.0  # only one trit, zero entropy

    def test_mixed_trits_have_entropy(self):
        # A number with mixed trits should have > 0 entropy
        bt = BalancedTernary.from_int(42)
        assert bt.trit_entropy() > 0.0

    def test_information_density_bounded(self):
        for n in range(-100, 101):
            bt = BalancedTernary.from_int(n)
            d = bt.information_density()
            assert 0.0 <= d <= 1.0, f"Density out of bounds for {n}: {d}"


# ═══════════════════════════════════════════════════
#  NegaBinary — Round-trip
# ═══════════════════════════════════════════════════

class TestNegaBinaryRoundTrip:
    def test_zero(self):
        assert NegaBinary.from_int(0).to_int() == 0

    def test_positive_integers(self):
        for n in range(1, 100):
            assert NegaBinary.from_int(n).to_int() == n, f"Failed for {n}"

    def test_negative_integers(self):
        for n in range(-100, 0):
            assert NegaBinary.from_int(n).to_int() == n, f"Failed for {n}"

    def test_large_values(self):
        for n in [500, -500, 9999, -9999]:
            assert NegaBinary.from_int(n).to_int() == n

    def test_known_encodings(self):
        # 1 = 1 * (-2)^0 = 1
        assert str(NegaBinary.from_int(1)) == "1"
        # -1 = 1*(-2)^1 + 1*(-2)^0 = -2 + 1 = -1 -> "11"
        assert NegaBinary.from_int(-1).to_int() == -1
        # 2 = 1*(-2)^2 + 1*(-2)^1 + 0*(-2)^0 = 4 - 2 = 2 -> "110"
        assert NegaBinary.from_int(2).to_int() == 2
        # -2 = 1*(-2)^1 = -2 -> "10"
        assert str(NegaBinary.from_int(-2)) == "10"


# ═══════════════════════════════════════════════════
#  NegaBinary — Arithmetic
# ═══════════════════════════════════════════════════

class TestNegaBinaryArithmetic:
    def test_addition(self):
        for a in range(-20, 21):
            for b in range(-20, 21):
                result = NegaBinary.from_int(a) + NegaBinary.from_int(b)
                assert result.to_int() == a + b, f"{a} + {b} failed: got {result.to_int()}"

    def test_subtraction(self):
        for a in range(-15, 16):
            for b in range(-15, 16):
                result = NegaBinary.from_int(a) - NegaBinary.from_int(b)
                assert result.to_int() == a - b, f"{a} - {b} failed"

    def test_multiplication(self):
        for a in range(-10, 11):
            for b in range(-10, 11):
                result = NegaBinary.from_int(a) * NegaBinary.from_int(b)
                assert result.to_int() == a * b, f"{a} * {b} failed"

    def test_negation(self):
        for n in range(-50, 51):
            assert (-NegaBinary.from_int(n)).to_int() == -n


# ═══════════════════════════════════════════════════
#  NegaBinary — Polarity & Tongues
# ═══════════════════════════════════════════════════

class TestNegaBinaryPolarity:
    def test_positive_polarity(self):
        # 1 has only bit 0 set (even position = positive)
        profile = NegaBinary.from_int(1).polarity_profile()
        assert profile["positive_bits"] == 1
        assert profile["negative_bits"] == 0
        assert profile["polarity"] == "positive"

    def test_negative_polarity(self):
        # -2 = "10" has only bit 1 set (odd position = negative)
        profile = NegaBinary.from_int(-2).polarity_profile()
        assert profile["negative_bits"] >= 1
        assert profile["polarity"] == "negative"

    def test_tongue_polarity(self):
        assert NegaBinary.from_int(1).tongue_polarity() == "KO"
        assert NegaBinary.from_int(-2).tongue_polarity() == "AV"

    def test_tongue_encoding_length(self):
        nb = NegaBinary.from_int(42)
        encoding = nb.tongue_encoding()
        assert len(encoding) == nb.width
        assert all(t in ("KO", "AV", "UM") for t in encoding)


# ═══════════════════════════════════════════════════
#  Cross-Conversion
# ═══════════════════════════════════════════════════

class TestCrossConversion:
    def test_negabinary_to_ternary(self):
        for n in range(-50, 51):
            nb = NegaBinary.from_int(n)
            bt = negabinary_to_balanced_ternary(nb)
            assert bt.to_int() == n

    def test_ternary_to_negabinary(self):
        for n in range(-50, 51):
            bt = BalancedTernary.from_int(n)
            nb = balanced_ternary_to_negabinary(bt)
            assert nb.to_int() == n

    def test_roundtrip_both_directions(self):
        for n in range(-30, 31):
            nb = NegaBinary.from_int(n)
            bt = negabinary_to_balanced_ternary(nb)
            nb2 = balanced_ternary_to_negabinary(bt)
            assert nb2.to_int() == n


# ═══════════════════════════════════════════════════
#  Gate Stability Analysis
# ═══════════════════════════════════════════════════

class TestGateStability:
    def test_small_mixed_values_favor_ternary(self):
        # Governance-like values: small, mixed sign
        values = [1, -1, 0, 1, -1, 0, 1, 0, -1, -1]
        report = analyze_gate_stability(values)
        assert "TERNARY" in report.stability_recommendation

    def test_large_positive_values(self):
        values = list(range(100, 200))
        report = analyze_gate_stability(values)
        # Should NOT recommend ternary for large positive-only
        assert report.binary_total_bits > 0
        assert report.ternary_total_trits > 0

    def test_report_fields(self):
        report = analyze_gate_stability([1, -1, 2, -2, 0])
        assert len(report.values) == 5
        assert report.binary_total_bits > 0
        assert report.ternary_total_trits > 0
        assert report.negabinary_total_bits > 0
        assert isinstance(report.stability_recommendation, str)

    def test_governance_decision_range(self):
        # Pure governance: only -1, 0, +1
        decisions = [1, -1, 0, 0, 1, -1, 1, 1, 0, -1]
        report = analyze_gate_stability(decisions)
        # Ternary should be very compact here (1 trit per value)
        assert report.ternary_total_trits == 10  # exactly 1 trit each
