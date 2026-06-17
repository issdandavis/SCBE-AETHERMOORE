from __future__ import annotations

import subprocess
import sys


def test_prove_black_box_value_command_prints_top_finding(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/system/prove_black_box_value.py", "--out-dir", str(tmp_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert "SCBE Black Box proof run" in result.stdout
    assert "Top finding:" in result.stdout
    assert "Buyer ZIP:" in result.stdout
    assert "Text report:" in result.stdout
