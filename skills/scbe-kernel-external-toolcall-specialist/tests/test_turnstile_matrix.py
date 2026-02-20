from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "references" / "turnstile-matrix.yaml"


def test_turnstile_matrix_has_required_domains() -> None:
    matrix = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
    domains = matrix.get("domains", {})
    for name in ["browser", "vehicle", "fleet", "antivirus", "arxiv", "patent"]:
        assert name in domains, f"missing domain {name}"


def test_vehicle_excludes_hold() -> None:
    matrix = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
    actions = set(matrix["domains"]["vehicle"]["allowed_actions"])
    assert "HOLD" not in actions
    assert {"ALLOW", "PIVOT"}.issubset(actions)


def test_arxiv_requires_hold_path() -> None:
    matrix = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
    actions = set(matrix["domains"]["arxiv"]["allowed_actions"])
    assert "HOLD" in actions
