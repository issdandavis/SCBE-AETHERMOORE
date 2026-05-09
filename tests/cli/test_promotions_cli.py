"""Live `geoseal promotions` subprocess integration tests.

The promotions subcommand reads the route promotion ledger and surfaces
dispatch patterns that have crossed the recurrence threshold. End-to-end
flow: route 3+ times -> promotions reports a candidate.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GEOSEAL_CLI = "src/geoseal_cli.py"


def _route(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "route", *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _promotions(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "promotions", *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
#  Empty / missing ledger
# ---------------------------------------------------------------------------


def test_promotions_on_missing_ledger_returns_empty(tmp_path: Path) -> None:
    ledger_path = tmp_path / "nonexistent.jsonl"
    proc = _promotions("--ledger-path", str(ledger_path))
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["ledger_exists"] is False
    assert body["total_entries"] == 0
    assert body["candidate_count"] == 0
    assert body["shown"] == []


# ---------------------------------------------------------------------------
#  Below threshold — no candidates
# ---------------------------------------------------------------------------


def test_promotions_below_threshold_lists_no_candidates(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    # Two routes — below the default threshold of 3.
    for _ in range(2):
        proc = _route(
            "--manual",
            "--op-name",
            "add",
            "--dst-tongue",
            "RU",
            "--arg",
            "a=x",
            "--arg",
            "b=y",
            "--ledger-path",
            str(ledger_path),
        )
        assert proc.returncode == 0

    proc = _promotions("--ledger-path", str(ledger_path), "--threshold", "3")
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["total_entries"] == 1
    assert body["candidate_count"] == 0
    assert body["shown"] == []


# ---------------------------------------------------------------------------
#  Above threshold — candidate surfaces
# ---------------------------------------------------------------------------


def test_promotions_above_threshold_surfaces_candidate(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    for _ in range(4):
        proc = _route(
            "--manual",
            "--op-name",
            "mul",
            "--dst-tongue",
            "RU",
            "--arg",
            "a=x",
            "--arg",
            "b=y",
            "--ledger-path",
            str(ledger_path),
        )
        assert proc.returncode == 0

    proc = _promotions("--ledger-path", str(ledger_path), "--threshold", "3")
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["candidate_count"] == 1
    assert len(body["shown"]) == 1
    candidate = body["shown"][0]
    assert candidate["count"] == 4
    assert candidate["is_candidate"] is True
    # The normalised argv captures the dispatch shape.
    assert "--op-name" in candidate["sample_argv"]
    assert "mul" in candidate["sample_argv"]


def test_promotions_show_all_includes_below_threshold(tmp_path: Path) -> None:
    """--show-all surfaces entries below the threshold too, useful for
    inspecting what's *almost* a candidate."""
    ledger_path = tmp_path / "ledger.jsonl"
    # add: 4 times → above threshold
    for _ in range(4):
        _route(
            "--manual",
            "--op-name",
            "add",
            "--dst-tongue",
            "RU",
            "--arg",
            "a=x",
            "--arg",
            "b=y",
            "--ledger-path",
            str(ledger_path),
        )
    # sub: 1 time → below
    _route(
        "--manual",
        "--op-name",
        "sub",
        "--dst-tongue",
        "RU",
        "--arg",
        "a=p",
        "--arg",
        "b=q",
        "--ledger-path",
        str(ledger_path),
    )

    proc = _promotions("--ledger-path", str(ledger_path), "--threshold", "3", "--show-all")
    assert proc.returncode == 0
    body = json.loads(proc.stdout)
    assert body["total_entries"] == 2
    assert body["candidate_count"] == 1
    assert body["shown_count"] == 2
    counts = sorted(e["count"] for e in body["shown"])
    assert counts == [1, 4]
    # is_candidate flag per entry.
    candidates = [e for e in body["shown"] if e["is_candidate"]]
    assert len(candidates) == 1


def test_promotions_sorted_by_count_descending(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    # add: 5 invocations
    for _ in range(5):
        _route(
            "--manual",
            "--op-name",
            "add",
            "--dst-tongue",
            "KO",
            "--arg",
            "a=x",
            "--arg",
            "b=y",
            "--ledger-path",
            str(ledger_path),
        )
    # mul: 3 invocations
    for _ in range(3):
        _route(
            "--manual",
            "--op-name",
            "mul",
            "--dst-tongue",
            "KO",
            "--arg",
            "a=x",
            "--arg",
            "b=y",
            "--ledger-path",
            str(ledger_path),
        )

    proc = _promotions("--ledger-path", str(ledger_path), "--threshold", "3")
    body = json.loads(proc.stdout)
    counts = [e["count"] for e in body["shown"]]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] == 5  # add ranked first


# ---------------------------------------------------------------------------
#  Threshold parameter respected
# ---------------------------------------------------------------------------


def test_promotions_threshold_parameter_changes_candidate_set(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    for _ in range(3):
        _route(
            "--manual",
            "--op-name",
            "div",
            "--dst-tongue",
            "KO",
            "--arg",
            "a=x",
            "--arg",
            "b=y",
            "--ledger-path",
            str(ledger_path),
        )

    # Threshold 3 → div is a candidate (count=3).
    proc_lo = _promotions("--ledger-path", str(ledger_path), "--threshold", "3")
    assert json.loads(proc_lo.stdout)["candidate_count"] == 1

    # Threshold 5 → div is NOT a candidate.
    proc_hi = _promotions("--ledger-path", str(ledger_path), "--threshold", "5")
    assert json.loads(proc_hi.stdout)["candidate_count"] == 0
