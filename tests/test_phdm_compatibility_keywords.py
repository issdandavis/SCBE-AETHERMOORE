"""Caller-controlled vocabulary must not bypass PHDM deviation calculation."""

from unittest.mock import Mock

import pytest

from src.harmonic.phdm_module import PHDM


@pytest.mark.parametrize(
    "word",
    [
        "scan",
        "verify",
        "extract",
        "navigate",
        "enter",
        "validate",
        "secure",
        "transfer",
        "mission",
        "dashboard",
    ],
)
def test_control_words_still_call_detector(word):
    phdm = PHDM()
    phdm._detector = Mock()
    phdm._detector.detect_manifold_deviation.return_value = 0.75
    message = f"unrelated opaque payload {word}"
    assert phdm.check_hamiltonian_path(message, "KO") == 0.75
    phdm._detector.detect_manifold_deviation.assert_called_once_with(
        sum(c.isascii() and c.isalpha() for c in message), len(message) + 2
    )


def test_real_detector_no_longer_erases_deviation_on_verify():
    phdm = PHDM()
    assert phdm.check_hamiltonian_path("unrelated opaque payload", "KO") > 0
    assert phdm.check_hamiltonian_path("unrelated opaque payload verify", "KO") > 0
