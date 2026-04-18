"""Tests for HYDRA ledger readonly-fallback logic."""

import os
import sys
import tempfile
from unittest.mock import patch
import pytest
from hydra.ledger import Ledger


def test_resolve_db_path_uses_writable_requested_path():
    """When the requested path is writable, use it directly."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        resolved = Ledger._resolve_db_path(db_path)
        # _resolve_db_path uses os.path.realpath; so must the assertion.
        assert resolved == os.path.realpath(db_path)


def test_resolve_db_path_falls_back_when_unwritable():
    """When the requested directory is not writable, fall back to repo-local."""
    # Mock _can_write_path to return False regardless of OS / filesystem.
    # The /proc trick only works on Linux; on Windows /proc maps to a writable C:\ path.
    with patch.object(Ledger, "_can_write_path", return_value=False):
        resolved = Ledger._resolve_db_path("/fake/unwritable/sub/ledger.db")
    assert "artifacts" in resolved and "runtime" in resolved


def test_can_write_path_returns_true_for_temp():
    """A temp directory should be writable."""
    with tempfile.TemporaryDirectory() as tmp:
        assert Ledger._can_write_path(tmp) is True


@pytest.mark.skipif(sys.platform == "win32", reason="/proc does not exist on Windows")
def test_can_write_path_returns_false_for_nonexistent_linux():
    """A non-creatable path should return False (Linux/macOS only)."""
    assert Ledger._can_write_path("/proc/fake_hydra_test") is False


def test_repo_fallback_db_is_under_artifacts():
    """The fallback path should be under artifacts/runtime/hydra/."""
    path = Ledger._repo_fallback_db()
    assert path.endswith("ledger.db")
    assert "artifacts" in path
