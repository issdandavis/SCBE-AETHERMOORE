"""Tests for HYDRA ledger readonly-fallback logic."""

import os
import tempfile
from hydra.ledger import Ledger


def test_resolve_db_path_uses_writable_requested_path():
    """When the requested path is writable, use it directly."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        resolved = Ledger._resolve_db_path(db_path)
        assert resolved == os.path.abspath(db_path)


def test_resolve_db_path_falls_back_when_unwritable():
    """When the requested directory is not writable, fall back to repo-local."""
    # Use a path guaranteed unwritable on both Unix (/proc) and Windows (NUL device prefix)
    if os.name == "nt":
        bad_path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "config", "fake_hydra_unwritable", "ledger.db")
    else:
        bad_path = "/proc/fake_hydra_unwritable/sub/ledger.db"
    resolved = Ledger._resolve_db_path(bad_path)
    assert "artifacts" in resolved and "runtime" in resolved


def test_can_write_path_returns_true_for_temp():
    """A temp directory should be writable."""
    with tempfile.TemporaryDirectory() as tmp:
        assert Ledger._can_write_path(tmp) is True


def test_can_write_path_returns_false_for_nonexistent():
    """A non-creatable path should return False."""
    if os.name == "nt":
        bad_path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "config", "fake_hydra_test")
    else:
        bad_path = "/proc/fake_hydra_test"
    assert Ledger._can_write_path(bad_path) is False


def test_repo_fallback_db_is_under_artifacts():
    """The fallback path should be under artifacts/runtime/hydra/."""
    path = Ledger._repo_fallback_db()
    assert path.endswith("ledger.db")
    assert "artifacts" in path
