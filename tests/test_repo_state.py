"""The hygiene monitor must be able to report RED, not just green.

A monitor is only worth its runtime if it fires on the thing it watches. This repo has a
standing example of the alternative: `install.js` printed "[hooks] installed pre-commit"
every run while `core.hooksPath` sent git somewhere else entirely, so a green message meant
nothing at all.

So these tests do not check that repo_state reports clean today (it does, because the
defects were fixed on 2026-07-27). They plant each defect and assert it is DETECTED --
using the real shapes that were live in this repo:

  pyproject 4.3.0 / __init__ 3.3.0        version incoherence
  repo 4.3.0 / PyPI 4.2.1                 publish drift
  core.hooksPath -> a subpackage husky    unreachable pre-commit hook
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("repo_state", ROOT / "scripts" / "system" / "repo_state.py")
rs = importlib.util.module_from_spec(_spec)
sys.modules["repo_state"] = rs
_spec.loader.exec_module(rs)


def _findings(state) -> set[str]:
    return {f["area"] for f in state["findings"]}


def test_detects_version_incoherence(monkeypatch):
    """pyproject said 4.3.0 while __init__ said 3.3.0 -- and 3.3.0 was a REAL past release."""
    monkeypatch.setattr(
        rs,
        "collect_versions",
        lambda: {
            "declared_pyproject": "4.3.0",
            "declared_dunder": "3.3.0",
            "declared_package_json": "4.3.0",
            "published_pypi": "4.3.0",
            "published_npm": "4.3.0",
            "internally_coherent": False,
            "publish_drift": [],
            "checked_registries": True,
        },
    )
    assert "versions" in _findings(rs.build())


def test_detects_publish_drift(monkeypatch):
    """The bug that broke pip install for weeks: repo ahead of what the registry serves."""
    monkeypatch.setattr(
        rs,
        "collect_versions",
        lambda: {
            "declared_pyproject": "4.3.0",
            "declared_dunder": "4.3.0",
            "declared_package_json": "4.3.0",
            "published_pypi": "4.2.1",
            "published_npm": "4.2.1",
            "internally_coherent": True,
            "publish_drift": ["pypi 4.2.1 != declared 4.3.0"],
            "checked_registries": True,
        },
    )
    state = rs.build()
    assert "publish" in _findings(state)
    assert any(f["severity"] == "high" for f in state["findings"])


def test_detects_unreachable_pre_commit_hook(monkeypatch):
    """core.hooksPath elsewhere = the credential scanner silently never runs."""
    monkeypatch.setattr(
        rs,
        "collect_hooks",
        lambda: {
            "core_hooks_path": "packages/agent-bus/.husky",
            "repo_hook_present": True,
            "effective_hook_present": True,
            "repo_hook_reachable": False,
        },
    )
    state = rs.build()
    assert "hooks" in _findings(state)
    assert any(f["severity"] == "high" and f["area"] == "hooks" for f in state["findings"])


def test_detects_missing_concurrency_and_nightly_bloat(monkeypatch):
    monkeypatch.setattr(
        rs,
        "collect_workflows",
        lambda: {
            "total": 87,
            "nightly": ["a", "b", "c", "d", "e", "f"],
            "nightly_count": 6,
            "weekly_count": 10,
            "branch_push_triggered": 17,
            "missing_concurrency": 11,
        },
    )
    areas = _findings(rs.build())
    assert "ci" in areas
    details = " ".join(f["detail"] for f in rs.build()["findings"])
    assert "concurrency" in details and "nightly" in details


def test_offline_is_unknown_not_in_sync(monkeypatch):
    """Refusing to check must never be recorded as having checked and passed."""
    monkeypatch.setattr(rs, "_pypi_version", lambda pkg: None)
    monkeypatch.setattr(rs, "_npm_version", lambda pkg: None)
    v = rs.collect_versions()
    assert v["checked_registries"] is False
    assert v["publish_drift"] == [], "cannot claim drift without a registry answer"


def test_clean_flag_tracks_findings():
    state = rs.build()
    assert state["clean"] == (not state["findings"])


def test_state_is_json_serializable_and_versioned():
    """Clay ingests this; a schema bump has to be visible in the row itself."""
    import json

    state = rs.build()
    json.dumps(state)  # raises if anything non-serializable slipped in
    assert state["schema_version"] >= 1
    assert state["generated_at_utc"].endswith("+00:00"), "timestamps must be UTC and explicit"


def test_no_overall_score_is_emitted():
    """Deliberate: a single health score invites tuning the score instead of the repo."""
    state = rs.build()
    assert not any(k in state for k in ("score", "health_score", "grade"))
