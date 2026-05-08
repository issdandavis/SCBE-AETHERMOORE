"""End-to-end integration tests for the floating-tower self-modify path.

Full lifecycle covered:

    route ×N -> promotions -> promote --as <name> -> aliases -> alias <name>
                                                  -> unpromote --alias <name>

These run real subprocesses against the geoseal CLI binary so the
BoundCommand wiring, parameter sets, JSON envelopes, and cross-tongue
emission are all verified end-to-end.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GEOSEAL_CLI = "src/geoseal_cli.py"


def _run(*subcmd_and_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, *subcmd_and_args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _route_n_times(
    n: int, ledger_path: Path, *, op: str = "add", dst: str = "RU"
) -> None:
    for _ in range(n):
        proc = _run(
            "route",
            "--manual",
            "--op-name", op,
            "--dst-tongue", dst,
            "--arg", "a=x",
            "--arg", "b=y",
            "--ledger-path", str(ledger_path),
        )
        assert proc.returncode == 0, proc.stderr


def _digest_for(ledger_path: Path) -> str:
    """Read the (single) digest from a ledger that's been written to."""
    proc = _run("promotions", "--ledger-path", str(ledger_path), "--show-all", "--threshold", "1")
    body = json.loads(proc.stdout)
    assert body["shown"], "ledger has no entries"
    return body["shown"][0]["digest"]


# ---------------------------------------------------------------------------
#  Empty / missing registry
# ---------------------------------------------------------------------------


def test_aliases_on_missing_registry_returns_empty(tmp_path: Path) -> None:
    proc = _run("aliases", "--registry-path", str(tmp_path / "none.json"))
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["alias_count"] == 0
    assert body["registry_exists"] is False
    assert body["aliases"] == []


# ---------------------------------------------------------------------------
#  Promote with explicit digest
# ---------------------------------------------------------------------------


def test_promote_below_threshold_quarantines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(2, ledger)  # below default threshold of 3
    digest = _digest_for(ledger)

    proc = _run(
        "promote",
        "--digest", digest,
        "--name", "ax",
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
        "--threshold", "3",
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "BelowThreshold"


def test_promote_unknown_digest_quarantines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger)

    proc = _run(
        "promote",
        "--digest", "0" * 64,  # not in ledger
        "--name", "ax",
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "DigestNotFound"


def test_promote_at_threshold_succeeds(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger)
    digest = _digest_for(ledger)

    proc = _run(
        "promote",
        "--digest", digest,
        "--name", "ax",
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
        "--threshold", "3",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    body = json.loads(proc.stdout)
    assert body["verdict"] == "ALLOW"
    promoted = body["promoted"]
    assert promoted["name"] == "ax"
    assert promoted["op_name"] == "add"
    assert promoted["dst_tongue"] == "RU"
    assert promoted["default_args"] == {"a": "x", "b": "y"}
    assert promoted["promoted_from_count"] == 3
    assert registry.exists()


def test_promote_with_invalid_alias_name_quarantines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger)
    digest = _digest_for(ledger)

    proc = _run(
        "promote",
        "--digest", digest,
        "--name", "Bad_Name",  # uppercase + underscore both rejected
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "AliasNameError"


def test_promote_with_reserved_name_quarantines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger)
    digest = _digest_for(ledger)

    proc = _run(
        "promote",
        "--digest", digest,
        "--name", "route",  # reserved built-in subcommand name
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "AliasNameError"
    assert "reserved" in err["message"]


def test_promote_duplicate_without_overwrite_quarantines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger)
    digest = _digest_for(ledger)

    common = (
        "promote",
        "--digest", digest,
        "--name", "ax",
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
    )
    assert _run(*common).returncode == 0
    # Second promote without --overwrite should refuse.
    proc = _run(*common)
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "AliasNameError"
    assert "already exists" in err["message"]


def test_promote_with_overwrite_replaces(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger, op="add", dst="RU")
    digest_add = _digest_for(ledger)
    assert _run(
        "promote", "--digest", digest_add, "--name", "ax",
        "--ledger-path", str(ledger), "--registry-path", str(registry),
    ).returncode == 0

    # Add a new dispatch, then re-promote `ax` to point at it.
    _route_n_times(3, ledger, op="mul", dst="KO")
    proc_promotions = _run(
        "promotions", "--ledger-path", str(ledger), "--threshold", "3"
    )
    candidates = json.loads(proc_promotions.stdout)["shown"]
    digest_mul = next(
        c["digest"] for c in candidates if "mul" in c["sample_argv"]
    )

    proc = _run(
        "promote", "--digest", digest_mul, "--name", "ax", "--overwrite",
        "--ledger-path", str(ledger), "--registry-path", str(registry),
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["promoted"]["op_name"] == "mul"


# ---------------------------------------------------------------------------
#  Promote --latest
# ---------------------------------------------------------------------------


def test_promote_latest_picks_top_candidate(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    # add: 5x, mul: 3x  → add is the top candidate.
    _route_n_times(5, ledger, op="add")
    _route_n_times(3, ledger, op="mul")

    proc = _run(
        "promote",
        "--latest",
        "--name", "top",
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    body = json.loads(proc.stdout)
    assert body["promoted"]["op_name"] == "add"
    assert body["promoted"]["promoted_from_count"] == 5


def test_promote_latest_with_no_candidates_quarantines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    # Only 1 invocation — below default threshold.
    _route_n_times(1, ledger)

    proc = _run(
        "promote",
        "--latest",
        "--name", "top",
        "--ledger-path", str(ledger),
        "--registry-path", str(registry),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "NoCandidate"


# ---------------------------------------------------------------------------
#  aliases — list
# ---------------------------------------------------------------------------


def test_aliases_lists_registered_entries(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger, op="add")
    digest_add = _digest_for(ledger)
    _run(
        "promote", "--digest", digest_add, "--name", "ax",
        "--ledger-path", str(ledger), "--registry-path", str(registry),
    )
    _route_n_times(3, ledger, op="sub")
    digest_sub = next(
        c["digest"]
        for c in json.loads(
            _run("promotions", "--ledger-path", str(ledger), "--threshold", "3").stdout
        )["shown"]
        if "sub" in c["sample_argv"]
    )
    _run(
        "promote", "--digest", digest_sub, "--name", "by",
        "--ledger-path", str(ledger), "--registry-path", str(registry),
    )

    proc = _run("aliases", "--registry-path", str(registry))
    assert proc.returncode == 0
    body = json.loads(proc.stdout)
    assert body["alias_count"] == 2
    names = {a["name"] for a in body["aliases"]}
    assert names == {"ax", "by"}


# ---------------------------------------------------------------------------
#  alias — invoke
# ---------------------------------------------------------------------------


def _promote(tmp_path: Path) -> tuple[Path, Path]:
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"
    _route_n_times(3, ledger, op="add", dst="RU")
    digest = _digest_for(ledger)
    assert _run(
        "promote", "--digest", digest, "--name", "ax",
        "--ledger-path", str(ledger), "--registry-path", str(registry),
    ).returncode == 0
    return ledger, registry


def test_alias_invoke_uses_default_args(tmp_path: Path) -> None:
    _, registry = _promote(tmp_path)
    proc = _run("alias", "--name", "ax", "--registry-path", str(registry), "--emit")
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["op_name"] == "add"
    assert body["dst_tongue"] == "RU"
    assert body["args"] == {"a": "x", "b": "y"}
    assert body["dst_code"] == "x.wrapping_add(y)"


def test_alias_invoke_overrides_args_per_key(tmp_path: Path) -> None:
    """Caller --arg overrides override stored defaults on a per-key basis;
    keys not overridden fall back to the stored value."""
    _, registry = _promote(tmp_path)
    proc = _run(
        "alias", "--name", "ax",
        "--arg", "a=p",  # only override 'a'; 'b' should use default 'y'
        "--registry-path", str(registry),
        "--emit",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["args"] == {"a": "p", "b": "y"}
    assert body["dst_code"] == "p.wrapping_add(y)"


def test_alias_invoke_emit_all_produces_six_translations(tmp_path: Path) -> None:
    _, registry = _promote(tmp_path)
    proc = _run("alias", "--name", "ax", "--registry-path", str(registry), "--emit-all")
    assert proc.returncode == 0
    body = json.loads(proc.stdout)
    assert set(body["translations"].keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    assert body["translations"]["RU"] == "x.wrapping_add(y)"
    assert body["dst_code"] == body["translations"]["RU"]  # routed tongue


def test_alias_invoke_raw_mode_pipe_friendly(tmp_path: Path) -> None:
    _, registry = _promote(tmp_path)
    proc = _run(
        "alias", "--name", "ax", "--registry-path", str(registry), "--emit", "--raw"
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "x.wrapping_add(y)"


def test_alias_invoke_unknown_quarantines(tmp_path: Path) -> None:
    proc = _run(
        "alias",
        "--name", "nope",
        "--registry-path", str(tmp_path / "registry.json"),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "AliasNotFoundError"


def test_alias_invoke_malformed_arg_quarantines(tmp_path: Path) -> None:
    _, registry = _promote(tmp_path)
    proc = _run(
        "alias",
        "--name", "ax",
        "--arg", "no_equals_sign",
        "--registry-path", str(registry),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "ArgParseError"


# ---------------------------------------------------------------------------
#  unpromote — remove
# ---------------------------------------------------------------------------


def test_unpromote_removes_alias(tmp_path: Path) -> None:
    _, registry = _promote(tmp_path)
    proc = _run("unpromote", "--alias", "ax", "--registry-path", str(registry))
    assert proc.returncode == 0
    body = json.loads(proc.stdout)
    assert body["removed"]["name"] == "ax"
    # Subsequent invoke must fail.
    proc_invoke = _run("alias", "--name", "ax", "--registry-path", str(registry))
    assert proc_invoke.returncode == 2
    assert json.loads(proc_invoke.stdout)["error_type"] == "AliasNotFoundError"


def test_unpromote_missing_alias_quarantines(tmp_path: Path) -> None:
    proc = _run(
        "unpromote",
        "--alias", "nope",
        "--registry-path", str(tmp_path / "registry.json"),
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "AliasNotFoundError"


# ---------------------------------------------------------------------------
#  Full lifecycle smoke — the floating-tower mechanic in one test
# ---------------------------------------------------------------------------


def test_full_floating_tower_lifecycle(tmp_path: Path) -> None:
    """The single end-to-end story: 4 invocations -> promote -> alias
    invocation produces byte-identical output to the original route."""
    ledger = tmp_path / "ledger.jsonl"
    registry = tmp_path / "registry.json"

    # Phase 1 — agent makes the same dispatch 4 times via route.
    _route_n_times(4, ledger, op="mul", dst="DR")

    # Phase 2 — operator promotes the latest candidate.
    proc_promote = _run(
        "promote", "--latest", "--name", "mxd",
        "--ledger-path", str(ledger), "--registry-path", str(registry),
    )
    assert proc_promote.returncode == 0, proc_promote.stdout

    # Phase 3 — alias invocation produces the same emitted code as
    # would the original `route ... --emit` call.
    proc_alias = _run(
        "alias", "--name", "mxd", "--registry-path", str(registry), "--emit"
    )
    proc_route = _run(
        "route", "--manual", "--op-name", "mul", "--dst-tongue", "DR",
        "--arg", "a=x", "--arg", "b=y",
        "--ledger-path", str(ledger), "--no-ledger", "--emit",
    )
    assert proc_alias.returncode == 0
    assert proc_route.returncode == 0
    alias_code = json.loads(proc_alias.stdout)["dst_code"]
    route_code = json.loads(proc_route.stdout)["dst_code"]
    assert alias_code == route_code, (
        f"alias and route disagree on emission: "
        f"alias={alias_code!r} route={route_code!r}"
    )
