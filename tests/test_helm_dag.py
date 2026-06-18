"""run_dag: concurrent, converging Helm operator."""

import time

from python.helm import Step, flag, run_dag, run_objective, upstream


def test_independent_steps_run_concurrently():
    def slow(objective, context):
        time.sleep(0.15)
        return {"done": True}

    steps = [Step(f"s{i}", "build", slow) for i in range(3)]
    started = time.perf_counter()
    run = run_dag("x", steps)
    elapsed = time.perf_counter() - started
    assert run.approved == 3 and run.fully_autonomous
    assert elapsed < 0.35, f"steps did not run concurrently (took {elapsed:.2f}s)"


def test_gated_step_waits_for_its_upstream():
    effects = {}
    steps = [
        Step("build", "build", lambda objective, context: {"verified": True}),
        Step(
            "ship",
            "deploy",
            lambda objective, context: effects.setdefault("shipped", context["results"]["build"]["verified"]),
            criteria=(upstream("build", "verified", True),),
        ),
    ]
    run = run_dag("ship it", steps)
    assert effects.get("shipped") is True and run.fully_autonomous
    order = [receipt.step for receipt in run.receipts]
    assert order.index("build") < order.index("ship")


def test_blocked_step_is_denied_not_dropped():
    steps = [Step("ship", "deploy", lambda objective, context: "x", criteria=(flag("ready"),))]
    run = run_dag("x", steps)
    assert run.denied_count == 1 and run.approved == 0
    assert run.receipts[0].status == "denied"


def test_run_is_deterministic():
    def make_steps():
        return [
            Step("a", "build", lambda objective, context: {"v": 1}),
            Step("b", "build", lambda objective, context: {"v": 2}, criteria=(upstream("a", "v", 1),)),
        ]

    assert run_dag("same", make_steps()).chain_digest == run_dag("same", make_steps()).chain_digest
    assert run_dag("same", make_steps()).chain_digest != run_dag("other", make_steps()).chain_digest


def test_failing_step_is_recorded_and_others_still_run():
    def boom(objective, context):
        raise RuntimeError("kaboom")

    steps = [Step("a", "build", lambda objective, context: {"ok": True}), Step("b", "build", boom)]
    run = run_dag("x", steps)
    assert run.approved == 1 and run.failed == 1
    assert next(receipt for receipt in run.receipts if receipt.step == "b").status == "failed"


def test_machine_v2_criteria_still_works():
    steps = [
        Step("a", "build", lambda objective, context: {"ok": True}, criteria=(flag("go"),)),
        Step("b", "verify", lambda objective, context: "B", criteria=(upstream("a", "ok", True),)),
    ]
    run = run_objective("x", steps, context={"go": True})
    assert run.approved == 2 and run.fully_autonomous
