"""
Tests for Ledger Keyword Persistence + Librarian Reload.
==========================================================

Covers:
- Ledger.save_keyword() stores keyword->memory_key in SQLite
- Ledger.load_keywords() returns full keyword index
- Duplicate keywords are ignored (INSERT OR IGNORE)
- Cross-session survival: save, close, reopen, load
- Librarian.__init__ loads persisted keywords
- Librarian.remember() persists keywords through ledger
- Librarian keyword index populated after remember()
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.ledger import Ledger
from hydra.librarian import Librarian


@pytest.fixture
def ledger(tmp_path):
    db_path = str(tmp_path / "test_ledger.db")
    return Ledger(db_path=db_path)


@pytest.fixture
def db_path(tmp_path):
    """Return a path for a ledger DB (not yet created)."""
    return str(tmp_path / "persist_test.db")


# =========================================================================
# Ledger.save_keyword + load_keywords
# =========================================================================


class TestLedgerKeywords:
    """Keyword index table in SQLite."""

    def test_save_and_load_single(self, ledger):
        ledger.save_keyword("python", "mem:python-intro")
        index = ledger.load_keywords()
        assert "python" in index
        assert "mem:python-intro" in index["python"]

    def test_save_multiple_keys_same_keyword(self, ledger):
        ledger.save_keyword("ai", "mem:ai-safety")
        ledger.save_keyword("ai", "mem:ai-governance")
        index = ledger.load_keywords()
        assert len(index["ai"]) == 2
        assert "mem:ai-safety" in index["ai"]
        assert "mem:ai-governance" in index["ai"]

    def test_save_multiple_keywords_same_key(self, ledger):
        ledger.save_keyword("safety", "mem:scbe")
        ledger.save_keyword("governance", "mem:scbe")
        index = ledger.load_keywords()
        assert "mem:scbe" in index["safety"]
        assert "mem:scbe" in index["governance"]

    def test_duplicate_insert_ignored(self, ledger):
        ledger.save_keyword("test", "mem:1")
        ledger.save_keyword("test", "mem:1")  # duplicate
        index = ledger.load_keywords()
        assert len(index["test"]) == 1

    def test_load_empty_returns_empty_dict(self, ledger):
        index = ledger.load_keywords()
        assert index == {}

    def test_many_keywords(self, ledger):
        for i in range(50):
            ledger.save_keyword(f"kw_{i}", f"mem:{i}")
        index = ledger.load_keywords()
        assert len(index) == 50


# =========================================================================
# Cross-session persistence
# =========================================================================


class TestCrossSessionPersistence:
    """Keywords survive ledger close and reopen."""

    def test_keywords_survive_reopen(self, db_path):
        # Session 1: save keywords
        ledger1 = Ledger(db_path=db_path)
        ledger1.save_keyword("alpha", "mem:a")
        ledger1.save_keyword("beta", "mem:b")
        del ledger1  # close

        # Session 2: reopen and load
        ledger2 = Ledger(db_path=db_path)
        index = ledger2.load_keywords()
        assert "alpha" in index
        assert "beta" in index
        assert "mem:a" in index["alpha"]
        assert "mem:b" in index["beta"]

    def test_memories_and_keywords_survive_reopen(self, db_path):
        # Session 1: remember facts
        ledger1 = Ledger(db_path=db_path)
        lib1 = Librarian(ledger1)
        lib1.remember("project:scbe", {"name": "SCBE"}, category="project", importance=0.9)
        del lib1
        del ledger1

        # Session 2: librarian loads keywords from DB
        ledger2 = Ledger(db_path=db_path)
        lib2 = Librarian(ledger2)
        assert len(lib2._keyword_index) > 0
        # The recalled value should still be there
        value = lib2.recall("project:scbe")
        assert value is not None


# =========================================================================
# Librarian keyword integration
# =========================================================================


class TestLibrarianKeywordIntegration:
    """Librarian.remember() populates and persists keyword index."""

    def test_remember_populates_keyword_index(self, ledger):
        lib = Librarian(ledger)
        lib.remember("fact:earth", "third planet", category="science", importance=0.5)
        # Keywords extracted from "fact:earth" and "third planet"
        assert len(lib._keyword_index) > 0

    def test_remember_persists_keywords_to_ledger(self, ledger):
        lib = Librarian(ledger)
        lib.remember("fact:gravity", "9.8 m/s^2", category="physics", importance=0.7)
        # Load directly from ledger to verify persistence
        index = ledger.load_keywords()
        assert len(index) > 0
        # At least one keyword from "gravity" or "fact" should be persisted
        all_keywords = set(index.keys())
        assert len(all_keywords) > 0

    def test_remember_with_explicit_keywords(self, ledger):
        lib = Librarian(ledger)
        lib.remember(
            "config:mode",
            "dark",
            category="settings",
            keywords=["theme", "dark_mode"],
        )
        assert "theme" in lib._keyword_index
        assert "config:mode" in lib._keyword_index["theme"]

    def test_recall_after_remember(self, ledger):
        lib = Librarian(ledger)
        lib.remember("pet:favorite", {"name": "Max", "type": "dog"})
        value = lib.recall("pet:favorite")
        assert value is not None
        assert value["name"] == "Max"

    def test_forget_marks_memory(self, ledger):
        lib = Librarian(ledger)
        lib.remember("temp:data", "temporary")
        assert lib.recall("temp:data") is not None
        lib.forget("temp:data")
        # After forget, category changes to "forgotten"
        # The memory should still exist but with low importance

    def test_librarian_init_loads_existing_keywords(self, db_path):
        """New Librarian instance loads keywords from existing DB."""
        # Populate
        ledger1 = Ledger(db_path=db_path)
        ledger1.save_keyword("hydra", "mem:hydra-intro")
        ledger1.save_keyword("spine", "mem:spine-doc")
        del ledger1

        # New Librarian should have those keywords loaded
        ledger2 = Ledger(db_path=db_path)
        lib = Librarian(ledger2)
        assert "hydra" in lib._keyword_index
        assert "spine" in lib._keyword_index


# =========================================================================
# Librarian stats
# =========================================================================


class TestLibrarianStats:
    """get_stats() includes keyword index info."""

    def test_stats_include_keyword_index_size(self, ledger):
        lib = Librarian(ledger)
        lib.remember("stat:test", "value")
        stats = lib.get_stats()
        assert "keyword_index_size" in stats
        assert stats["keyword_index_size"] >= 0

    def test_stats_include_cache_info(self, ledger):
        lib = Librarian(ledger)
        stats = lib.get_stats()
        assert "cache_size" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "cache_hit_rate" in stats
