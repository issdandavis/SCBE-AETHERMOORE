"""Offline tests for strength_router (no models, no network). Mirrors test_failure_map / test_stepwise.

Covers the routing math and the anti-cheat guardrails the design flagged: escalate only where the
cheaper model is known-weak; a block is a narrow per-step primitive (never the whole task); routing
OFF must equal the single-shot baseline (so a "lift" can't be manufactured by the harness itself).
"""

from __future__ import annotations

from python.scbe.failure_map import clears_through, seq_task
from python.scbe.stepwise import Step, build_context
from python.helm.strength_router import (
    Solver,
    block_eligible,
    build_failure_map,
    main,
    measure_routing_lift,
    pre_route,
    routed_proposer,
    run_routed,
)
from python.helm.strength_router_tasks import correct_label, _label_from_state, _match_label, number_task


# ---- pre-routing reads the failure map and escalates ONLY at the weak step --------------------
def test_pre_route_escalates_only_where_small_is_weak():
    task = seq_task("t", ["a", "b", "c"])  # steps s1,s2,s3
    small = Solver("small", "small", proposer=clears_through(1), cost=1)  # clears s1, drifts at s2
    strong = Solver("strong", "strong", proposer=clears_through(9), cost=3)  # clears all
    fmap = build_failure_map([task], [small, strong])
    a = pre_route(task, fmap, [small, strong])
    assert a["s1"].name == "small"  # small clears step 0 -> cheapest stays
    assert a["s2"].name == "strong"  # small drifts at step 1 -> targeted escalation
    assert a["s3"].name == "strong"


def test_block_eligible_only_for_registered_step():
    judge = Step(name="label", key="label", options=lambda st: ["a"], check=lambda st, v: True)
    calc = Step(name="r3", key="r3", calc=lambda st: 0)
    blocks = {"label": Solver("blk", "block", block=lambda st: "a")}
    assert block_eligible(judge, blocks) is not None  # registered for this step's key
    assert block_eligible(calc, blocks) is None  # calc steps are already code, skip
    assert block_eligible(Step(name="other", key="other", options=lambda st: ["a"]), blocks) is None


# ---- composition: per-step dispatch behind the single proposer slot --------------------------
def test_routed_proposer_dispatches_per_step():
    task = seq_task("t", ["a", "b", "c"])
    hits = []
    s_small = Solver("small", "small", proposer=lambda c, o: (hits.append("small"), "a")[1])
    s_strong = Solver("strong", "strong", proposer=lambda c, o: (hits.append("strong"), o[0])[1])
    assignment = {"s1": s_small, "s2": s_strong, "s3": s_strong}
    res = run_routed(task, assignment)
    assert res["completed"] is True
    assert res["solver_mix"] == {"small": 1, "strong": 2, "block": 0, "calc": 0}
    assert "small" in hits and "strong" in hits


def test_block_assigned_step_offloads_to_oracle():
    # a choice step assigned a block (no proposer) -> routed_proposer defers -> auto-offload to oracle
    task = seq_task("t", ["a", "b"])
    s_small = Solver("small", "small", proposer=clears_through(9))  # would clear, but s2 is block-assigned
    s_block = Solver("blk", "block", block=lambda st: "b")  # the correct answer for s2
    assignment = {"s1": s_small, "s2": s_block}
    res = run_routed(task, assignment, max_rewinds=2)
    assert res["completed"] is True
    assert "s2" in res["offloaded"]  # the block rescued the step it was assigned to
    assert res["solver_mix"]["block"] == 1


# ---- ANTI-CHEAT: routing OFF must equal the single-shot baseline ------------------------------
def test_all_small_routing_equals_single_shot():
    tasks = [seq_task("t%d" % i, ["a", "b", "c"]) for i in range(3)]
    small = Solver("small", "small", proposer=clears_through(1), cost=1)  # clears only step 0
    fmap = build_failure_map(tasks, [small])  # only the weak model exists
    rep = measure_routing_lift(tasks, fmap, [small], single_shot=clears_through(1))
    # with no stronger solver, routing can't escalate -> routed == single-shot, no manufactured lift
    assert rep["routed_solved"] == rep["single_solved"]
    assert rep["net_lift"] == 0
    assert rep["solver_mix"]["strong"] == 0


def test_escalation_produces_real_lift_with_visible_mix():
    tasks = [seq_task("t%d" % i, ["a", "b", "c"]) for i in range(4)]
    small = Solver("small", "small", proposer=clears_through(1), cost=1)
    strong = Solver("strong", "strong", proposer=clears_through(9), cost=3)
    fmap = build_failure_map(tasks, [small, strong])
    rep = measure_routing_lift(tasks, fmap, [small, strong], single_shot=clears_through(1))
    assert rep["single_solved"] == 0  # lone weak model clears nothing past s1
    assert rep["routed_solved"] == 4  # escalation rescues the deep steps
    assert rep["net_lift"] == 4
    assert rep["solver_mix"]["small"] > 0 and rep["solver_mix"]["strong"] > 0  # both used, mix visible


# ---- build_context format pin (routed_proposer depends on it) ---------------------------------
def test_routed_proposer_recovers_step_name_from_live_context():
    task = seq_task("t", ["a", "b", "c"])
    step = task.steps[1]  # s2
    ctx = build_context(task, {}, step, ["b", "x", "y"], [])
    got = {}
    assignment = {"s2": Solver("x", "small", proposer=lambda c, o: (got.setdefault("dispatched", True), "b")[1])}
    routed_proposer(assignment)(ctx, ["b", "x", "y"])
    assert got.get("dispatched") is True  # parsed 's2' out of the live build_context output


# ---- the GPU task family's pure logic (truth + parsing), no model ------------------------------
def test_fizzbuzz_truth_and_block_offload_logic():
    assert correct_label(15) == "FizzBuzz" and correct_label(9) == "Fizz"
    assert correct_label(10) == "Buzz" and correct_label(7) == "none"
    # the block computes r3/r5; the label is then deterministic from them
    assert _label_from_state({"r3": 0, "r5": 0}) == "FizzBuzz"
    assert _label_from_state({"r3": 1, "r5": 0}) == "Buzz"
    # number_task: r3/r5 are calc blocks (run in code), label is the only choice step
    t = number_task(30)
    kinds = [("calc" if s.is_calc() else "choice") for s in t.steps]
    assert kinds == ["calc", "calc", "choice"]


def test_match_label_parsing():
    assert _match_label("The answer is FizzBuzz.") == "FizzBuzz"
    assert _match_label("fizz") == "Fizz"
    assert _match_label("I think Buzz") == "Buzz"
    assert _match_label("none of them") == "none"
    assert _match_label("fizz and buzz") == "FizzBuzz"  # both -> FizzBuzz


def test_control_cli_routes_to_fair_attribution(monkeypatch, capsys):
    import python.helm.strength_router_tasks as tasks

    seen = {}

    def fake_control(n=20, model="qwen2.5-coder:1.5b", start=1000):
        seen.update({"n": n, "model": model, "start": start})
        return "FAIR_CONTROL_SENTINEL"

    monkeypatch.setattr(tasks, "run_control_groups", fake_control)
    assert main(["--control", "--n", "7", "--model", "tiny-local"]) == 0
    assert seen == {"n": 7, "model": "tiny-local", "start": 1000}
    assert "FAIR_CONTROL_SENTINEL" in capsys.readouterr().out
