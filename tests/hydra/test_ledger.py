"""
Focused tests for HYDRA ledger path resolution.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.ledger import Ledger


def test_ledger_uses_hydra_ledger_db_env(monkeypatch, tmp_path):
    db_path = tmp_path / "custom" / "ledger.db"
    monkeypatch.setenv("HYDRA_LEDGER_DB", str(db_path))
    monkeypatch.delenv("HYDRA_HOME", raising=False)

    ledger = Ledger()

    assert ledger.db_path == str(db_path.resolve())
    assert db_path.exists()


def test_ledger_uses_hydra_home_env(monkeypatch, tmp_path):
    hydra_home = tmp_path / "hydra-home"
    monkeypatch.delenv("HYDRA_LEDGER_DB", raising=False)
    monkeypatch.setenv("HYDRA_HOME", str(hydra_home))

    ledger = Ledger()

    assert ledger.db_path == str((hydra_home / "ledger.db").resolve())
    assert (hydra_home / "ledger.db").exists()
