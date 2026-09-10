from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"


def test_homepage_capability_path_is_visible() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert "Capability" in html
    assert "host verifies authority" in html or "Host verifies identity and authority" in html
    assert "Receipt" in html
    assert "The model proposes. The system decides what may happen" in html


def test_homepage_boundary_rejects_ambient_access() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert "Isolation" in html
    assert "no ambient access" in html or "without ambient access" in html
    assert "failed check" in html
    assert "re-plan" in html


def test_homepage_traces_governed_action_path() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert 'data-route-map' in html
    assert 'data-boundary-canvas' in html
    assert "Proposal" in html
    assert "Capability check" in html
    assert "Isolated action" in html


def test_homepage_points_at_runtime_and_evidence() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert 'href="agents.html"' in html
    assert 'href="research/evidence-ledger.html"' in html
    assert 'href="proof-workbench.html"' in html
    assert "no certification claim" in html
