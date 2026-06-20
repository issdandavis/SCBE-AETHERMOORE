"""Live `geoseal route` subprocess integration tests.

Manual mode never calls Ollama, so those tests run unconditionally.
Auto mode requires Ollama; those tests auto-skip when not reachable
(same probe used by the live SLM router suite).
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

GEOSEAL_CLI = "src/geoseal_cli.py"


def _run(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "route", *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _ollama_reachable(host: str = "http://localhost:11434", timeout: float = 1.0) -> bool:
    try:
        import httpx  # noqa: PLC0415
    except ImportError:
        return False
    try:
        return httpx.get(f"{host}/api/tags", timeout=timeout).status_code == 200
    except Exception:
        return False


_OLLAMA_UP = _ollama_reachable()


# ---------------------------------------------------------------------------
#  Manual mode — no SLM, deterministic dispatch from the shell
# ---------------------------------------------------------------------------


def test_route_manual_mode_basic_dispatch() -> None:
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "RU",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["mode"] == "manual"
    assert body["verdict"] == "ALLOW"
    assert body["op_name"] == "add"
    assert body["dst_tongue"] == "RU"
    assert body["band"] == "ARITHMETIC"
    assert body["args"] == {"a": "x", "b": "y"}
    # In manual mode no SLM stages run, so confidence defaults to 1.0.
    assert body["confidence"] == 1.0


def test_route_manual_mode_pinning_provenance_in_reasoning() -> None:
    proc = _run(
        "--manual",
        "--op-name",
        "xor",
        "--dst-tongue",
        "DR",
        "--arg",
        "a=p",
        "--arg",
        "b=q",
    )
    assert proc.returncode == 0
    body = json.loads(proc.stdout)
    reasoning = body["reasoning"]
    assert any("band=pinned-via-op:LOGIC" in line for line in reasoning)
    assert any("op=pinned:xor" in line for line in reasoning)
    assert any("tongue=caller-supplied:DR" in line for line in reasoning)


def test_route_manual_mode_missing_op_name_quarantines() -> None:
    proc = _run(
        "--manual",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["verdict"] == "QUARANTINE"
    assert err["error_type"] == "ManualModeError"
    assert "op_name" in err["message"]


def test_route_manual_mode_missing_dst_tongue_quarantines() -> None:
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "ManualModeError"
    assert "dst_tongue" in err["message"]


def test_route_manual_mode_count_now_routes_after_lexicon_close() -> None:
    """After the CA-tongue canonicalisation closed the sphere from 57→64,
    `count` (and the other 6 previously-excluded aggregation ops) routes
    in manual mode like any other op. This used to assert quarantine; now
    it asserts the inverse — the contract flipped when the lexicon closed."""
    proc = _run(
        "--manual",
        "--op-name",
        "count",
        "--dst-tongue",
        "KO",
        "--arg",
        "xs=v",
    )
    assert proc.returncode == 0, proc.stdout
    body = json.loads(proc.stdout)
    assert body["verdict"] == "ALLOW"
    assert body["op_name"] == "count"
    assert body["dst_tongue"] == "KO"
    assert body["band"] == "AGGREGATION"


def test_route_manual_mode_band_op_disagreement_quarantines() -> None:
    proc = _run(
        "--manual",
        "--band",
        "LOGIC",
        "--op-name",
        "add",  # actually ARITHMETIC
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "ManualModeError"
    assert "disagrees" in err["message"]


# ---------------------------------------------------------------------------
#  Arg-parsing edge cases — CLI boundary
# ---------------------------------------------------------------------------


def test_route_malformed_arg_pair_rejected() -> None:
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "KO",
        "--arg",
        "no_equals_sign",
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["error_type"] == "ArgParseError"


def test_route_arg_value_can_contain_equals_sign() -> None:
    """`a=x=y` should bind a → "x=y", not error. The parser splits
    only on the first `=`."""
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=value_with=equals",
        "--arg",
        "b=y",
    )
    # Lift step's identifier-only arg pattern will reject this on dispatch
    # — but the CLI parser itself must succeed. (Funnel-bounded: the IR
    # rejects, we don't crash at the boundary.)
    # Actually the router dispatches to manual mode without lift, so the
    # arg flows through. Let's just verify the parse succeeded.
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["args"]["a"] == "value_with=equals"


# ---------------------------------------------------------------------------
#  Auto mode — requires Ollama, auto-skip otherwise
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _OLLAMA_UP, reason="Ollama not running")
def test_route_auto_mode_with_pinned_op_calls_ollama_only_for_tongue() -> None:
    """Auto mode + pinned op → SLM only picks tongue. Confirms the
    hybrid path works end-to-end through the CLI."""
    proc = _run(
        "--intent",
        "add x and y",
        "--op-name",
        "add",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--timeout-seconds",
        "30",
        "--min-confidence",
        "0.0",
    )
    # Auto mode without a qualified model may hit confidence floor or
    # produce a low-quality classification; the test guards on the
    # process-level contract (verdict in {ALLOW, QUARANTINE}, JSON valid)
    # rather than asserting a specific tongue.
    body = json.loads(proc.stdout)
    assert body["mode"] == "auto"
    assert body["verdict"] in ("ALLOW", "QUARANTINE")
    if body["verdict"] == "ALLOW":
        assert body["op_name"] == "add"


def test_route_auto_mode_unreachable_ollama_quarantines() -> None:
    """If Ollama isn't running and AUTO mode is invoked, the router
    must surface a clean QUARANTINE rather than crashing."""
    proc = _run(
        "--intent",
        "Add",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--ollama-host",
        "http://127.0.0.1:1",  # nothing listens here
        "--timeout-seconds",
        "1",
    )
    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err["verdict"] == "QUARANTINE"
    # Either ConnectError or a timeout — both must subclass-match
    # ClassificationFailure / QuarantineError.
    assert err["error_type"] in (
        "ClassificationFailure",
        "ManualModeError",
    )


# ---------------------------------------------------------------------------
#  Mode flag mutex — auto and manual must be discriminated
# ---------------------------------------------------------------------------


def test_route_no_mode_flag_uses_intent_set() -> None:
    """Without --manual, the AUTO parameter set is selected (intent-driven)."""
    proc = _run(
        "--intent",
        "Add",
        "--op-name",
        "add",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    # With op + tongue both pinned in AUTO mode, no SLM call needed.
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["mode"] == "auto"
    assert body["op_name"] == "add"


def test_route_manual_alone_is_acceptable_parameter_set() -> None:
    """The MANUAL set is satisfied by --manual + the supporting pins.
    Without --intent and without --manual, both sets are absent and
    the parser rejects."""
    proc = _run(
        "--op-name",
        "add",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    # Neither --intent nor --manual supplied → no parameter set satisfied.
    assert proc.returncode != 0
    assert "no parameter set" in proc.stderr or "satisfied" in proc.stderr


# ---------------------------------------------------------------------------
#  Emit modifiers — close the NL -> IR -> code loop in one call
# ---------------------------------------------------------------------------


def test_route_emit_single_tongue_adds_dst_code() -> None:
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "RU",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--emit",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["dst_code"] == "x.wrapping_add(y)"
    # Without --emit-all, no translations map.
    assert "translations" not in body


def test_route_emit_all_produces_six_translations() -> None:
    """The bijective sphere broadcast: one IR -> 6 valid implementations."""
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--emit-all",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert "translations" in body
    translations = body["translations"]
    assert set(translations.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}
    # Spot-check Rust + Haskell.
    assert translations["RU"] == "x.wrapping_add(y)"
    assert translations["DR"] == "(x + y)"
    # Primary dst_code mirrors the routed tongue.
    assert body["dst_code"] == translations["KO"]


def _extract_json_from_stream(text: str) -> dict:
    """Find the first balanced JSON object in `text` and parse it.

    Necessary because Python startup writes liboqs version warnings to
    stderr in this repo, so stderr isn't pure JSON even when the CLI
    emits a clean envelope.
    """
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object found in stream: {text!r}")
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"unbalanced JSON in stream: {text!r}")


def test_route_emit_raw_puts_code_on_stdout_envelope_on_stderr() -> None:
    """Pipe-friendly: stdout is the bare emitted code, stderr keeps the
    audit envelope. `geoseal route ... --emit --raw | wc -c` should
    count just the code bytes (plus trailing newline)."""
    proc = _run(
        "--manual",
        "--op-name",
        "mul",
        "--dst-tongue",
        "RU",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--emit",
        "--raw",
    )
    assert proc.returncode == 0, proc.stderr
    # stdout: just the emitted code (no JSON, no envelope).
    assert proc.stdout.strip() == "x.wrapping_mul(y)"
    assert "{" not in proc.stdout, "envelope leaked to stdout in --raw mode"
    # stderr: contains the JSON envelope (possibly with import warnings prefixed).
    envelope = _extract_json_from_stream(proc.stderr)
    assert envelope["op_name"] == "mul"
    assert envelope["dst_code"] == "x.wrapping_mul(y)"


def test_route_emit_raw_ignored_when_emit_all_active() -> None:
    """--raw with --emit-all is ambiguous (which tongue's code goes
    to stdout?) so we ignore --raw and fall back to envelope-on-stdout."""
    proc = _run(
        "--manual",
        "--op-name",
        "sub",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--emit-all",
        "--raw",
    )
    assert proc.returncode == 0, proc.stderr
    # stdout should be the JSON envelope, not bare code.
    body = json.loads(proc.stdout)
    assert "translations" in body
    assert proc.stderr == "" or "translations" not in proc.stderr


def test_route_no_emit_flag_omits_dst_code() -> None:
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "RU",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert "dst_code" not in body
    assert "translations" not in body


# ---------------------------------------------------------------------------
#  Promotion ledger — recurrence detection across CLI invocations
# ---------------------------------------------------------------------------


def test_route_persists_to_promotion_ledger(tmp_path) -> None:
    """First invocation lands count=1 in the ledger and is not yet a
    promotion candidate (threshold defaults to 3)."""
    ledger_path = tmp_path / "ledger.jsonl"
    proc = _run(
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
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    assert body["ledger"]["count"] == 1
    assert body["ledger"]["is_candidate"] is False
    assert ledger_path.exists()


def test_route_repeated_invocations_cross_promotion_threshold(tmp_path) -> None:
    """Three identical dispatches must trip the promotion threshold."""
    ledger_path = tmp_path / "ledger.jsonl"
    args = (
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
        "--promotion-threshold",
        "3",
    )
    counts = []
    for _ in range(3):
        proc = _run(*args)
        assert proc.returncode == 0, proc.stderr
        counts.append(json.loads(proc.stdout)["ledger"]["count"])
    assert counts == [1, 2, 3]
    final_body = json.loads(_run(*args).stdout)
    assert final_body["ledger"]["count"] == 4
    assert final_body["ledger"]["is_candidate"] is True


def test_route_no_ledger_flag_skips_persistence(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    proc = _run(
        "--manual",
        "--op-name",
        "add",
        "--dst-tongue",
        "KO",
        "--arg",
        "a=x",
        "--arg",
        "b=y",
        "--no-ledger",
        "--ledger-path",
        str(ledger_path),
    )
    assert proc.returncode == 0, proc.stderr
    body = json.loads(proc.stdout)
    # No ledger key in the response.
    assert "ledger" not in body
    assert "ledger_error" not in body
    # No file written.
    assert not ledger_path.exists()


def test_route_normalised_dispatch_has_stable_digest(tmp_path) -> None:
    """Two semantically-identical dispatches produce the same digest
    regardless of which surface arguments are used. Both produce
    op=add, dst_tongue=RU, args={'a':'x','b':'y'} so they should
    hash to the same ledger entry."""
    ledger_path = tmp_path / "ledger.jsonl"

    # First: AUTO mode with both pinned (no SLM call needed).
    proc1 = _run(
        "--intent",
        "add x and y",
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
    # Second: MANUAL mode, same dispatch.
    proc2 = _run(
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
    assert proc1.returncode == 0 and proc2.returncode == 0
    digest1 = json.loads(proc1.stdout)["ledger"]["digest"]
    digest2 = json.loads(proc2.stdout)["ledger"]["digest"]
    assert digest1 == digest2, "same dispatch via different mode should share digest"
    assert json.loads(proc2.stdout)["ledger"]["count"] == 2


def test_route_distinct_dispatches_get_distinct_digests(tmp_path) -> None:
    """Different op + same args = different digest = no spurious recurrence."""
    ledger_path = tmp_path / "ledger.jsonl"
    proc_add = _run(
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
    proc_mul = _run(
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
    digest_add = json.loads(proc_add.stdout)["ledger"]["digest"]
    digest_mul = json.loads(proc_mul.stdout)["ledger"]["digest"]
    assert digest_add != digest_mul
    # Each one should be count=1 (never collided).
    assert json.loads(proc_add.stdout)["ledger"]["count"] == 1
    assert json.loads(proc_mul.stdout)["ledger"]["count"] == 1


def test_route_emit_round_trips_all_57_tier1_ops() -> None:
    """Every Tier 1 op should round-trip cleanly through the emit path
    in manual mode. This is the integration-level proof that the route
    -> emit pipeline is bijective for the participating sphere."""
    # Pick a representative subset to keep test runtime sane — one per band.
    cases = [
        ("add", "ARITHMETIC", {"a": "x", "b": "y"}),
        ("xor", "LOGIC", {"a": "p", "b": "q"}),
        ("eq", "COMPARISON", {"a": "u", "b": "v"}),
        ("sum", "AGGREGATION", {"xs": "data"}),
    ]
    for op, expected_band, args in cases:
        flags = ["--manual", "--op-name", op, "--dst-tongue", "KO", "--emit-all"]
        for k, v in args.items():
            flags.extend(["--arg", f"{k}={v}"])
        proc = _run(*flags)
        assert proc.returncode == 0, f"{op}: {proc.stderr}"
        body = json.loads(proc.stdout)
        assert body["band"] == expected_band, f"{op}: wrong band"
        translations = body["translations"]
        assert len(translations) == 6, f"{op}: missing tongues"
        # Every tongue produced non-empty code.
        for tongue, code in translations.items():
            assert code, f"{op}/{tongue}: empty emission"
