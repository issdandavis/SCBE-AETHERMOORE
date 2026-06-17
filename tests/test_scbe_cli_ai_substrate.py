import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCBE = REPO_ROOT / "scbe.py"


def run_scbe(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCBE), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )


def test_encode_code_cli_emits_ast_cube_matrix_json(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")

    result = run_scbe("encode-code", str(src), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["shape"][1] == 14
    assert payload["nodes"][1]["type"] == "FunctionDef"
    assert payload["nodes"][1]["face_trits"]["KO"] == 1
    assert len(payload["matrix"]) == payload["shape"][0]


def test_stereo_cli_emits_registered_two_lens_json(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text("def f(x):\n    y = x + 1\n    return y\n", encoding="utf-8")

    result = run_scbe("stereo", str(src), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["lock_ratio"] == 1.0
    assert payload["stereo_width"] == 18
    assert len(payload["stereo_matrix"]) == payload["node_count"]
    assert {"lens_a_relation", "lens_b_faces", "lens_b_location"} <= set(payload["tokens"][1])
