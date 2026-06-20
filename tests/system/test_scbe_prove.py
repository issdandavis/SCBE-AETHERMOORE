from __future__ import annotations

import subprocess
import sys


def test_scbe_prove_forge_derives_then_reuses_memory() -> None:
    result = subprocess.run(
        [sys.executable, "scbe.py", "prove", "forge"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )

    assert result.returncode == 0, result.stderr
    assert "SCBE Forge proof run" in result.stdout
    assert "Run 1: derive, build, verify, remember" in result.stdout
    assert "Run 2: reuse remembered recipe, rebuild, re-verify" in result.stdout
    assert "DERIVED fresh -> REMEMBERED" in result.stdout
    assert "REUSED memory" in result.stdout
    assert result.stdout.count("BUILT + VERIFIED: YES") == 2
    assert "PROOF COMPLETE" in result.stdout


def test_scbe_prove_black_box_forwards_to_value_proof(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, "scbe.py", "prove", "black-box", "--out-dir", str(tmp_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )

    assert result.returncode == 0, result.stderr
    assert "SCBE Black Box proof run" in result.stdout
    assert "Top finding:" in result.stdout
    assert "Buyer ZIP:" in result.stdout
    assert "Text report:" in result.stdout
