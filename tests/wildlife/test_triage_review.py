"""Pin the triage review report shape.

Locks the markdown structure so future agents (or Issac) can grep / parse
the report deterministically and so the bucket classification doesn't
silently regress.
"""

from __future__ import annotations

from scripts.wildlife.triage_review import _bucket, render

# ----------------------------- bucket classifier -------------------------- #


def test_bucket_recognises_canonical_replies() -> None:
    assert _bucket("DELETE") == "DELETE"
    assert _bucket("DELETE (if dead code)") == "DELETE"
    assert _bucket("delete the function") == "DELETE"
    assert _bucket("DOCUMENT this is intentional") == "DOCUMENT"
    assert _bucket("FIX: refactor parser") == "FIX"
    assert _bucket("FIX:<one-line plan>") == "FIX"


def test_bucket_unknown_replies_go_to_other() -> None:
    assert _bucket("") == "OTHER"
    assert _bucket("hmm not sure") == "OTHER"
    assert _bucket("REWRITE everything") == "OTHER"


# ----------------------------- render contract ---------------------------- #


def _mini_results() -> dict:
    return {
        "schema": "wildlife-dispatch-results-v1",
        "ran_at": "2026-05-09T00:00:00Z",
        "results": [
            {
                "animal_id": "todo-src_x.py-10",
                "pack": "CROW",
                "ok": True,
                "title": "TODO: clean up x",
                "response": "DELETE (if dead code)",
            },
            {
                "animal_id": "todo-src_y.py-20",
                "pack": "CROW",
                "ok": True,
                "title": "TODO: do the thing",
                "response": "FIX: rename helper",
            },
            {
                "animal_id": "issue-1",
                "pack": "WOLF",
                "ok": True,
                "title": "RCE in upload",
                "response": (
                    "(1) likely root cause: missing input sanitization\n"
                    "(2) edit src/api/upload.py\n"
                    "(3) test_upload_rejects_shell.py"
                ),
            },
            {
                "animal_id": "issue-broken",
                "pack": "WOLF",
                "ok": False,
                "error": "HTTPError: HTTP Error 500: Internal Server Error",
            },
        ],
    }


def _mini_board() -> dict:
    return {
        "schema": "wildlife-board-v1",
        "harvested_at": "2026-05-09T00:00:00Z",
        "packs": {
            "crows": [
                {"id": "todo-src_x.py-10", "title": "TODO: clean up x", "path": "src/x.py"},
                {"id": "todo-src_y.py-20", "title": "TODO: do the thing", "path": "src/y.py"},
            ],
            "wolves": [
                {"id": "issue-1", "title": "RCE in upload", "path": ""},
                {"id": "issue-broken", "title": "...", "path": ""},
            ],
        },
    }


def test_render_summary_table_includes_buckets_per_pack() -> None:
    md = render(_mini_results(), _mini_board())
    assert "## Summary by pack" in md
    assert "| Pack | DELETE | DOCUMENT | FIX | OTHER |" in md
    # CROW row: 1 DELETE, 1 FIX
    assert "| CROW | 1 | 0 | 1 | 0 |" in md
    # WOLF row: 1 OTHER (the FIX-shaped reply doesn't start with FIX:)
    assert "| WOLF | 0 | 0 | 0 | 1 |" in md


def test_render_groups_entries_by_pack_then_bucket() -> None:
    md = render(_mini_results(), _mini_board())
    assert "## crows (CROW)" in md
    # FIX section comes before DELETE in the output (FIX > DOCUMENT > DELETE > OTHER)
    fix_pos = md.find("### FIX — 1")
    delete_pos = md.find("### DELETE — 1")
    assert fix_pos > 0 and delete_pos > 0
    assert fix_pos < delete_pos


def test_render_includes_file_path_for_animal() -> None:
    md = render(_mini_results(), _mini_board())
    assert "**`src/x.py`**" in md
    assert "**`src/y.py`**" in md


def test_render_surfaces_failures_with_error_types() -> None:
    md = render(_mini_results(), _mini_board())
    assert "## Failures" in md
    assert "`HTTPError`" in md


def test_render_handles_empty_results() -> None:
    md = render({"results": []}, {"packs": {}})
    assert "# Wildlife Triage Review" in md
    assert "**Total tamed:** 0" in md
