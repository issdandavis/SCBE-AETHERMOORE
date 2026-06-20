"""Tests for Crank — the visible workflow machine (intent -> checkpointed phases -> catalog)."""

from python.crank import Phase, GateVerdict, default_gate, render, turn


def _good_phases():
    return [
        Phase("research", lambda intent, ctx: f"notes:{intent}"),
        Phase("build", lambda intent, ctx: f"impl:{intent}"),
        Phase("review", lambda intent, ctx: f"reviewed:{ctx['outputs']['build']}"),
        Phase("deliver", lambda intent, ctx: {"artifact": ctx["outputs"]["build"], "status": "shipped"}),
    ]


def test_happy_path_produces_full_catalog():
    cat = turn("add a tool", _good_phases())
    assert cat.ok is True
    assert [r.status for r in cat.receipts] == ["ok", "ok", "ok", "ok"]
    assert [r.phase for r in cat.receipts] == ["research", "build", "review", "deliver"]
    assert cat.result == {"artifact": "impl:add a tool", "status": "shipped"}
    # every receipt carries digests + a chain link
    assert all(r.output_digest and r.chain_digest for r in cat.receipts)


def test_run_is_deterministic():
    a = turn("same task", _good_phases())
    b = turn("same task", _good_phases())
    assert a.chain_digest == b.chain_digest
    assert a.to_dict()["receipts"] == b.to_dict()["receipts"]


def test_chain_is_tamper_evident():
    base = turn("task", _good_phases())
    tampered_phases = _good_phases()
    tampered_phases[1] = Phase("build", lambda intent, ctx: f"impl:{intent}!!")  # different build output
    tampered = turn("task", tampered_phases)
    assert tampered.chain_digest != base.chain_digest  # one changed output -> different proof


def test_drift_when_a_phase_produces_nothing():
    phases = [
        Phase("research", lambda intent, ctx: "notes"),
        Phase("build", lambda intent, ctx: ""),  # empty -> drift
        Phase("deliver", lambda intent, ctx: "shipped"),
    ]
    cat = turn("x", phases)
    assert cat.ok is False
    assert [r.status for r in cat.receipts] == ["ok", "drift"]  # stop_on_fail halts the crank
    assert "no output" in cat.receipts[1].note


def test_drift_when_a_phase_raises_does_not_crash_machine():
    def boom(intent, ctx):
        raise RuntimeError("kaboom")

    cat = turn("x", [Phase("research", lambda i, c: "ok"), Phase("build", boom)])
    assert cat.ok is False
    assert cat.receipts[1].status == "drift"
    assert "kaboom" in cat.receipts[1].note


def test_blocked_when_gate_refuses():
    def strict_gate(phase, output):
        if isinstance(output, str) and "secret" in output:
            return GateVerdict(False, "leaks a secret")
        return GateVerdict(True)

    phases = [Phase("research", lambda i, c: "fine"), Phase("build", lambda i, c: "here is the secret key")]
    cat = turn("x", phases, gate=strict_gate)
    assert cat.ok is False
    assert cat.receipts[1].status == "blocked"
    assert "secret" in cat.receipts[1].note


def test_collision_when_phase_repeats_earlier_output():
    phases = [
        Phase("research", lambda i, c: "same"),
        Phase("build", lambda i, c: "same"),  # identical to research -> no progress
    ]
    cat = turn("x", phases)
    assert cat.ok is False
    assert cat.receipts[1].status == "collision"
    assert "research" in cat.receipts[1].note


def test_can_continue_past_failures():
    phases = [
        Phase("a", lambda i, c: ""),  # drift
        Phase("b", lambda i, c: "real"),  # still runs because stop_on_fail=False
    ]
    cat = turn("x", phases, stop_on_fail=False)
    assert [r.status for r in cat.receipts] == ["drift", "ok"]
    assert cat.ok is False  # one drift still fails the run overall


def test_default_gate_rejects_empty():
    assert default_gate("p", "").allow is False
    assert default_gate("p", []).allow is False
    assert default_gate("p", "x").allow is True


def test_render_is_readable():
    text = render(turn("task", _good_phases()))
    assert "crank" in text and "OK" in text and "research: ok" in text
