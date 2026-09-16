"""The PyPI guard must reject test payloads without rejecting source layouts."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = runpy.run_path(str(ROOT / "scripts" / "pypi_dist_guard.py"))


@pytest.mark.parametrize(
    "member",
    [
        "python/scbe/test_opcode_charge.py",
        "symphonic_cipher/scbe_aethermoore/layer_tests.py",
        "symphonic_cipher/scbe_aethermoore/axiom_grouped/tests/__init__.py",
        "scbe-4.3.1/src/symphonic_cipher/scbe_aethermoore/patent_validation_tests.py",
    ],
)
def test_test_payload_is_a_release_error(member):
    archive = GUARD["DistFile"](Path("fixture.whl"), [member])
    assert GUARD["scan_patterns"](archive, GUARD["FAIL_PATTERNS"])


def test_runtime_source_layout_is_allowed():
    archive = GUARD["DistFile"](Path("fixture.tar.gz"), ["scbe-4.3.1/src/crypto/geo_seal.py"])
    assert not GUARD["scan_patterns"](archive, GUARD["FAIL_PATTERNS"])
