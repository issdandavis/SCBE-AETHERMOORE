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
        timeout=20,
        check=False,
    )


def test_full_name_tongue_alias_works_for_direct_encode() -> None:
    direct = run_scbe("enc", "dr", "fox")
    full_name = run_scbe("enc", "draumric", "fox")

    assert direct.returncode == 0, direct.stderr
    assert full_name.returncode == 0, full_name.stderr
    assert full_name.stdout == direct.stdout


def test_plain_english_encode_routes_to_local_command_without_ai() -> None:
    natural = run_scbe("how", "do", "I", "encode", "fox", "in", "draumric?")
    direct = run_scbe("enc", "dr", "fox")

    assert natural.returncode == 0, natural.stderr
    assert natural.stdout == direct.stdout
    assert "model took too long" not in natural.stdout.lower()


def test_plain_english_explain_routes_to_local_command_without_ai() -> None:
    result = run_scbe("what", "is", "L12")

    assert result.returncode == 0, result.stderr
    assert "L12: Harmonic Wall" in result.stdout


def test_describe_json_is_machine_readable() -> None:
    result = run_scbe("describe", "fox", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert payload["flow"].endswith(f"-> {payload['decision']}")
    assert {"what", "see", "hear", "feel", "taste", "flow", "tongue"} <= set(payload)
