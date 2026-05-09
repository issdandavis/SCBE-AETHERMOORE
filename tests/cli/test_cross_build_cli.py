"""Live `geoseal cross-build` subprocess integration tests.

These run the actual CLI binary so we know the BoundCommand wiring,
parameter-set validation, and JSON output all hold end-to-end. Direct
unit coverage for the IR is in `test_cross_build_ir.py`; these tests
are the cross-tongue parity check via the real swarm-dispatch surface.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GEOSEAL_CLI = "src/geoseal_cli.py"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "cross-build", *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _run_alias(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "xb", *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
#  Single-translation mode
# ---------------------------------------------------------------------------


def test_cross_build_single_ko_to_ru_for_add() -> None:
    proc = _run(
        "--src-code",
        "(x + y)",
        "--src-tongue",
        "KO",
        "--dst-tongue",
        "RU",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["mode"] == "single"
    assert body["src_tongue"] == "KO"
    assert body["dst_tongue"] == "RU"
    assert body["src_language"] == "python"
    assert body["dst_language"] == "rust"
    assert body["dst_code"] == "x.wrapping_add(y)"
    assert body["ir"]["op_name"] == "add"


def test_cross_build_single_av_to_dr_for_xor() -> None:
    proc = _run(
        "--src-code",
        "(p ^ q)",
        "--src-tongue",
        "AV",
        "--dst-tongue",
        "DR",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["ir"]["op_name"] == "xor"
    # Haskell xor is `xor`
    assert "xor" in body["dst_code"].lower()


def test_alias_xb_works_identically() -> None:
    main = _run("--src-code", "(x - y)", "--src-tongue", "KO", "--dst-tongue", "DR")
    aliased = _run_alias("--src-code", "(x - y)", "--src-tongue", "KO", "--dst-tongue", "DR")
    assert main.returncode == 0 and aliased.returncode == 0
    assert json.loads(main.stdout)["dst_code"] == json.loads(aliased.stdout)["dst_code"]


# ---------------------------------------------------------------------------
#  Broadcast mode — emit IR in every tongue
# ---------------------------------------------------------------------------


def test_cross_build_broadcast_emits_five_translations() -> None:
    proc = _run(
        "--src-code",
        "(x + y)",
        "--src-tongue",
        "KO",
        "--all-tongues",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["mode"] == "broadcast"
    # Source tongue is excluded — 5 destinations.
    translations = body["translations"]
    assert set(translations.keys()) == {"AV", "RU", "CA", "UM", "DR"}
    # Sanity: the Rust translation is the canonical wrapping_add form.
    assert translations["RU"] == "x.wrapping_add(y)"


# ---------------------------------------------------------------------------
#  Info mode
# ---------------------------------------------------------------------------


def test_cross_build_list_ops_reports_64_participating() -> None:
    """After CA-tongue canonicalisation the sphere closes — all 64
    lexicon ops round-trip, the excluded set is empty."""
    proc = _run("--list-ops")
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["participating_count"] == 64
    assert body["excluded_count"] == 0
    assert "add" in body["participating_ops"]
    # The 7 previously-excluded aggregation ops now round-trip cleanly.
    for op in ("count", "fold", "mean", "reduce", "scan", "stdev", "variance"):
        assert op in body["participating_ops"], f"{op} should participate"
        assert op not in body["excluded_ops"]


# ---------------------------------------------------------------------------
#  Quarantine surfaces — funnel-bounded behaviour at the CLI layer
# ---------------------------------------------------------------------------


def test_cross_build_quarantines_arbitrary_code() -> None:
    proc = _run(
        "--src-code",
        "import os",
        "--src-tongue",
        "KO",
        "--dst-tongue",
        "RU",
    )
    assert proc.returncode == 2, "non-lexicon source must surface as QUARANTINE"
    err = json.loads(proc.stdout)
    assert err["verdict"] == "QUARANTINE"
    assert err["error_type"] == "LiftFailure"


def test_cross_build_rejects_mutually_exclusive_modes() -> None:
    """Asking for single + broadcast + info at the same time must trip
    the parameter-set validator before we touch the IR."""
    proc = _run(
        "--src-code",
        "(x + y)",
        "--src-tongue",
        "KO",
        "--dst-tongue",
        "RU",
        "--all-tongues",
    )
    assert proc.returncode != 0
    assert "mutually exclusive" in proc.stderr


# ---------------------------------------------------------------------------
#  Cross-tongue parity check (the hook's request, in test form)
# ---------------------------------------------------------------------------


def test_cross_tongue_parity_round_trip_through_cli() -> None:
    """Round-trip via the CLI itself: KO -> RU via subprocess A,
    then RU -> KO via subprocess B, must return the original source."""
    forward = _run(
        "--src-code",
        "(x * y)",
        "--src-tongue",
        "KO",
        "--dst-tongue",
        "RU",
    )
    assert forward.returncode == 0
    forward_body = json.loads(forward.stdout)
    rust_code = forward_body["dst_code"]

    back = _run(
        "--src-code",
        rust_code,
        "--src-tongue",
        "RU",
        "--dst-tongue",
        "KO",
    )
    assert back.returncode == 0
    assert json.loads(back.stdout)["dst_code"] == "(x * y)"
