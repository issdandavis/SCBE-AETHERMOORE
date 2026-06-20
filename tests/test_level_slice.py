"""level_slice: the vertical slice -- one free model clears ONE governed level end to end.

A sandbox of messy ``*.tmp`` files is the level; winning is every file normalized to ``*.bak``,
checked by READING the filesystem. The new name is the only blank (pair_loop), each rename is
governed + sealed (desktop_access), progress is tracked + packed (context_ledger), and the move
record is etched reversibly as stones (board.py). These tests prove it composes AND that the walls
hold: a wrong name is caught, a destructive name is refused, a path escape is refused.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.level_slice import (  # noqa: E402
    build_registry,
    normalize,
    run_level,
    _with_sandbox,
)

FILES = ["Draft One.tmp", "report.tmp", "NOTES final.tmp"]


def test_clears_the_level_and_wins():
    out = _with_sandbox(FILES)
    assert out["won"] is True
    assert out["on_disk"] == ["draft-one.bak", "notes-final.bak", "report.bak"]
    assert all(m["decision"] == "ALLOWED" for m in out["moves"])
    assert all(m["model_calls"] == 1 for m in out["moves"])  # one blank per file, nothing else


def test_receipts_and_ledger_are_sealed_and_move_record_is_reversible():
    out = _with_sandbox(FILES)
    assert out["sealed"] is True  # governed action receipts tamper-evident
    assert out["ledger_sealed"] is True  # self-memory event log tamper-evident
    assert out["reversible"] is True  # the etched stones replay losslessly
    assert "->" in out["pack"]  # context packed to shorthand


def test_a_wrong_name_model_is_caught_by_the_walls():
    # a model that ignores the task and proposes a name outside the walls never clears a file;
    # the harness fails honestly rather than committing a bad rename.
    def bad_model(goal, out, allowed):
        return "whatever.txt"

    out = _with_sandbox(FILES, name_model=bad_model)
    assert out["won"] is False
    assert all(m["decision"] == "NO_NAME" for m in out["moves"])
    assert out["on_disk"] == sorted(FILES)  # nothing was renamed


def test_a_destructive_name_is_refused_by_the_screen():
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td)
        (sandbox / "a.tmp").write_text("x", encoding="utf-8")
        reg = build_registry(sandbox)
        rec = reg.invoke("rename_file", {"src": "a.tmp", "dst": "rm -rf /"}, confirm="x")
        assert rec["decision"] == "REFUSED"  # never-delete screen, even as a filename
        assert (sandbox / "a.tmp").exists()  # the file is untouched


def test_a_path_escape_is_refused():
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td)
        (sandbox / "a.tmp").write_text("x", encoding="utf-8")
        reg = build_registry(sandbox)
        rec = reg.invoke("rename_file", {"src": "a.tmp", "dst": "../escaped.bak"}, confirm="x")
        assert rec["decision"] == "ALLOWED"  # passes the registry...
        assert "escapes the sandbox" in rec["result"]  # ...but the handler confines it
        assert not (sandbox.parent / "escaped.bak").exists()


def test_a_guarded_rename_needs_a_confirm_reason():
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td)
        (sandbox / "a.tmp").write_text("x", encoding="utf-8")
        reg = build_registry(sandbox)
        rec = reg.invoke("rename_file", {"src": "a.tmp", "dst": "a.bak"})  # no confirm
        assert rec["decision"] == "NEEDS_CONFIRM"
        assert (sandbox / "a.tmp").exists()


def test_normalize_is_pure():
    assert normalize("Draft One.tmp") == "draft-one.bak"
    assert normalize("report.tmp") == "report.bak"


def test_run_level_on_explicit_sandbox():
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td)
        for f in ["X Y.tmp", "z.tmp"]:
            (sandbox / f).write_text("x", encoding="utf-8")
        out = run_level(["X Y.tmp", "z.tmp"], sandbox)
        assert out["won"] is True
        assert sorted(p.name for p in sandbox.iterdir()) == ["x-y.bak", "z.bak"]
