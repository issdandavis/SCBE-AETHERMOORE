"""Unit tests for analyze_rho_log decision hint (no JSONL I/O)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_analyze():
    path = REPO / "scripts" / "analyze_rho_log.py"
    spec = importlib.util.spec_from_file_location("analyze_rho_log", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def az():
    return _load_analyze()


def test_hint_insufficient_records(az):
    h = az._decision_hint({"total_records": 2, "per_axis": {}})
    assert h["verdict"] == "INSUFFICIENT_RECORDS"


def test_hint_insufficient_warm_axes(az):
    summary = {
        "total_records": 50,
        "per_axis": {
            "KO": {"rho_latest": 0.5, "samples": 50, "warm_samples": 50},
            "AV": {"rho_latest": 0.4, "samples": 50, "warm_samples": 50},
        },
    }
    h = az._decision_hint(summary)
    assert h["verdict"] == "INSUFFICIENT_WARM_AXES"


def test_hint_low_signal(az):
    summary = {
        "total_records": 40,
        "per_axis": {
            "KO": {"rho_latest": 0.02, "samples": 40, "warm_samples": 40},
            "AV": {"rho_latest": -0.01, "samples": 40, "warm_samples": 40},
            "RU": {"rho_latest": 0.03, "samples": 40, "warm_samples": 40},
        },
    }
    h = az._decision_hint(summary)
    assert h["verdict"] == "LOW_SIGNAL"
    assert float(h["rho_span"]) < 0.05


def test_hint_structured(az):
    summary = {
        "total_records": 40,
        "per_axis": {
            "KO": {"rho_latest": 0.55, "samples": 40, "warm_samples": 40},
            "AV": {"rho_latest": 0.1, "samples": 40, "warm_samples": 40},
            "RU": {"rho_latest": -0.45, "samples": 40, "warm_samples": 40},
            "CA": {"rho_latest": 0.0, "samples": 40, "warm_samples": 40},
        },
    }
    h = az._decision_hint(summary)
    assert h["verdict"] == "STRUCTURED"
    assert float(h["rho_span"]) >= 0.12
