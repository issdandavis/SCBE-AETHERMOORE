"""Tests for Helm — the operator loop (AI runs reversible work, humans approve gates)."""

from python.helm import Step, default_policy, render, run_objective


def _steps(side_effects):
    """A realistic objective: research/build/verify are autonomous; deploy + charge are gated.
    `side_effects` is a dict the actions flip so we can prove what actually ran."""

    def mark(name):
        def action(obj, ctx):
            side_effects[name] = True
            return f"{name}:{obj}"

        return action

    return [
        Step("research", "research", mark("research")),
        Step("build", "build", mark("build")),
        Step("verify", "verify", mark("verify")),
        Step("deploy", "deploy", mark("deploy")),  # gated
        Step("charge", "spend", mark("charge")),  # gated
    ]


def test_autonomous_steps_run_gated_steps_are_parked():
    fx = {}
    run = run_objective("ship the tool", _steps(fx))
    # the reversible work ran
    assert fx == {"research": True, "build": True, "verify": True}
    # the gated work did NOT run — it's queued, not executed
    assert "deploy" not in fx and "charge" not in fx
    assert run.autonomous_done == 3 and run.pending_approval == 2
    assert run.needs_human is True
    assert {q["step"] for q in run.approval_queue} == {"deploy", "charge"}


def test_approval_lets_a_gated_step_execute():
    fx = {}
    run = run_objective("ship the tool", _steps(fx), approvals={"deploy"})
    assert fx.get("deploy") is True  # deploy ran because it was approved
    assert "charge" not in fx  # charge still parked
    assert run.approved_done == 1 and run.pending_approval == 1
    deploy = next(r for r in run.receipts if r.step == "deploy")
    assert deploy.status == "approved-done"


def test_irreversible_step_is_gated_even_if_kind_is_benign():
    fx = {}
    steps = [Step("rewrite_history", "edit", lambda o, c: fx.setdefault("ran", True), reversible=False)]
    run = run_objective("x", steps)
    assert "ran" not in fx and run.pending_approval == 1
    assert "irreversible" in run.approval_queue[0]["reason"]


def test_failing_autonomous_step_does_not_abort_the_run():
    def boom(obj, ctx):
        raise RuntimeError("kaboom")

    fx = {}
    steps = [
        Step("a", "build", lambda o, c: fx.setdefault("a", True)),
        Step("b", "build", boom),
        Step("c", "build", lambda o, c: fx.setdefault("c", True)),
    ]
    run = run_objective("x", steps)
    assert fx == {"a": True, "c": True}  # c still ran after b failed
    assert run.failed == 1 and run.autonomous_done == 2
    assert next(r for r in run.receipts if r.step == "b").status == "failed"


def test_run_is_deterministic_and_chain_tamper_evident():
    a = run_objective("same", _steps({}))
    b = run_objective("same", _steps({}))
    assert a.chain_digest == b.chain_digest
    # a different objective -> different chain (the receipt chain reflects the run)
    c = run_objective("different", _steps({}))
    assert c.chain_digest != a.chain_digest


def test_default_policy_classifies_correctly():
    assert default_policy(Step("x", "build", lambda o, c: None)).gated is False
    assert default_policy(Step("x", "verify", lambda o, c: None)).gated is False
    for kind in ("spend", "deploy", "legal", "destructive", "admin", "credential", "publish"):
        assert default_policy(Step("x", kind, lambda o, c: None)).gated is True


def test_later_steps_see_earlier_results():
    steps = [
        Step("a", "build", lambda o, c: "A"),
        Step("b", "verify", lambda o, c: f"saw:{c['results']['a']}"),
    ]
    run = run_objective("x", steps)
    assert run.results["b"] == "saw:A"


def test_render_surfaces_the_queue():
    text = render(run_objective("ship", _steps({})))
    assert "AWAITING YOU" in text and "APPROVAL QUEUE" in text
    assert "deploy" in text and "charge" in text
