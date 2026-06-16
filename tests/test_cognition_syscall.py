import json
import subprocess
import sys

from python.scbe import cognition_syscall as CS
from python.scbe import illuminate as IL


def test_exact_match_allows():
    receipt = CS.receipt_from_program(["add", "mul", "inc"])
    assert receipt["decision"] == "ALLOW"
    assert receipt["action"] == "execute"
    assert receipt["thought"]["relation"] == "exact match"


def test_diverged_escalates():
    receipt = CS.receipt_from_program(["add", "sqrt", "mul"])
    assert receipt["decision"] == "ESCALATE"
    assert receipt["action"] == "route_to_verifier"
    assert receipt["thought"]["relation"] in {"close", "diverged", "sign flip"}


def test_incomplete_denies():
    receipt = CS.receipt_from_program(["add", "add", "add"])
    assert receipt["decision"] == "DENY"
    assert receipt["action"] == "reject"


def test_archive_governance_counts_all_niches():
    archive = IL.illuminate(generations=2, batch=80, seed=2)
    payload = CS.govern_archive(archive)
    assert sum(payload["counts"].values()) == payload["niches"] == len(archive)
    assert payload["counts"]["ALLOW"] > 0


def test_cli_json_receipt_smoke():
    proc = subprocess.run(
        [sys.executable, "scbe.py", "cog", "+", "sqrt", "*", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(proc.stdout)
    assert receipt["schema"] == CS.SCHEMA
    assert receipt["decision"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}

