"""Tests for the meet-in-the-middle codegen protocol."""

from __future__ import annotations

import pytest

from src.agentic.meet_in_the_middle import (
    CodeHalf,
    SEAM_MARKER,
    SeamContract,
    merge_halves,
)

# ---------------------------------------------------------------------------
#  SeamContract canonicalization
# ---------------------------------------------------------------------------


def test_seam_contract_hash_is_stable() -> None:
    a = SeamContract(names=("x", "y"), types=("int", "int"))
    b = SeamContract(names=("x", "y"), types=("int", "int"))
    assert a.seam_tongue_hash() == b.seam_tongue_hash()


def test_seam_contract_hash_changes_when_names_change() -> None:
    a = SeamContract(names=("x", "y"))
    b = SeamContract(names=("x", "z"))
    assert a.seam_tongue_hash() != b.seam_tongue_hash()


def test_seam_contract_notes_do_not_affect_hash() -> None:
    a = SeamContract(names=("x",), notes="forward agent should validate input")
    b = SeamContract(names=("x",), notes="totally different note")
    assert a.seam_tongue_hash() == b.seam_tongue_hash()


def test_seam_contract_rejects_bad_identifiers() -> None:
    with pytest.raises(ValueError):
        SeamContract(names=("123bad",))
    with pytest.raises(ValueError):
        SeamContract(names=("good", "1also-bad"))


def test_seam_contract_rejects_mismatched_types() -> None:
    with pytest.raises(ValueError):
        SeamContract(names=("x", "y"), types=("int",))


# ---------------------------------------------------------------------------
#  Convergent merge
# ---------------------------------------------------------------------------

CONTRACT = SeamContract(names=("payload", "verdict"), types=("dict", "str"))

FORWARD_GOOD = """\
import json

def forward_intake(raw_text):
    payload = {"text": raw_text, "len": len(raw_text)}
    verdict = "ALLOW" if len(raw_text) < 200 else "QUARANTINE"
    %(seam)s
""" % {"seam": SEAM_MARKER}

REVERSE_GOOD = """\
%(seam)s
    return {"payload": payload, "verdict": verdict, "audit": True}


if __name__ == "__main__":
    import sys
    out = forward_intake(sys.argv[1] if len(sys.argv) > 1 else "hello world")
    print(out["verdict"], out["payload"]["len"])
""" % {"seam": SEAM_MARKER}


def test_convergent_halves_merge_and_run() -> None:
    fwd = CodeHalf(direction="forward", code=FORWARD_GOOD, declared_seam=CONTRACT)
    rev = CodeHalf(direction="reverse", code=REVERSE_GOOD, declared_seam=CONTRACT)
    report = merge_halves(fwd, rev, execute=True)
    assert report.converged, report.diagnostics
    assert report.forward_seam_hash == report.reverse_seam_hash
    assert report.execution_returncode == 0
    assert "ALLOW" in (report.execution_stdout or "")


def test_seam_mismatch_blocks_merge() -> None:
    fwd_contract = SeamContract(names=("payload", "verdict"))
    rev_contract = SeamContract(names=("payload", "decision"))  # diverged name
    fwd = CodeHalf(direction="forward", code=FORWARD_GOOD, declared_seam=fwd_contract)
    # Build a reverse half that names `decision` instead of `verdict` so it
    # consistently uses the diverged contract.
    rev_code = REVERSE_GOOD.replace("verdict", "decision")
    rev = CodeHalf(direction="reverse", code=rev_code, declared_seam=rev_contract)
    report = merge_halves(fwd, rev, execute=False)
    assert not report.converged
    assert any("seam contracts differ" in d for d in report.diagnostics)


def test_forward_missing_seam_name_is_caught() -> None:
    # Forward only binds `payload`, contract demands payload + verdict.
    fwd_code = """\
def forward_intake(raw_text):
    payload = {"text": raw_text}
    %(seam)s
""" % {"seam": SEAM_MARKER}
    fwd = CodeHalf(direction="forward", code=fwd_code, declared_seam=CONTRACT)
    rev = CodeHalf(direction="reverse", code=REVERSE_GOOD, declared_seam=CONTRACT)
    report = merge_halves(fwd, rev, execute=False)
    assert not report.converged
    assert any("does not bind seam names" in d for d in report.diagnostics)


def test_missing_seam_marker_blocks() -> None:
    fwd = CodeHalf(direction="forward", code="x = 1\n", declared_seam=CONTRACT)
    rev = CodeHalf(direction="reverse", code=REVERSE_GOOD, declared_seam=CONTRACT)
    report = merge_halves(fwd, rev)
    assert not report.converged
    assert any("forward half missing SEAM_MARKER" in d for d in report.diagnostics)


def test_direction_validation() -> None:
    with pytest.raises(ValueError):
        CodeHalf(direction="sideways", code="x = 1\n", declared_seam=CONTRACT)
