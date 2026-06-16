"""Tests for the Wolfram face — 256 tokens mapped to the 256 ECA rules."""

from __future__ import annotations

import pytest

from python.scbe.wolfram_face import (
    UNIVERSAL_RULES,
    classify,
    full_map,
    step,
    token_rule,
)


class TestStep:
    def test_rule_0_clears_to_zero(self):
        assert step([1, 0, 1, 1, 0], 0) == [0, 0, 0, 0, 0]

    def test_rule_255_fills_to_one(self):
        assert step([1, 0, 1, 1, 0], 255) == [1, 1, 1, 1, 1]

    def test_rule_110_known_neighbourhood(self):
        # Rule 110 = 0b01101110; neighbourhood 010 (=2) -> bit 2 -> 1.
        out = step([0, 1, 0], 110)  # cell 1 sees (0,1,0)=010
        assert out[1] == 1


class TestMap:
    def test_full_map_is_256(self):
        m = full_map()
        assert len(m) == 256
        assert [e["rule"] for e in m] == list(range(256))

    def test_token_index_equals_rule(self):
        assert token_rule(42)["rule"] == 42
        assert token_rule(42)["wolfram_code_bits"] == "00101010"

    def test_index_out_of_range_rejected(self):
        for bad in (-1, 256, 999):
            with pytest.raises(ValueError):
                token_rule(bad)


class TestClasses:
    def test_universal_rules_are_class_iv(self):
        for r in UNIVERSAL_RULES:
            t = token_rule(r)
            assert t["class"] == "IV", r
            assert t["universal"] is True, r

    def test_iconic_rule_anchors(self):
        assert token_rule(0)["class"] == "I"  # blank -> homogeneous
        assert token_rule(255)["class"] == "I"  # fill -> homogeneous
        assert token_rule(30)["class"] == "III"  # Rule 30 -> chaotic
        assert token_rule(110)["class"] == "IV"  # Rule 110 -> complex/universal

    def test_classify_is_deterministic(self):
        # No RNG anywhere — same rule must classify identically every call.
        for r in (18, 30, 90, 110, 184, 250):
            assert classify(r) == classify(r)

    def test_only_known_classes_emitted(self):
        assert {e["class"] for e in full_map()} <= {"I", "II", "III", "IV"}
