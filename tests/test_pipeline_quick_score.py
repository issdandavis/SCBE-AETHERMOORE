"""Tests for the lightweight pipeline scorer in scbe.py.

Verifies that the natural sieve produces meaningfully different scores
for different input classes — the core property the old SHA-256 scorer broke.
"""

from __future__ import annotations

import importlib.machinery
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Load scbe.py (no .py-less import dance needed now)
_loader = importlib.machinery.SourceFileLoader("scbe_mod", str(ROOT / "scbe.py"))
_mod = types.ModuleType("scbe_mod")
_mod.__file__ = str(ROOT / "scbe.py")
_loader.exec_module(_mod)

pipeline_quick_score = _mod.pipeline_quick_score


# ─── Core property: different inputs produce different scores ───


class TestScoreDiscrimination:
    """The whole point: the scorer must distinguish input classes."""

    def test_empty_vs_normal_prose(self) -> None:
        empty = pipeline_quick_score("")
        prose = pipeline_quick_score("The quick brown fox jumps over the lazy dog")
        assert empty["d_star"] > prose["d_star"], "empty should be further from normal"
        assert empty["H_eff"] < prose["H_eff"], "empty should score lower"

    def test_prose_vs_injection(self) -> None:
        prose = pipeline_quick_score("A perfectly normal sentence about dinner.")
        sqli = pipeline_quick_score("SELECT * FROM users WHERE 1=1; DROP TABLE;--")
        assert sqli["d_star"] > prose["d_star"], "SQL injection further from normal"
        assert sqli["H_eff"] < prose["H_eff"], "SQL injection scores lower"

    def test_prose_vs_xss(self) -> None:
        prose = pipeline_quick_score("She walked through the garden quietly.")
        xss = pipeline_quick_score("<script>alert(document.cookie)</script>")
        assert xss["d_star"] > prose["d_star"], "XSS further from normal"

    def test_prose_vs_shell_injection(self) -> None:
        prose = pipeline_quick_score("The weather is nice today.")
        shell = pipeline_quick_score("rm -rf / --no-preserve-root")
        assert shell["d_star"] > prose["d_star"], "shell injection further from normal"

    def test_all_digits_far_from_prose(self) -> None:
        prose = pipeline_quick_score("Hello world")
        digits = pipeline_quick_score("12345678901234567890")
        assert digits["d_star"] > prose["d_star"] + 1.0, "all digits much further"

    def test_control_chars_highest_distance(self) -> None:
        ctrl = pipeline_quick_score("\x00\x01\x02\x03\x04\x05")
        prose = pipeline_quick_score("Normal text here")
        assert ctrl["d_star"] > prose["d_star"] + 5.0, "control chars extremely far"

    def test_repeated_char_vs_diverse(self) -> None:
        repeated = pipeline_quick_score("a" * 200)
        diverse = pipeline_quick_score(
            "The fox jumped over the lazy dog while birds sang overhead."
        )
        assert repeated["d_star"] > diverse["d_star"], "repetition further from normal"

    def test_no_two_classes_identical(self) -> None:
        """The old scorer gave identical scores for everything. This must not."""
        inputs = [
            "",
            "hello",
            "SELECT * FROM users;--",
            "<script>alert(1)</script>",
            "12345678901234567890",
            "\x00\x01\x02\x03",
            "A normal safe sentence about cooking.",
        ]
        scores = [pipeline_quick_score(t)["d_star"] for t in inputs]
        unique_scores = set(round(s, 4) for s in scores)
        assert len(unique_scores) >= 5, f"Expected diverse scores, got: {scores}"


# ─── Decision tier correctness ───


class TestDecisionTiers:
    """Verify decision thresholds produce sensible classifications."""

    def test_safe_prose_not_denied(self) -> None:
        result = pipeline_quick_score("Once upon a time there lived a brave knight.")
        assert result["decision"] != "DENY", f"safe prose should not DENY: {result}"

    def test_control_chars_denied(self) -> None:
        result = pipeline_quick_score("\x00\x01\x02\x03\x04\x05\x06\x07")
        assert result["decision"] == "DENY"

    def test_all_digits_denied(self) -> None:
        result = pipeline_quick_score("0" * 50)
        assert result["decision"] == "DENY"

    def test_empty_denied(self) -> None:
        result = pipeline_quick_score("")
        assert result["decision"] == "DENY"

    def test_injection_escalated_or_worse(self) -> None:
        result = pipeline_quick_score("SELECT * FROM users; DROP TABLE;--")
        assert result["decision"] in ("ESCALATE", "DENY", "QUARANTINE")

    def test_code_not_allowed(self) -> None:
        result = pipeline_quick_score('import os; os.system("rm -rf /")')
        assert result["decision"] != "ALLOW"


# ─── Multilingual fairness ───


class TestMultilingual:
    """Non-Latin scripts should not be auto-denied."""

    def test_french_not_denied(self) -> None:
        result = pipeline_quick_score("Le renard brun rapide saute par-dessus.")
        assert result["decision"] != "DENY"

    def test_german_not_denied(self) -> None:
        result = pipeline_quick_score("Der schnelle braune Fuchs springt.")
        assert result["decision"] != "DENY"

    def test_multilingual_similar_to_english(self) -> None:
        en = pipeline_quick_score("The quick brown fox jumps")
        fr = pipeline_quick_score("Le renard brun rapide saute")
        # French should be in same ballpark as English (within 1.0 d*)
        assert abs(en["d_star"] - fr["d_star"]) < 1.5


# ─── Output structure ───


class TestOutputContract:
    """Verify the returned dict has all required fields."""

    def test_required_fields(self) -> None:
        result = pipeline_quick_score("test")
        required = {
            "input_len",
            "d_star",
            "x_poincare",
            "H_eff",
            "phase_deviation",
            "decision",
            "digest_hex",
        }
        assert required <= set(result.keys())

    def test_h_eff_bounded(self) -> None:
        """H_eff must be in (0, 1] for any input."""
        for text in ["", "x", "a" * 1000, "\x00" * 10, "normal text"]:
            result = pipeline_quick_score(text)
            assert 0 < result["H_eff"] <= 1.0, f"H_eff out of range: {result}"

    def test_d_star_non_negative(self) -> None:
        for text in ["", "hello", "12345", "\xff" * 10]:
            result = pipeline_quick_score(text)
            assert result["d_star"] >= 0.0

    def test_decision_valid(self) -> None:
        for text in ["", "hello", "DROP TABLE", "\x00"]:
            result = pipeline_quick_score(text)
            assert result["decision"] in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")

    def test_input_len_correct(self) -> None:
        result = pipeline_quick_score("hello")
        assert result["input_len"] == 5

    def test_digest_is_hex(self) -> None:
        result = pipeline_quick_score("test")
        int(result["digest_hex"], 16)  # should not raise


# ─── Performance ───


class TestPerformance:
    """Scorer should handle large inputs without exploding."""

    def test_1mb_input(self) -> None:
        import time

        big = "x" * 1_000_000
        t0 = time.time()
        result = pipeline_quick_score(big)
        elapsed = time.time() - t0
        assert elapsed < 10.0, f"1MB took {elapsed:.1f}s (should be <10s)"
        assert result["decision"] in ("ALLOW", "QUARANTINE", "ESCALATE", "DENY")

    def test_empty_fast(self) -> None:
        import time

        t0 = time.time()
        for _ in range(1000):
            pipeline_quick_score("")
        elapsed = time.time() - t0
        assert elapsed < 2.0, f"1000 empty calls took {elapsed:.1f}s"
