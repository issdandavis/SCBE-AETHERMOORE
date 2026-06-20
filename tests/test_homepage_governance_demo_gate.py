from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"


def test_homepage_governance_demo_has_critical_veto_path() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert "CRITICAL_THREAT_PATTERNS" in html
    assert "matchedCriticalThreats.length > 0" in html
    assert "Trust cannot override critical safety" in html


def test_homepage_governance_demo_catches_payment_theft_prompt() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert "credit\\s*card" in html
    assert "credential/payment theft" in html
    assert "risk = Math.max(risk, 0.96)" in html


def test_homepage_governance_demo_uses_real_gate_before_browser_fallback() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert "/v1/governed/chat/completions" in html
    assert "runRealGovernedGate" in html
    assert "REAL_GATE_API" in html
    assert "BROWSER_FALLBACK" in html
    assert "Customer token vault" in html


def test_homepage_governance_demo_has_executable_use_case_samples() -> None:
    html = INDEX.read_text(encoding="utf-8")

    assert "GOVERNANCE_SAMPLES" in html
    assert "setGovernanceSample" in html
    assert "Safe paid run" in html
    assert "Payment theft" in html
    assert "gov-source-label" in html
