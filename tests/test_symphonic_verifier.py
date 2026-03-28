import pytest

try:
    from agents.browser.symphonic_verifier import SymphonicVerifier
except (ImportError, Exception):
    pytest.skip(
        "dependency not available (fastapi required by agents.browser)",
        allow_module_level=True,
    )


def test_symphonic_verifier_returns_structured_result():
    verifier = SymphonicVerifier(min_confidence=0.5)
    result = verifier.verify(action="click", target="#submit")

    assert isinstance(result.passed, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert len(result.expected_harmonics) == 3
    assert len(result.observed_peaks) > 0


def test_symphonic_verifier_is_deterministic_for_same_input():
    verifier = SymphonicVerifier(min_confidence=0.5)

    r1 = verifier.verify(action="navigate", target="https://example.com")
    r2 = verifier.verify(action="navigate", target="https://example.com")

    assert r1.confidence == r2.confidence
    assert r1.observed_peaks == r2.observed_peaks
