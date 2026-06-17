"""Tests for cross-language Rosetta + cross-compile game."""

from python.scbe.cross_lang import lookup, concepts, grade, challenges, LANGUAGES


class TestLookup:
    def test_row_has_all_languages(self):
        row = lookup("print")
        assert set(row) >= set(LANGUAGES)
        assert row["rust"].startswith("println!")

    def test_unknown_concept(self):
        assert lookup("nope") is None

    def test_concepts_nonempty(self):
        assert len(concepts()) >= 8


class TestGrade:
    def test_correct_lenient(self):
        # trailing semicolon / whitespace ignored
        r = grade("print", "rust", 'println!("hi")')
        assert r["ok"] and r["correct"]

    def test_wrong(self):
        r = grade("print", "rust", 'console.log("hi")')
        assert r["ok"] and not r["correct"]

    def test_errors(self):
        assert not grade("nope", "rust", "x")["ok"]
        assert not grade("print", "cobol", "x")["ok"]


class TestGame:
    def test_challenges_deterministic(self):
        a = challenges(rounds=5, seed=42)
        b = challenges(rounds=5, seed=42)
        assert a == b and len(a) == 5

    def test_challenge_has_no_answer_leak(self):
        for c in challenges(rounds=5, seed=3):
            assert "answer" not in c  # AI must produce it
            assert c["from_lang"] != c["to_lang"]
            assert "from_code" in c and "to_lang" in c
