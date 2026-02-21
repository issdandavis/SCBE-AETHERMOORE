"""
Canonical Spiralverse linguistic registry tests.

These tests enforce alignment between:
- docs/specs/spiralverse_canonical_registry.v1.json
- six-tongues-cli.py runtime constants
"""

from __future__ import annotations

import json
import math
import os
from importlib.machinery import SourceFileLoader


_ROOT = os.path.join(os.path.dirname(__file__), "..")
_CLI_PATH = os.path.join(_ROOT, "six-tongues-cli.py")
_REGISTRY_PATH = os.path.join(_ROOT, "docs", "specs", "spiralverse_canonical_registry.v1.json")

_loader = SourceFileLoader("six_tongues_cli", _CLI_PATH)
cli = _loader.load_module()


def _load_registry() -> dict:
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_registry_has_exactly_six_base_tongues():
    registry = _load_registry()
    base = registry["base_tongues"]
    codes = [row["code"] for row in base]
    assert codes == ["KO", "AV", "RU", "CA", "UM", "DR"]
    assert cli.TONGUES == codes


def test_weights_match_runtime_constants():
    registry = _load_registry()
    runtime = cli.CrossTokenizer.WEIGHT
    for row in registry["base_tongues"]:
        code = row["code"]
        expected = float(row["weight_phi"])
        assert code in runtime
        assert math.isclose(runtime[code], expected, rel_tol=0.0, abs_tol=1e-12)


def test_phases_match_runtime_constants():
    registry = _load_registry()
    runtime = cli.CrossTokenizer.PHASE
    for row in registry["base_tongues"]:
        code = row["code"]
        expected = float(row["phase_radians"])
        assert code in runtime
        assert math.isclose(runtime[code], expected, rel_tol=0.0, abs_tol=1e-12)


def test_kor_aelin_counts_are_canonical():
    registry = _load_registry()
    runes = registry["kor_aelin"]["runic_letters"]
    particles = registry["kor_aelin"]["particle_grammar_core"]

    assert len(runes) == 24
    assert len(set(runes)) == 24
    assert "Kor" in runes

    assert len(particles) == 14
    assert len(set(particles)) == 14
    assert "kor" in particles


def test_sub_traditions_are_not_base_tongues():
    registry = _load_registry()
    base_codes = {row["code"] for row in registry["base_tongues"]}
    names = {row["name"] for row in registry["sub_traditions"]}
    for base in base_codes:
        assert base not in names
