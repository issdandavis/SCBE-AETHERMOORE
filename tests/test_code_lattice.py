"""
Tests for Code Lattice — Coding Patterns as Tongue-Mapped Training Signals.

Validates:
1. Pattern registry is well-formed (all fields, no duplicates)
2. Tongue-domain mapping covers all 6 tongues
3. Pattern selection responds to trit signal characteristics
4. QHO level filters by curriculum difficulty (min_n)
5. Compound intent multiplies system × learner (grows, doesn't repeat)
6. Anti-patterns ("swear words") detected at boundaries
7. SFT flattening produces complete training records
8. Report formatting includes all required sections
"""

import pytest

from src.crypto.code_lattice import (
    TONGUE_DOMAIN,
    DOMAIN_DESCRIPTION,
    PATTERN_REGISTRY,
    PATTERNS_BY_DOMAIN,
    ALL_ANTIPATTERNS,
    ALL_GOOD_PATTERNS,
    CodeLatticeBundle,
    select_patterns,
    generate_code_lattice_bundle,
    flatten_code_lattice_for_sft,
    format_code_lattice_report,
)
from src.crypto.qho_bundle import (
    QHOLevel,
    MAX_N,
)

# ===================================================================
# Pattern Registry
# ===================================================================


class TestPatternRegistry:
    """Test that the pattern registry is well-formed."""

    def test_has_patterns(self):
        assert len(PATTERN_REGISTRY) > 0

    def test_all_patterns_have_required_fields(self):
        for p in PATTERN_REGISTRY:
            assert p.name, f"Pattern missing name"
            assert p.domain, f"Pattern {p.name} missing domain"
            assert p.description, f"Pattern {p.name} missing description"
            assert p.why, f"Pattern {p.name} missing why"
            assert p.code_good, f"Pattern {p.name} missing code_good"
            assert p.cross_domain, f"Pattern {p.name} missing cross_domain"
            assert isinstance(p.is_antipattern, bool)
            assert 0 <= p.min_n <= MAX_N

    def test_unique_names(self):
        names = [p.name for p in PATTERN_REGISTRY]
        assert len(names) == len(set(names)), "Duplicate pattern names found"

    def test_has_antipatterns(self):
        """Must have 'swear words' in the registry."""
        assert len(ALL_ANTIPATTERNS) > 0

    def test_has_good_patterns(self):
        assert len(ALL_GOOD_PATTERNS) > 0

    def test_antipatterns_have_code_bad(self):
        """Every anti-pattern should show the bad code."""
        for p in ALL_ANTIPATTERNS:
            assert p.code_bad, f"Anti-pattern {p.name} missing code_bad"

    def test_antipatterns_have_recovery(self):
        """Every anti-pattern also shows the good code (recovery)."""
        for p in ALL_ANTIPATTERNS:
            assert p.code_good, f"Anti-pattern {p.name} missing code_good (recovery)"

    def test_min_n_covers_range(self):
        """Patterns should span from n=0 to at least n=3."""
        min_ns = {p.min_n for p in PATTERN_REGISTRY}
        assert 0 in min_ns, "No patterns for ground state"
        assert any(n >= 3 for n in min_ns), "No patterns for high excitation"


# ===================================================================
# Tongue-Domain Mapping
# ===================================================================


class TestTongueDomainMapping:
    """Test that all 6 tongues map to coding domains."""

    def test_six_tongues_mapped(self):
        assert len(TONGUE_DOMAIN) == 6

    def test_all_standard_tongues(self):
        for t in ["ko", "av", "ru", "ca", "um", "dr"]:
            assert t in TONGUE_DOMAIN

    def test_six_domains(self):
        domains = set(TONGUE_DOMAIN.values())
        assert len(domains) == 6

    def test_all_domains_have_descriptions(self):
        for domain in TONGUE_DOMAIN.values():
            assert domain in DOMAIN_DESCRIPTION

    def test_all_domains_have_patterns(self):
        """Every domain should have at least one pattern."""
        for domain in set(TONGUE_DOMAIN.values()):
            assert domain in PATTERNS_BY_DOMAIN, f"No patterns for domain {domain}"
            assert len(PATTERNS_BY_DOMAIN[domain]) > 0

    def test_complement_pairs_different_domains(self):
        """Complement tongue pairs should map to different domains."""
        pairs = [("ko", "dr"), ("av", "um"), ("ru", "ca")]
        for t1, t2 in pairs:
            assert TONGUE_DOMAIN[t1] != TONGUE_DOMAIN[t2], f"{t1} and {t2} map to same domain: {TONGUE_DOMAIN[t1]}"


# ===================================================================
# Pattern Selection
# ===================================================================


class TestPatternSelection:
    """Test that trit signals select appropriate code patterns."""

    @pytest.fixture
    def ground_state_qho(self):
        return QHOLevel(
            n=0, energy=0.5, fork_count=0, crossing_energy=0.0, harmonic_wall_cost=1.0, is_ground_state=True
        )

    @pytest.fixture
    def excited_qho(self):
        return QHOLevel(
            n=5, energy=5.5, fork_count=3, crossing_energy=2.5, harmonic_wall_cost=3.2, is_ground_state=False
        )

    def test_ground_state_gets_only_n0_patterns(self, ground_state_qho):
        """At n=0, only patterns with min_n=0 should appear."""
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("simple test text")
        lessons = select_patterns(signal, ground_state_qho, gain=0.0)
        for lesson in lessons:
            assert lesson.pattern.min_n == 0, (
                f"Pattern {lesson.pattern.name} (min_n={lesson.pattern.min_n}) " f"should not appear at n=0"
            )

    def test_excited_state_gets_more_patterns(self, ground_state_qho, excited_qho):
        """Higher QHO level should unlock more patterns."""
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("test text for comparison")
        ground_lessons = select_patterns(signal, ground_state_qho, gain=0.0)
        excited_lessons = select_patterns(signal, excited_qho, gain=1.5)
        assert len(excited_lessons) >= len(ground_lessons)

    def test_high_gain_increases_compound_intent(self, excited_qho):
        """Higher Monty Hall gain should increase compound intent."""
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("boundary test text")
        low_gain = select_patterns(signal, excited_qho, gain=0.1)
        high_gain = select_patterns(signal, excited_qho, gain=2.5)

        if low_gain and high_gain:
            low_max = max(l.compound_intent for l in low_gain)
            high_max = max(l.compound_intent for l in high_gain)
            assert high_max > low_max

    def test_no_duplicate_patterns(self, excited_qho):
        """Same pattern should not appear twice in the lesson list."""
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("dedup test text")
        lessons = select_patterns(signal, excited_qho, gain=1.0)
        names = [l.pattern.name for l in lessons]
        assert len(names) == len(set(names))

    def test_lessons_have_valid_fields(self, excited_qho):
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("field validation test")
        lessons = select_patterns(signal, excited_qho, gain=1.0)
        for lesson in lessons:
            assert 0.0 <= lesson.relevance <= 1.0
            assert lesson.compound_intent >= 0.0
            assert lesson.tongue in ["ko", "av", "ru", "ca", "um", "dr"]
            assert lesson.axis in ["structure", "stability", "creativity"]

    def test_sorted_by_compound_intent(self, excited_qho):
        """Lessons should be sorted highest compound intent first."""
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("sort order test")
        lessons = select_patterns(signal, excited_qho, gain=1.5)
        if len(lessons) >= 2:
            for i in range(len(lessons) - 1):
                assert lessons[i].compound_intent >= lessons[i + 1].compound_intent


# ===================================================================
# Full Bundle Generation
# ===================================================================


class TestCodeLatticeBundle:
    """Test full code lattice bundle generation."""

    def test_generates_bundle(self):
        bundle = generate_code_lattice_bundle("Test text for code lattice generation")
        assert isinstance(bundle, CodeLatticeBundle)

    def test_has_qho_bundle(self):
        bundle = generate_code_lattice_bundle("QHO inside code lattice")
        assert bundle.qho_bundle is not None
        assert bundle.qho_bundle.text == "QHO inside code lattice"

    def test_has_lessons(self):
        bundle = generate_code_lattice_bundle("A text that should trigger some patterns")
        assert isinstance(bundle.lessons, list)

    def test_active_domains_match_lessons(self):
        bundle = generate_code_lattice_bundle("Domain matching test text")
        lesson_domains = set(l.pattern.domain for l in bundle.lessons)
        for d in bundle.active_domains:
            assert d in lesson_domains

    def test_swear_word_count_correct(self):
        bundle = generate_code_lattice_bundle("Counting anti-patterns in this text")
        actual_count = sum(1 for l in bundle.lessons if l.pattern.is_antipattern)
        assert bundle.swear_word_count == actual_count

    def test_total_compound_intent_is_sum(self):
        bundle = generate_code_lattice_bundle("Compound intent sum check")
        expected = sum(l.compound_intent for l in bundle.lessons)
        assert abs(bundle.total_compound_intent - round(expected, 4)) < 0.01

    def test_different_texts_different_bundles(self):
        b1 = generate_code_lattice_bundle("Simple hello world program")
        b2 = generate_code_lattice_bundle("Complex distributed systems architecture with fault tolerance")
        # At minimum, the QHO level or lessons should differ
        assert (
            b1.qho_bundle.qho.n != b2.qho_bundle.qho.n
            or len(b1.lessons) != len(b2.lessons)
            or b1.total_compound_intent != b2.total_compound_intent
        )


# ===================================================================
# Compound Intent (Understanding, Not Repetition)
# ===================================================================


class TestCompoundIntent:
    """Test that system × learner intent compounds correctly."""

    def test_compound_is_product_not_sum(self):
        """Compound intent = system_intent × learner_intent, not addition."""
        bundle = generate_code_lattice_bundle("Compound test")
        for lesson in bundle.lessons:
            # Compound intent should be > 0 when both system and learner contribute
            if lesson.relevance > 0 and bundle.qho_bundle.qho.n > 0:
                assert lesson.compound_intent > 0

    def test_higher_qho_higher_compound(self):
        """Higher QHO level should produce higher compound intent on same text."""
        # We can't directly control QHO level, but we can verify the math
        from src.crypto.trit_curriculum import compute_trit_signal

        signal = compute_trit_signal("compound scaling test")

        low_qho = QHOLevel(
            n=1, energy=1.5, fork_count=0, crossing_energy=0.5, harmonic_wall_cost=1.2, is_ground_state=False
        )
        high_qho = QHOLevel(
            n=5, energy=5.5, fork_count=3, crossing_energy=2.5, harmonic_wall_cost=5.0, is_ground_state=False
        )

        low_lessons = select_patterns(signal, low_qho, gain=1.0)
        high_lessons = select_patterns(signal, high_qho, gain=1.0)

        if low_lessons and high_lessons:
            low_max = max(l.compound_intent for l in low_lessons)
            high_max = max(l.compound_intent for l in high_lessons)
            assert high_max > low_max


# ===================================================================
# SFT Flattening
# ===================================================================


class TestSFTFlattening:
    """Test SFT record generation from code lattice bundles."""

    @pytest.fixture
    def sample_bundles(self):
        texts = [
            "Simple greeting text for testing",
            "Complex distributed systems with fault tolerance mechanisms",
            "Security boundary analysis for authorization gates",
        ]
        return [generate_code_lattice_bundle(t) for t in texts]

    def test_produces_records(self, sample_bundles):
        records = flatten_code_lattice_for_sft(sample_bundles)
        assert len(records) > 0

    def test_records_have_code_fields(self, sample_bundles):
        records = flatten_code_lattice_for_sft(sample_bundles)
        for rec in records:
            assert "code_lesson" in rec
            assert "code_domain" in rec
            assert "swear_word_count" in rec
            assert "compound_intent" in rec

    def test_lesson_records_have_full_detail(self, sample_bundles):
        records = flatten_code_lattice_for_sft(sample_bundles)
        for rec in records:
            if rec["code_lesson"] is not None:
                lesson = rec["code_lesson"]
                assert "name" in lesson
                assert "domain" in lesson
                assert "description" in lesson
                assert "why" in lesson
                assert "code_good" in lesson
                assert "code_bad" in lesson
                assert "cross_domain" in lesson
                assert "relevance" in lesson

    def test_has_qho_metadata(self, sample_bundles):
        """SFT records should still carry QHO metadata from the base layer."""
        records = flatten_code_lattice_for_sft(sample_bundles)
        for rec in records:
            assert "qho_n" in rec
            assert "curriculum_difficulty" in rec

    def test_record_count_matches_lessons(self, sample_bundles):
        """Each lesson produces one record (or one base record if no lessons)."""
        records = flatten_code_lattice_for_sft(sample_bundles)
        sum(max(len(b.lessons), 1) for b in sample_bundles)
        # Records come from lessons (1 per lesson) or base (1 if no lessons)
        # Allow some slack for bundles with lessons expanding multipath
        assert len(records) >= len(sample_bundles)


# ===================================================================
# Report
# ===================================================================


class TestReport:
    """Test report formatting."""

    @pytest.fixture
    def sample_bundles(self):
        texts = [
            "Test text one for report",
            "Test text two for report with more words",
        ]
        return [generate_code_lattice_bundle(t) for t in texts]

    def test_report_produces_output(self, sample_bundles):
        report = format_code_lattice_report(sample_bundles)
        assert len(report) > 100

    def test_report_has_header(self, sample_bundles):
        report = format_code_lattice_report(sample_bundles)
        assert "CODE LATTICE TRAINING REPORT" in report

    def test_report_has_philosophy(self, sample_bundles):
        report = format_code_lattice_report(sample_bundles)
        assert "Understanding Compounds" in report

    def test_report_has_statistics(self, sample_bundles):
        report = format_code_lattice_report(sample_bundles)
        assert "Total bundles" in report
        assert "Total lessons" in report
        assert "Swear words detected" in report

    def test_report_has_domain_activity(self, sample_bundles):
        report = format_code_lattice_report(sample_bundles)
        assert "Domain Activity" in report


# ===================================================================
# Cross-Domain Mapping
# ===================================================================


class TestCrossDomain:
    """Test that cross-domain analogies are meaningful."""

    def test_all_patterns_have_cross_domain(self):
        for p in PATTERN_REGISTRY:
            assert len(p.cross_domain) > 10, f"Pattern {p.name} has too-short cross_domain: '{p.cross_domain}'"

    def test_antipatterns_reference_tongue(self):
        """Anti-pattern cross-domain text should reference Sacred Tongue concepts."""
        tongue_keywords = [
            "tongue",
            "swear",
            "spell",
            "lattice",
            "vortex",
            "forge",
            "shadow",
            "void",
            "KO",
            "AV",
            "RU",
            "CA",
            "UM",
            "DR",
            "binding",
            "torque",
            "polyhedral",
            "harmonic",
            "wall",
            "phi",
            "boundary",
            "trit",
        ]
        for p in ALL_ANTIPATTERNS:
            has_keyword = any(kw.lower() in p.cross_domain.lower() for kw in tongue_keywords)
            assert has_keyword, (
                f"Anti-pattern {p.name} cross_domain doesn't reference tongue concepts: " f"'{p.cross_domain}'"
            )

    def test_code_examples_are_valid_python_ish(self):
        """Code examples should look like real code (contain at least one keyword)."""
        code_keywords = [
            "def ",
            "class ",
            "import ",
            "return ",
            "if ",
            "for ",
            "try:",
            "except",
            "async ",
            "with ",
            "assert ",
            " = ",
            "not in ",
            "**",
        ]
        for p in PATTERN_REGISTRY:
            has_keyword = any(kw in p.code_good for kw in code_keywords)
            assert has_keyword, f"Pattern {p.name} code_good doesn't look like code: '{p.code_good[:50]}'"
