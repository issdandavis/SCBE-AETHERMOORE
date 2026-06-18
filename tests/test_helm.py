"""Tests for Helm — criteria-based approval (meets criteria -> approved -> runs)."""

from python.helm import Step, flag, human, met, render, run_objective, upstream


def test_no_criteria_runs_unconditionally():
    fx = {}
    run = run_objective("x", [Step("a", "build", lambda o, c: fx.setdefault("a", True))])
    assert fx == {"a": True} and run.approved == 1 and run.fully_autonomous


def test_met_criteria_approve_and_run():
    fx = {}
    step = Step(
        "deploy", "deploy", lambda o, c: fx.setdefault("deployed", True), criteria=(met("ready", lambda o, c, s: True),)
    )
    run = run_objective("x", [step])
    assert fx.get("deployed") is True
    assert run.receipts[0].status == "approved"


def test_unmet_criteria_deny_and_do_not_run():
    fx = {}
    step = Step(
        "deploy",
        "deploy",
        lambda o, c: fx.setdefault("deployed", True),
        criteria=(met("ready", lambda o, c, s: False),),
    )
    run = run_objective("x", [step])
    assert "deployed" not in fx  # the action never fired
    assert run.denied_count == 1 and run.approved == 0
    r = run.receipts[0]
    assert r.status == "denied" and "ready" in r.reason


def test_upstream_criterion_gates_on_an_earlier_result():
    fx = {}
    steps = [
        Step("build", "build", lambda o, c: {"verified": True}),
        Step(
            "deploy",
            "deploy",
            lambda o, c: fx.setdefault("shipped", True),
            criteria=(upstream("build", "verified", True),),
        ),
    ]
    run = run_objective("ship", steps)
    assert fx.get("shipped") is True and run.fully_autonomous

    # now make the build NOT verify -> deploy must be denied, must not ship
    fx2 = {}
    steps[0] = Step("build", "build", lambda o, c: {"verified": False})
    steps[1] = Step(
        "deploy",
        "deploy",
        lambda o, c: fx2.setdefault("shipped", True),
        criteria=(upstream("build", "verified", True),),
    )
    run2 = run_objective("ship", steps)
    assert "shipped" not in fx2 and run2.denied_count == 1


def test_flag_criterion_from_context():
    step = Step("deploy", "deploy", lambda o, c: "shipped", criteria=(flag("within_budget"),))
    assert run_objective("x", [step]).denied_count == 1  # flag absent -> denied
    assert run_objective("x", [step], context={"within_budget": True}).approved == 1  # flag set -> approved


def test_human_criterion_is_just_a_context_signal():
    step = Step("charge", "spend", lambda o, c: "charged", criteria=(human("approved_spend"),))
    assert run_objective("x", [step]).denied_count == 1  # no human signal -> denied
    assert run_objective("x", [step], context={"approved_spend": True}).approved == 1


def test_failing_action_is_recorded_and_loop_continues():
    def boom(o, c):
        raise RuntimeError("kaboom")

    fx = {}
    steps = [
        Step("a", "build", lambda o, c: fx.setdefault("a", True)),
        Step("b", "build", boom),
        Step("c", "build", lambda o, c: fx.setdefault("c", True)),
    ]
    run = run_objective("x", steps)
    assert fx == {"a": True, "c": True} and run.failed == 1 and run.approved == 2
    assert next(r for r in run.receipts if r.step == "b").status == "failed"


def test_criterion_that_errors_is_treated_as_not_met():
    def explode(o, c, s):
        raise ValueError("bad check")

    step = Step("deploy", "deploy", lambda o, c: "shipped", criteria=(met("boom", explode),))
    run = run_objective("x", [step])
    assert run.denied_count == 1 and run.receipts[0].status == "denied"


def test_run_is_deterministic_and_chain_tamper_evident():
    steps = [Step("a", "build", lambda o, c: "A"), Step("b", "verify", lambda o, c: "B")]
    assert run_objective("same", steps).chain_digest == run_objective("same", steps).chain_digest
    assert run_objective("other", steps).chain_digest != run_objective("same", steps).chain_digest


def test_render_marks_autonomous_and_denials():
    steps = [
        Step("build", "build", lambda o, c: {"verified": True}),
        Step("deploy", "deploy", lambda o, c: "x", criteria=(upstream("build", "verified", False),)),
    ]
    text = render(run_objective("x", steps))
    assert "denied" in text and "deploy" in text
