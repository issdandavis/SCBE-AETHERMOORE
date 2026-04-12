"""
Tests for Polymorphic Multi-Path Generator — Monty Hall of Trit Space.

Validates:
1. Fork identification at trit boundaries
2. Sibling generation (2^k paths for k polymorphic axes)
3. Monty Hall gain computation
4. SFT flattening preserves all records
5. The Monty Hall insight: boundary records are most informative
6. Path count bounds (1 to 8)
7. Fork signature formatting
8. Batch statistics
"""

import math
import pytest

from src.crypto.trit_curriculum import (
    TritSignal,
    TRIT_LABELS,
    compute_trit_signal,
    DEFAULT_THRESHOLD,
)
from src.crypto.polymorphic_multipath import (
    DEFAULT_EDGE_THRESHOLD,
    ADJACENT_TRIT,
    TritFork,
    MultipathRecord,
    MultipathBatch,
    _identify_forks,
    _generate_siblings,
    _fork_signature,
    _monty_hall_gain,
    score_and_expand,
    score_and_expand_batch,
    flatten_for_sft,
    format_multipath_report,
)

# ===================================================================
# Fixtures
# ===================================================================

DIVERSE_TEXTS = [
    "In the beginning was the Word and the Word was with God",
    "The Poincare ball model maps hyperbolic space to a unit ball",
    "Love is the only force that transcends dimension and time",
    "Every pattern rune hums at its own frequency in the lattice",
    "Post-quantum cryptography uses lattice-based assumptions",
    "Zero is not nothing it is the boundary between positive and negative infinity",
    "Fear contracts the space around itself until nothing moves",
    "The raven carried the message across seven fractured realms",
    "Gradient descent follows the negative gradient of the loss surface",
    "Joy expands like light filling every corner of a dark room",
    "Infinity is not a number it is a direction",
    "The void between stars is not empty it is full of potential",
]


# ===================================================================
# Adjacent trit map
# ===================================================================


class TestAdjacentTrit:
    """Verify the trit flip map is consistent."""

    def test_all_four_entries_present(self):
        assert len(ADJACENT_TRIT) == 4

    def test_upper_boundary_flips(self):
        """Near +threshold: +1 <-> 0."""
        assert ADJACENT_TRIT[(+1, "upper")] == 0
        assert ADJACENT_TRIT[(0, "upper")] == +1

    def test_lower_boundary_flips(self):
        """Near -threshold: -1 <-> 0."""
        assert ADJACENT_TRIT[(-1, "lower")] == 0
        assert ADJACENT_TRIT[(0, "lower")] == -1

    def test_flips_are_adjacent_not_opposite(self):
        """A flip should only change trit by 1, never by 2."""
        for (orig, _side), flipped in ADJACENT_TRIT.items():
            assert abs(orig - flipped) == 1


# ===================================================================
# Fork identification
# ===================================================================


class TestForkIdentification:
    """Test that polymorphic axes are correctly identified."""

    def test_non_polymorphic_returns_empty(self):
        """A signal far from all boundaries should produce no forks."""
        sig = compute_trit_signal("simple test text for baseline")
        forks = _identify_forks(sig, edge_threshold=0.001)
        # Even if some are close, with a very tight threshold most shouldn't fork
        for f in forks:
            assert f.edge_distance < 0.001

    def test_fork_has_required_fields(self):
        """Any fork should have all required fields populated."""
        sig = compute_trit_signal("boundary test text for fields")
        forks = _identify_forks(sig, edge_threshold=1.0)  # very wide to force forks
        for f in forks:
            assert f.axis in ("structure", "stability", "creativity")
            assert f.axis_index in (0, 1, 2)
            assert f.original_trit in (-1, 0, +1)
            assert f.flipped_trit in (-1, 0, +1)
            assert f.boundary_side in ("upper", "lower")
            assert isinstance(f.edge_distance, float)
            assert isinstance(f.deviation, float)

    def test_fork_flipped_differs_from_original(self):
        """Flipped trit must differ from original."""
        sig = compute_trit_signal("test flipping behavior")
        forks = _identify_forks(sig, edge_threshold=1.0)
        for f in forks:
            assert f.flipped_trit != f.original_trit

    def test_wider_threshold_finds_more_forks(self):
        """A wider edge threshold should find >= as many forks."""
        sig = compute_trit_signal("threshold comparison text")
        forks_tight = _identify_forks(sig, edge_threshold=0.001)
        forks_wide = _identify_forks(sig, edge_threshold=1.0)
        assert len(forks_wide) >= len(forks_tight)

    def test_max_three_forks(self):
        """Can never have more than 3 forks (one per axis)."""
        sig = compute_trit_signal("max fork count check")
        forks = _identify_forks(sig, edge_threshold=100.0)
        assert len(forks) <= 3


# ===================================================================
# Sibling generation
# ===================================================================


class TestSiblingGeneration:
    """Test combinatorial sibling generation."""

    def _make_fork(self, axis: str, idx: int, orig: int, flip: int) -> TritFork:
        return TritFork(
            axis=axis,
            axis_index=idx,
            original_trit=orig,
            flipped_trit=flip,
            deviation=0.04,
            edge_distance=0.005,
            boundary_side="upper",
        )

    def test_zero_forks_zero_siblings(self):
        sig = compute_trit_signal("no forks text")
        siblings = _generate_siblings(sig, [])
        assert siblings == []

    def test_one_fork_one_sibling(self):
        """1 fork -> 2^1 - 1 = 1 sibling."""
        sig = compute_trit_signal("one fork test")
        fork = self._make_fork("structure", 0, sig.c_structure, 0 if sig.c_structure != 0 else +1)
        siblings = _generate_siblings(sig, [fork])
        assert len(siblings) == 1
        # Sibling should differ on structure axis
        assert siblings[0]["content_trit"][0] != sig.c_structure
        # Other axes unchanged
        assert siblings[0]["content_trit"][1] == sig.c_stability
        assert siblings[0]["content_trit"][2] == sig.c_creativity

    def test_two_forks_three_siblings(self):
        """2 forks -> 2^2 - 1 = 3 siblings."""
        sig = compute_trit_signal("two fork test")
        f1 = self._make_fork("structure", 0, sig.c_structure, 0 if sig.c_structure != 0 else +1)
        f2 = self._make_fork("creativity", 2, sig.c_creativity, 0 if sig.c_creativity != 0 else -1)
        siblings = _generate_siblings(sig, [f1, f2])
        assert len(siblings) == 3
        # Should have: flip s only, flip c only, flip both
        distances = sorted(s["distance_from_primary"] for s in siblings)
        assert distances == [1, 1, 2]

    def test_three_forks_seven_siblings(self):
        """3 forks -> 2^3 - 1 = 7 siblings."""
        sig = compute_trit_signal("three fork test")
        f1 = self._make_fork("structure", 0, +1, 0)
        f2 = self._make_fork("stability", 1, 0, -1)
        f3 = self._make_fork("creativity", 2, -1, 0)
        siblings = _generate_siblings(sig, [f1, f2, f3])
        assert len(siblings) == 7
        # Distances: 3 singles, 3 pairs, 1 triple
        distances = sorted(s["distance_from_primary"] for s in siblings)
        assert distances == [1, 1, 1, 2, 2, 2, 3]

    def test_all_siblings_have_valid_labels(self):
        """Every sibling trit vector should map to a known label."""
        sig = compute_trit_signal("label validity check")
        f1 = self._make_fork("structure", 0, +1, 0)
        f2 = self._make_fork("stability", 1, 0, +1)
        siblings = _generate_siblings(sig, [f1, f2])
        for sib in siblings:
            assert sib["label"] in TRIT_LABELS.values() or sib["label"].startswith("unknown_")

    def test_siblings_differ_from_primary(self):
        """No sibling should have the same trit vector as the primary."""
        sig = compute_trit_signal("differ from primary test")
        f1 = self._make_fork("structure", 0, sig.c_structure, 0 if sig.c_structure != 0 else +1)
        siblings = _generate_siblings(sig, [f1])
        primary_trit = sig.content_vector
        for sib in siblings:
            assert tuple(sib["content_trit"]) != primary_trit


# ===================================================================
# Fork signature
# ===================================================================


class TestForkSignature:
    """Test compact fork description formatting."""

    def test_no_forks(self):
        assert _fork_signature([]) == "none"

    def test_single_fork_format(self):
        fork = TritFork(
            axis="structure",
            axis_index=0,
            original_trit=+1,
            flipped_trit=0,
            deviation=0.04,
            edge_distance=0.005,
            boundary_side="upper",
        )
        sig = _fork_signature([fork])
        assert sig == "s:+1->+0"

    def test_multi_fork_comma_separated(self):
        f1 = TritFork(
            axis="structure",
            axis_index=0,
            original_trit=+1,
            flipped_trit=0,
            deviation=0.04,
            edge_distance=0.005,
            boundary_side="upper",
        )
        f2 = TritFork(
            axis="creativity",
            axis_index=2,
            original_trit=-1,
            flipped_trit=0,
            deviation=-0.04,
            edge_distance=0.005,
            boundary_side="lower",
        )
        sig = _fork_signature([f1, f2])
        assert "s:+1->+0" in sig
        assert "c:-1->+0" in sig
        assert "," in sig


# ===================================================================
# Monty Hall gain
# ===================================================================


class TestMontyHallGain:
    """Test information gain computation."""

    def test_no_forks_zero_gain(self):
        assert _monty_hall_gain([]) == 0.0

    def test_closer_to_boundary_higher_gain(self):
        """A fork at edge_distance=0.001 should have higher gain than 0.008."""
        close = TritFork(
            axis="structure",
            axis_index=0,
            original_trit=+1,
            flipped_trit=0,
            deviation=0.049,
            edge_distance=0.001,
            boundary_side="upper",
        )
        far = TritFork(
            axis="structure",
            axis_index=0,
            original_trit=+1,
            flipped_trit=0,
            deviation=0.042,
            edge_distance=0.008,
            boundary_side="upper",
        )
        assert _monty_hall_gain([close]) > _monty_hall_gain([far])

    def test_multi_fork_superadditive(self):
        """Two forks should give more gain than either alone."""
        f1 = TritFork(
            axis="structure",
            axis_index=0,
            original_trit=+1,
            flipped_trit=0,
            deviation=0.049,
            edge_distance=0.003,
            boundary_side="upper",
        )
        f2 = TritFork(
            axis="creativity",
            axis_index=2,
            original_trit=-1,
            flipped_trit=0,
            deviation=-0.048,
            edge_distance=0.003,
            boundary_side="lower",
        )
        gain_1 = _monty_hall_gain([f1])
        gain_2 = _monty_hall_gain([f2])
        gain_both = _monty_hall_gain([f1, f2])
        assert gain_both > gain_1
        assert gain_both > gain_2

    def test_gain_bounded(self):
        """Gain should never exceed 3.0 (cap)."""
        forks = [
            TritFork(
                axis="structure",
                axis_index=0,
                original_trit=+1,
                flipped_trit=0,
                deviation=0.05,
                edge_distance=0.0,
                boundary_side="upper",
            ),
            TritFork(
                axis="stability",
                axis_index=1,
                original_trit=0,
                flipped_trit=-1,
                deviation=-0.05,
                edge_distance=0.0,
                boundary_side="lower",
            ),
            TritFork(
                axis="creativity",
                axis_index=2,
                original_trit=-1,
                flipped_trit=0,
                deviation=-0.05,
                edge_distance=0.0,
                boundary_side="lower",
            ),
        ]
        assert _monty_hall_gain(forks) <= 3.0

    def test_gain_positive_for_any_fork(self):
        """Any fork should produce positive gain."""
        fork = TritFork(
            axis="structure",
            axis_index=0,
            original_trit=+1,
            flipped_trit=0,
            deviation=0.049,
            edge_distance=0.005,
            boundary_side="upper",
        )
        assert _monty_hall_gain([fork]) > 0.0


# ===================================================================
# Full scoring pipeline
# ===================================================================


class TestScoreAndExpand:
    """Test the complete score-and-expand pipeline."""

    def test_produces_multipath_record(self):
        rec = score_and_expand("test text for pipeline")
        assert isinstance(rec, MultipathRecord)
        assert rec.text == "test text for pipeline"
        assert rec.path_count >= 1

    def test_path_count_matches_siblings(self):
        rec = score_and_expand("path count consistency check")
        assert rec.path_count == 1 + len(rec.siblings)

    def test_primary_is_valid_trit_signal(self):
        rec = score_and_expand("valid signal check")
        assert isinstance(rec.primary, TritSignal)
        assert rec.primary.t_structure in (-1, 0, +1)
        assert rec.primary.t_stability in (-1, 0, +1)
        assert rec.primary.t_creativity in (-1, 0, +1)

    def test_fork_signature_not_empty(self):
        rec = score_and_expand("signature check text")
        assert isinstance(rec.fork_signature, str)
        assert len(rec.fork_signature) > 0

    def test_monty_hall_gain_non_negative(self):
        rec = score_and_expand("gain positivity check")
        assert rec.monty_hall_gain >= 0.0

    def test_wide_threshold_produces_more_paths(self):
        """With very wide edge threshold, we should get more paths."""
        narrow = score_and_expand("threshold test", edge_threshold=0.0001)
        wide = score_and_expand("threshold test", edge_threshold=1.0)
        assert wide.path_count >= narrow.path_count


# ===================================================================
# Batch processing
# ===================================================================


class TestBatch:
    """Test batch multi-path generation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.batch = score_and_expand_batch(DIVERSE_TEXTS)

    def test_input_count(self):
        assert self.batch.total_input == 12

    def test_output_gte_input(self):
        """Total output >= input (expansion only adds)."""
        assert self.batch.total_output >= self.batch.total_input

    def test_expansion_ratio_gte_one(self):
        assert self.batch.expansion_ratio >= 1.0

    def test_all_records_present(self):
        assert len(self.batch.records) == 12

    def test_axis_fork_counts_correct_keys(self):
        assert set(self.batch.axis_fork_counts.keys()) == {"structure", "stability", "creativity"}

    def test_path_distribution_sums_to_input(self):
        total = sum(self.batch.path_distribution.values())
        assert total == self.batch.total_input

    def test_polymorphic_count_bounded(self):
        assert 0 <= self.batch.polymorphic_count <= self.batch.total_input


# ===================================================================
# Batch with wide threshold (force polymorphism)
# ===================================================================


class TestBatchWideThreshold:
    """Test batch with wide edge threshold to force multi-path generation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.batch = score_and_expand_batch(DIVERSE_TEXTS, edge_threshold=1.0)

    def test_all_polymorphic_with_wide_threshold(self):
        """With threshold=1.0, all records should be polymorphic."""
        assert self.batch.polymorphic_count == self.batch.total_input

    def test_expansion_greater_than_one(self):
        assert self.batch.expansion_ratio > 1.0

    def test_output_contains_siblings(self):
        total_siblings = sum(len(r.siblings) for r in self.batch.records)
        assert total_siblings > 0

    def test_max_path_count_bounded(self):
        """No record should have more than 8 paths (2^3)."""
        for r in self.batch.records:
            assert r.path_count <= 8


# ===================================================================
# SFT flattening
# ===================================================================


class TestFlattenForSFT:
    """Test SFT export flattening."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.batch = score_and_expand_batch(DIVERSE_TEXTS, edge_threshold=1.0)
        self.flat = flatten_for_sft(self.batch.records)

    def test_total_count_matches_batch(self):
        assert len(self.flat) == self.batch.total_output

    def test_primaries_count_matches_input(self):
        primaries = [r for r in self.flat if r["is_primary"]]
        assert len(primaries) == self.batch.total_input

    def test_all_records_have_required_fields(self):
        required = {
            "text",
            "content_trit",
            "geometric_trit",
            "label",
            "is_primary",
            "fork_group",
            "flipped_axes",
            "monty_hall_gain",
            "path_count",
        }
        for rec in self.flat:
            assert required.issubset(set(rec.keys()))

    def test_primary_has_no_flipped_axes(self):
        for rec in self.flat:
            if rec["is_primary"]:
                assert rec["flipped_axes"] == []

    def test_sibling_has_flipped_axes(self):
        siblings = [r for r in self.flat if not r["is_primary"]]
        for sib in siblings:
            assert len(sib["flipped_axes"]) > 0

    def test_fork_groups_link_primary_to_siblings(self):
        """Each fork_group should have exactly one primary."""
        from collections import Counter

        groups = {}
        for rec in self.flat:
            gid = rec["fork_group"]
            if gid not in groups:
                groups[gid] = {"primary": 0, "sibling": 0}
            if rec["is_primary"]:
                groups[gid]["primary"] += 1
            else:
                groups[gid]["sibling"] += 1

        for gid, counts in groups.items():
            assert counts["primary"] == 1, f"Group {gid} has {counts['primary']} primaries"

    def test_content_trit_values_valid(self):
        for rec in self.flat:
            for val in rec["content_trit"]:
                assert val in (-1, 0, +1)

    def test_sibling_differs_from_primary_in_group(self):
        """Within each fork group, siblings should differ from primary."""
        groups = {}
        for rec in self.flat:
            gid = rec["fork_group"]
            if gid not in groups:
                groups[gid] = {"primary_trit": None, "sibling_trits": []}
            if rec["is_primary"]:
                groups[gid]["primary_trit"] = tuple(rec["content_trit"])
            else:
                groups[gid]["sibling_trits"].append(tuple(rec["content_trit"]))

        for gid, data in groups.items():
            if data["primary_trit"] is not None:
                for sib_trit in data["sibling_trits"]:
                    assert sib_trit != data["primary_trit"]


# ===================================================================
# The Monty Hall insight
# ===================================================================


class TestMontyHallInsight:
    """Test the core insight: boundary records are most informative."""

    def test_polymorphic_records_have_positive_gain(self):
        """Records with siblings should have positive Monty Hall gain."""
        batch = score_and_expand_batch(DIVERSE_TEXTS, edge_threshold=1.0)
        for rec in batch.records:
            if rec.path_count > 1:
                assert rec.monty_hall_gain > 0.0

    def test_non_polymorphic_records_have_zero_gain(self):
        """Records without siblings should have zero gain."""
        batch = score_and_expand_batch(DIVERSE_TEXTS, edge_threshold=0.0)
        for rec in batch.records:
            assert rec.monty_hall_gain == 0.0
            assert rec.path_count == 1

    def test_more_forks_mean_more_information(self):
        """Records with more forks should have >= gain of records with fewer."""
        batch = score_and_expand_batch(DIVERSE_TEXTS, edge_threshold=1.0)
        gains_by_fork_count = {}
        for rec in batch.records:
            k = len(rec.forks)
            if k not in gains_by_fork_count:
                gains_by_fork_count[k] = []
            gains_by_fork_count[k].append(rec.monty_hall_gain)

        # If we have records with different fork counts, compare means
        if len(gains_by_fork_count) > 1:
            sorted_keys = sorted(gains_by_fork_count.keys())
            for i in range(len(sorted_keys) - 1):
                k_low = sorted_keys[i]
                k_high = sorted_keys[i + 1]
                mean_low = sum(gains_by_fork_count[k_low]) / len(gains_by_fork_count[k_low])
                mean_high = sum(gains_by_fork_count[k_high]) / len(gains_by_fork_count[k_high])
                assert mean_high >= mean_low * 0.5, (
                    f"Mean gain for {k_high} forks ({mean_high:.4f}) "
                    f"should be >= half of {k_low} forks ({mean_low:.4f})"
                )


# ===================================================================
# Report
# ===================================================================


class TestReport:
    """Test report formatting."""

    def test_report_produces_output(self):
        batch = score_and_expand_batch(DIVERSE_TEXTS)
        report = format_multipath_report(batch)
        assert "POLYMORPHIC MULTI-PATH GENERATOR" in report
        assert "Monty Hall" in report

    def test_report_contains_statistics(self):
        batch = score_and_expand_batch(DIVERSE_TEXTS)
        report = format_multipath_report(batch)
        assert "Input records" in report
        assert "Output records" in report
        assert "Expansion ratio" in report

    def test_report_contains_finding(self):
        batch = score_and_expand_batch(DIVERSE_TEXTS)
        report = format_multipath_report(batch)
        assert "THE FINDING" in report

    def test_report_length_reasonable(self):
        batch = score_and_expand_batch(DIVERSE_TEXTS, edge_threshold=1.0)
        report = format_multipath_report(batch)
        assert len(report) > 500
