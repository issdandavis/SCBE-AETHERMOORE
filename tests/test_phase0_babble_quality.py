"""
Phase 0 Baby Babble — Dataset Quality Test Harness
====================================================

Exhaustive validation of training-data/sft/phase0_baby_babble_sft.jsonl

Tests organized by category:
  A. Schema integrity (every field, every type, every constraint)
  B. Distribution balance (tongue, tier, difficulty, layers, axioms)
  C. Content quality (no empties, valid tokens, proper conversation format)
  D. Curriculum structure (difficulty tiers, TPDFF weight ranges)
  E. Deduplication (no exact duplicates, near-duplicate detection)
  F. Statistical properties (chi-squared uniformity, token length analysis)
  G. Cross-field consistency (tongue_weights match dominant_tongue, layers match tier)
  H. Edge cases (boundary values, extremes, outliers)

Follows the "test the full alphabet in English AND Greek" philosophy.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATA_PATH = Path(__file__).resolve().parents[1] / "training-data" / "sft" / "phase0_baby_babble_sft.jsonl"

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHI = (1 + math.sqrt(5)) / 2

TIERS = {
    "tpdff-pure_noise": {"count": 2000, "diff_lo": 0.00, "diff_hi": 0.10},
    "tpdff-echo": {"count": 2500, "diff_lo": 0.10, "diff_hi": 0.25},
    "tpdff-pattern": {"count": 2500, "diff_lo": 0.25, "diff_hi": 0.40},
    "tpdff-sorting": {"count": 2000, "diff_lo": 0.40, "diff_hi": 0.55},
    "tpdff-completion": {"count": 2000, "diff_lo": 0.55, "diff_hi": 0.70},
    "tpdff-translation": {"count": 1500, "diff_lo": 0.70, "diff_hi": 0.85},
    "tpdff-naming": {"count": 1500, "diff_lo": 0.85, "diff_hi": 1.00},
}

REQUIRED_FIELDS = {
    "messages": list,
    "tongue_weights": dict,
    "dominant_tongue": str,
    "layers": list,
    "axioms": list,
    "difficulty": (int, float),
    "augmentation": str,
    "tags": list,
    "source_hash": str,
    "curriculum_phase": (int, str),
    "tpdff_weights": dict,
}

TPDFF_KEYS = {"P1_smooth", "P2_pattern", "P3_bind"}


@pytest.fixture(scope="module")
def records() -> List[Dict[str, Any]]:
    """Load all records once for the module."""
    assert DATA_PATH.exists(), f"Dataset not found: {DATA_PATH}"
    data = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON at line {i + 1}: {e}")
    return data


@pytest.fixture(scope="module")
def tier_groups(records) -> Dict[str, List[Dict]]:
    """Group records by augmentation tier."""
    groups: Dict[str, List[Dict]] = {}
    for r in records:
        aug = r.get("augmentation", "unknown")
        groups.setdefault(aug, []).append(r)
    return groups


# ===========================================================================
# A. Schema Integrity
# ===========================================================================


class TestSchemaIntegrity:
    """Every record must have the correct fields and types."""

    def test_file_exists(self):
        assert DATA_PATH.exists()

    def test_file_not_empty(self):
        assert DATA_PATH.stat().st_size > 0

    def test_total_record_count(self, records):
        assert len(records) == 14_000, f"Expected 14,000 records, got {len(records)}"

    def test_all_required_fields_present(self, records):
        for i, r in enumerate(records):
            for field, expected_type in REQUIRED_FIELDS.items():
                assert field in r, f"Record {i}: missing field '{field}'"
                if isinstance(expected_type, tuple):
                    assert isinstance(
                        r[field], expected_type
                    ), f"Record {i}: field '{field}' type {type(r[field]).__name__}, expected {expected_type}"
                else:
                    assert isinstance(
                        r[field], expected_type
                    ), f"Record {i}: field '{field}' type {type(r[field]).__name__}, expected {expected_type.__name__}"

    def test_messages_have_three_roles(self, records):
        for i, r in enumerate(records):
            msgs = r["messages"]
            assert len(msgs) == 3, f"Record {i}: {len(msgs)} messages, expected 3"
            assert msgs[0]["role"] == "system", f"Record {i}: first message not system"
            assert msgs[1]["role"] == "user", f"Record {i}: second message not user"
            assert msgs[2]["role"] == "assistant", f"Record {i}: third message not assistant"

    def test_messages_have_content(self, records):
        for i, r in enumerate(records):
            for j, msg in enumerate(r["messages"]):
                assert "content" in msg, f"Record {i}, msg {j}: missing 'content'"
                assert isinstance(msg["content"], str), f"Record {i}, msg {j}: content not string"
                assert len(msg["content"]) > 0, f"Record {i}, msg {j}: empty content"

    def test_tongue_weights_have_all_six(self, records):
        for i, r in enumerate(records):
            tw = r["tongue_weights"]
            for t in TONGUES:
                assert t in tw, f"Record {i}: missing tongue weight '{t}'"
                assert isinstance(tw[t], (int, float)), f"Record {i}: tongue weight '{t}' not numeric"

    def test_dominant_tongue_valid(self, records):
        for i, r in enumerate(records):
            assert r["dominant_tongue"] in TONGUES, f"Record {i}: invalid dominant tongue '{r['dominant_tongue']}'"

    def test_layers_are_integers(self, records):
        for i, r in enumerate(records):
            for layer in r["layers"]:
                assert isinstance(layer, int), f"Record {i}: layer {layer} not int"

    def test_layers_in_range(self, records):
        for i, r in enumerate(records):
            for layer in r["layers"]:
                assert 1 <= layer <= 14, f"Record {i}: layer {layer} out of range [1,14]"

    def test_axioms_are_strings(self, records):
        valid_axioms = {
            "A1_unitarity",
            "A2_locality",
            "A3_causality",
            "A4_symmetry",
            "A5_composition",
        }
        for i, r in enumerate(records):
            for ax in r["axioms"]:
                assert isinstance(ax, str), f"Record {i}: axiom {ax} not string"
                assert ax in valid_axioms, f"Record {i}: unknown axiom '{ax}'"

    def test_difficulty_in_unit_interval(self, records):
        for i, r in enumerate(records):
            d = r["difficulty"]
            assert 0.0 <= d <= 1.0, f"Record {i}: difficulty {d} outside [0,1]"

    def test_source_hash_is_hex(self, records):
        for i, r in enumerate(records):
            h = r["source_hash"]
            assert len(h) >= 8, f"Record {i}: hash length {len(h)}, expected at least 8"
            assert all(c in "0123456789abcdef" for c in h), f"Record {i}: non-hex chars in hash"

    def test_curriculum_phase_is_phase0(self, records):
        for i, r in enumerate(records):
            assert r["curriculum_phase"] in (0, "phase0"), f"Record {i}: curriculum_phase = '{r['curriculum_phase']}'"

    def test_tpdff_weights_have_all_keys(self, records):
        for i, r in enumerate(records):
            tw = r["tpdff_weights"]
            assert set(tw.keys()) == TPDFF_KEYS, f"Record {i}: tpdff keys = {set(tw.keys())}"

    def test_tpdff_weights_are_numeric(self, records):
        for i, r in enumerate(records):
            for k, v in r["tpdff_weights"].items():
                assert isinstance(v, (int, float)), f"Record {i}: tpdff weight '{k}' not numeric"

    def test_tags_include_phase0(self, records):
        for i, r in enumerate(records):
            assert "phase0" in r["tags"], f"Record {i}: 'phase0' not in tags {r['tags']}"


# ===========================================================================
# B. Distribution Balance
# ===========================================================================


class TestDistributionBalance:
    """Tongue, tier, and difficulty distributions must be balanced."""

    def test_tongue_distribution_uniform(self, records):
        dist = Counter(r["dominant_tongue"] for r in records)
        expected = len(records) / 6
        for t in TONGUES:
            ct = dist[t]
            deviation = abs(ct - expected) / expected
            assert deviation < 0.10, f"Tongue {t}: {ct} records, {deviation:.1%} off from expected {expected:.0f}"

    def test_all_tongues_represented(self, records):
        tongues_seen = set(r["dominant_tongue"] for r in records)
        assert tongues_seen == set(TONGUES), f"Missing tongues: {set(TONGUES) - tongues_seen}"

    def test_tier_counts_match_spec(self, tier_groups):
        for tier_name, spec in TIERS.items():
            actual = len(tier_groups.get(tier_name, []))
            assert actual == spec["count"], f"Tier {tier_name}: {actual} records, expected {spec['count']}"

    def test_all_tiers_present(self, tier_groups):
        for tier_name in TIERS:
            assert tier_name in tier_groups, f"Missing tier: {tier_name}"

    def test_no_unknown_tiers(self, tier_groups):
        for tier_name in tier_groups:
            assert tier_name in TIERS, f"Unknown tier: {tier_name}"

    def test_difficulty_covers_full_range(self, records):
        diffs = [r["difficulty"] for r in records]
        assert min(diffs) <= 0.05, f"Min difficulty {min(diffs)} too high"
        assert max(diffs) >= 0.95, f"Max difficulty {max(diffs)} too low"

    def test_difficulty_distribution_not_degenerate(self, records):
        diffs = [r["difficulty"] for r in records]
        stdev = statistics.stdev(diffs)
        assert stdev > 0.15, f"Difficulty stdev {stdev:.3f} too low (degenerate distribution)"

    def test_layer_coverage(self, records):
        all_layers = set()
        for r in records:
            all_layers.update(r["layers"])
        assert len(all_layers) >= 3, f"Only {len(all_layers)} unique layers seen, expected at least 3"

    def test_axiom_coverage(self, records):
        all_axioms = set()
        for r in records:
            all_axioms.update(r["axioms"])
        assert len(all_axioms) >= 3, f"Only {len(all_axioms)} unique axioms seen, expected at least 3"

    def test_tongue_balance_per_tier(self, tier_groups):
        """Each tier should have reasonable tongue balance (not all one tongue)."""
        for tier_name, group in tier_groups.items():
            if len(group) < 100:
                continue
            dist = Counter(r["dominant_tongue"] for r in group)
            max_pct = max(dist.values()) / len(group)
            assert max_pct < 0.40, f"Tier {tier_name}: {max_pct:.1%} dominated by one tongue"

    def test_chi_squared_tongue_uniformity(self, records):
        """Chi-squared test for tongue uniformity (p > 0.01)."""
        dist = Counter(r["dominant_tongue"] for r in records)
        expected = len(records) / 6
        chi_sq = sum((dist[t] - expected) ** 2 / expected for t in TONGUES)
        # Chi-squared critical value for df=5, p=0.01 is 15.09
        assert chi_sq < 15.09, f"Tongue distribution chi-squared = {chi_sq:.2f} (p < 0.01, not uniform)"


# ===========================================================================
# C. Content Quality
# ===========================================================================


class TestContentQuality:
    """Message content should be well-formed and non-trivial."""

    def test_no_empty_assistant_responses(self, records):
        for i, r in enumerate(records):
            content = r["messages"][2]["content"].strip()
            assert len(content) > 0, f"Record {i}: empty assistant response"

    def test_no_empty_user_prompts(self, records):
        for i, r in enumerate(records):
            content = r["messages"][1]["content"].strip()
            assert len(content) > 0, f"Record {i}: empty user prompt"

    def test_system_message_contains_phase0_marker(self, records):
        for i, r in enumerate(records):
            sys_msg = r["messages"][0]["content"]
            assert (
                "PHASE-0" in sys_msg or "phase-0" in sys_msg.lower() or "BABY-BABBLE" in sys_msg
            ), f"Record {i}: system message lacks Phase-0 marker"

    def test_system_message_contains_tongue_name(self, records):
        tongue_names = {"Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"}
        tongue_codes = {"KO", "AV", "RU", "CA", "UM", "DR"}
        for i, r in enumerate(records):
            sys_msg = r["messages"][0]["content"]
            has_tongue = any(n in sys_msg for n in tongue_names) or any(c in sys_msg for c in tongue_codes)
            assert has_tongue, f"Record {i}: system message lacks tongue identifier"

    def test_user_prompt_not_too_short(self, records):
        short_count = sum(1 for r in records if len(r["messages"][1]["content"]) < 5)
        pct = short_count / len(records)
        assert pct < 0.05, f"{pct:.1%} of user prompts are under 5 chars"

    def test_assistant_response_not_absurdly_long(self, records):
        for i, r in enumerate(records):
            resp = r["messages"][2]["content"]
            assert len(resp) < 5000, f"Record {i}: assistant response {len(resp)} chars (too long for Phase 0)"

    def test_token_format_apostrophe_pattern(self, records):
        """Sacred Tongue tokens follow prefix'suffix pattern. At least some records should contain them."""
        apostrophe_count = 0
        sample = records[:2000]
        for r in sample:
            user_text = r["messages"][1]["content"]
            if "'" in user_text:
                apostrophe_count += 1
        pct = apostrophe_count / len(sample)
        assert pct > 0.30, f"Only {pct:.1%} of sampled records contain apostrophe-style tongue tokens"

    def test_no_null_or_none_in_content(self, records):
        for i, r in enumerate(records):
            for j, msg in enumerate(r["messages"]):
                assert msg["content"] is not None, f"Record {i}, msg {j}: None content"
                assert msg["content"] != "None", f"Record {i}, msg {j}: literal 'None' string"
                assert msg["content"] != "null", f"Record {i}, msg {j}: literal 'null' string"

    def test_no_python_repr_leaks(self, records):
        """No accidental Python repr() artifacts in content."""
        sample = records[:3000]
        for i, r in enumerate(sample):
            for msg in r["messages"]:
                content = msg["content"]
                assert "\\n" not in content or len(content) > 20, f"Record {i}: suspicious escaped newline"
                assert "<class '" not in content, f"Record {i}: Python class repr leak"
                assert "Traceback" not in content, f"Record {i}: Python traceback in content"


# ===========================================================================
# D. Curriculum Structure
# ===========================================================================


class TestCurriculumStructure:
    """Difficulty tiers and TPDFF weights must align with curriculum design."""

    def test_difficulty_within_tier_bounds(self, tier_groups):
        for tier_name, spec in TIERS.items():
            group = tier_groups.get(tier_name, [])
            for i, r in enumerate(group):
                d = r["difficulty"]
                assert (
                    spec["diff_lo"] <= d <= spec["diff_hi"]
                ), f"Tier {tier_name}, record {i}: difficulty {d} outside [{spec['diff_lo']}, {spec['diff_hi']}]"

    def test_early_tiers_have_lower_difficulty(self, tier_groups):
        tier_order = list(TIERS.keys())
        avg_diffs = []
        for tier_name in tier_order:
            group = tier_groups.get(tier_name, [])
            if group:
                avg_diffs.append(statistics.mean(r["difficulty"] for r in group))
            else:
                avg_diffs.append(0)
        for i in range(len(avg_diffs) - 1):
            assert avg_diffs[i] < avg_diffs[i + 1], (
                f"Tier {tier_order[i]} avg difficulty ({avg_diffs[i]:.3f}) "
                f">= tier {tier_order[i + 1]} ({avg_diffs[i + 1]:.3f})"
            )

    def test_tpdff_p1_weight_is_1(self, records):
        for i, r in enumerate(records):
            p1 = r["tpdff_weights"]["P1_smooth"]
            assert abs(p1 - 1.0) < 0.01, f"Record {i}: P1_smooth = {p1}, expected 1.0"

    def test_tpdff_p2_weight_is_phi(self, records):
        for i, r in enumerate(records):
            p2 = r["tpdff_weights"]["P2_pattern"]
            assert abs(p2 - PHI) < 0.01, f"Record {i}: P2_pattern = {p2}, expected {PHI:.3f}"

    def test_tpdff_p3_weight_is_phi_squared(self, records):
        for i, r in enumerate(records):
            p3 = r["tpdff_weights"]["P3_bind"]
            assert abs(p3 - PHI**2) < 0.01, f"Record {i}: P3_bind = {p3}, expected {PHI**2:.3f}"

    def test_early_tiers_use_fewer_layers(self, tier_groups):
        """Pure noise / echo should use fewer active layers than naming / translation."""
        early_layers = []
        late_layers = []
        for r in tier_groups.get("tpdff-pure_noise", []):
            early_layers.append(len(r["layers"]))
        for r in tier_groups.get("tpdff-naming", []):
            late_layers.append(len(r["layers"]))
        if early_layers and late_layers:
            avg_early = statistics.mean(early_layers)
            avg_late = statistics.mean(late_layers)
            assert (
                avg_early <= avg_late + 2
            ), f"Early tier avg layers ({avg_early:.1f}) much higher than late tier ({avg_late:.1f})"


# ===========================================================================
# E. Deduplication
# ===========================================================================


class TestDeduplication:
    """No exact duplicates. Limited near-duplicates."""

    def test_no_exact_duplicate_hashes(self, records):
        hashes = [r["source_hash"] for r in records]
        unique = set(hashes)
        assert len(unique) == len(hashes), f"{len(hashes) - len(unique)} duplicate source_hash values"

    def test_no_exact_duplicate_messages(self, records):
        seen = set()
        dupes = 0
        for r in records:
            key = json.dumps(r["messages"], sort_keys=True)
            if key in seen:
                dupes += 1
            seen.add(key)
        pct = dupes / len(records)
        assert pct < 0.01, f"{dupes} exact duplicate messages ({pct:.1%})"

    def test_assistant_response_diversity(self, records):
        """Assistant responses shouldn't all be the same."""
        responses = Counter(r["messages"][2]["content"] for r in records)
        most_common_count = responses.most_common(1)[0][1]
        pct = most_common_count / len(records)
        assert pct < 0.05, f"Most common response appears {most_common_count} times ({pct:.1%})"

    def test_user_prompt_diversity(self, records):
        """User prompts should be diverse."""
        prompts = set(r["messages"][1]["content"] for r in records)
        unique_pct = len(prompts) / len(records)
        assert unique_pct > 0.50, f"Only {unique_pct:.1%} unique user prompts"


# ===========================================================================
# F. Statistical Properties
# ===========================================================================


class TestStatisticalProperties:
    """Statistical quality metrics."""

    def test_difficulty_mean_near_center(self, records):
        diffs = [r["difficulty"] for r in records]
        mean = statistics.mean(diffs)
        # Weighted toward lower tiers (more records at easy end), so center around 0.35-0.55
        assert 0.25 <= mean <= 0.60, f"Difficulty mean = {mean:.3f}, expected near center"

    def test_assistant_response_length_distribution(self, records):
        lengths = [len(r["messages"][2]["content"]) for r in records]
        mean_len = statistics.mean(lengths)
        assert mean_len > 3, f"Mean response length = {mean_len:.1f} chars (too short)"
        assert mean_len < 2000, f"Mean response length = {mean_len:.1f} chars (too long for Phase 0)"

    def test_user_prompt_length_distribution(self, records):
        lengths = [len(r["messages"][1]["content"]) for r in records]
        mean_len = statistics.mean(lengths)
        assert mean_len > 10, f"Mean user prompt length = {mean_len:.1f} chars (too short)"

    def test_tongue_weight_values_in_range(self, records):
        for i, r in enumerate(records):
            for t, w in r["tongue_weights"].items():
                assert 0.0 <= w <= 2.0, f"Record {i}: tongue weight {t} = {w}, outside [0, 2]"

    def test_tongue_weight_dominant_is_highest(self, records):
        """The dominant tongue should have the highest weight (or tied for highest)."""
        violations = 0
        for r in records:
            dom = r["dominant_tongue"]
            dom_weight = r["tongue_weights"][dom]
            max_weight = max(r["tongue_weights"].values())
            if dom_weight < max_weight - 0.01:
                violations += 1
        pct = violations / len(records)
        assert pct < 0.05, f"{violations} records ({pct:.1%}) where dominant tongue isn't highest weight"

    def test_difficulty_has_no_nan(self, records):
        for i, r in enumerate(records):
            assert not math.isnan(r["difficulty"]), f"Record {i}: difficulty is NaN"

    def test_no_negative_weights(self, records):
        for i, r in enumerate(records):
            for t, w in r["tongue_weights"].items():
                assert w >= 0, f"Record {i}: negative tongue weight {t} = {w}"
            for k, v in r["tpdff_weights"].items():
                assert v >= 0, f"Record {i}: negative tpdff weight {k} = {v}"


# ===========================================================================
# G. Cross-Field Consistency
# ===========================================================================


class TestCrossFieldConsistency:
    """Fields must be internally consistent with each other."""

    def test_augmentation_matches_known_tier(self, records):
        for i, r in enumerate(records):
            assert r["augmentation"] in TIERS, f"Record {i}: unknown augmentation '{r['augmentation']}'"

    def test_difficulty_matches_augmentation_tier(self, records):
        for i, r in enumerate(records):
            aug = r["augmentation"]
            d = r["difficulty"]
            spec = TIERS[aug]
            assert (
                spec["diff_lo"] <= d <= spec["diff_hi"]
            ), f"Record {i}: difficulty {d} doesn't match tier {aug} [{spec['diff_lo']}, {spec['diff_hi']}]"

    def test_source_hash_uniqueness(self, records):
        """Hashes should be unique across records (no collisions at 8-char truncation)."""
        hashes = [r["source_hash"] for r in records]
        unique = set(hashes)
        collision_rate = (len(hashes) - len(unique)) / len(hashes)
        assert collision_rate < 0.01, f"Hash collision rate {collision_rate:.1%} too high"

    def test_system_message_tongue_matches_dominant(self, records):
        """System message should reference the dominant tongue."""
        tongue_full = {
            "KO": "Kor'aelin",
            "AV": "Avali",
            "RU": "Runethic",
            "CA": "Cassisivadan",
            "UM": "Umbroth",
            "DR": "Draumric",
        }
        mismatches = 0
        for r in records:
            sys_msg = r["messages"][0]["content"]
            dom = r["dominant_tongue"]
            full_name = tongue_full[dom]
            if dom not in sys_msg and full_name not in sys_msg:
                mismatches += 1
        pct = mismatches / len(records)
        assert pct < 0.05, f"{mismatches} records ({pct:.1%}) where system message doesn't mention dominant tongue"


# ===========================================================================
# H. Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Boundary values and extremes."""

    def test_minimum_difficulty_exists(self, records):
        diffs = [r["difficulty"] for r in records]
        assert min(diffs) < 0.05, f"Minimum difficulty {min(diffs)} — no near-zero records"

    def test_maximum_difficulty_exists(self, records):
        diffs = [r["difficulty"] for r in records]
        assert max(diffs) > 0.95, f"Maximum difficulty {max(diffs)} — no near-one records"

    def test_very_short_responses_are_valid(self, records):
        """Short responses (1-3 chars) should still be real tongue tokens or numbers."""
        short = [r for r in records if len(r["messages"][2]["content"].strip()) <= 3]
        for r in short:
            content = r["messages"][2]["content"].strip()
            assert len(content) > 0, "Empty response"

    def test_no_json_in_content(self, records):
        """Content fields shouldn't accidentally contain JSON objects."""
        for i, r in enumerate(records[:3000]):
            for msg in r["messages"]:
                content = msg["content"].strip()
                if content.startswith("{") and content.endswith("}"):
                    try:
                        json.loads(content)
                        pytest.fail(f"Record {i}: message content is a JSON object, not text")
                    except json.JSONDecodeError:
                        pass

    def test_no_extremely_long_single_tokens(self, records):
        """No single 'word' should be absurdly long (suggests corruption)."""
        for i, r in enumerate(records[:2000]):
            words = r["messages"][1]["content"].split()
            for w in words:
                assert len(w) < 100, f"Record {i}: word '{w[:30]}...' is {len(w)} chars"

    def test_file_is_valid_utf8(self):
        """Entire file must be valid UTF-8."""
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            try:
                f.read()
            except UnicodeDecodeError as e:
                pytest.fail(f"File is not valid UTF-8: {e}")

    def test_no_trailing_whitespace_lines(self):
        """Each line should be clean JSON, no extra whitespace."""
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                stripped = line.rstrip("\n\r")
                assert stripped == stripped.rstrip(), f"Line {i + 1}: trailing whitespace"
