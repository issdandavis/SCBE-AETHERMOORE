"""Regression guard for the PQC receipt proof (patent Claim 12 evidence).

Runs scripts/security/pqc_receipt_proof.py and requires a clean exit. Skipped
where real liboqs is unavailable (the proof asserts tier-1, so it can only pass
with native ML-KEM/ML-DSA present).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _liboqs_tier1() -> bool:
    try:
        sys.path.insert(0, str(_REPO))
        from src.crypto.pqc_liboqs import get_pqc_proof_tier

        return get_pqc_proof_tier() == 1
    except Exception:
        return False


@pytest.mark.security
@pytest.mark.skipif(not _liboqs_tier1(), reason="native liboqs (tier 1) not available")
def test_pqc_receipt_proof_passes():
    proof = _REPO / "scripts" / "security" / "pqc_receipt_proof.py"
    env = os.environ.copy()  # keep the full env so liboqs can locate its native DLL
    env["PYTHONPATH"] = str(_REPO)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(proof)],
        cwd=str(_REPO),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"PQC receipt proof failed:\n{result.stdout}\n{result.stderr}"
    assert "all checks passed" in result.stdout
