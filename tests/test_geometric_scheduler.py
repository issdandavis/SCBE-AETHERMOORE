"""Geometric scheduler — real concurrent dispatch via manifold routing."""
import threading

import pytest

from python.scbe.geometric_scheduler import GeometricScheduler, Job, Worker
from python.scbe.geometric_router import TONGUES


def _fleet():
    return [Worker(f"{t}-agent", {t: 1.0}) for t in TONGUES]


def _hetero_jobs(n=60, seed=5):
    import random
    rng = random.Random(seed)
    jobs = []
    for i in range(n):
        # random dominant tongue (NOT i%6 — that would make round-robin accidentally optimal)
        dom = TONGUES[rng.randrange(6)]
        prof = {t: (1.0 if t == dom else 0.1) for t in TONGUES}
        jobs.append(Job(f"job{i:03d}", prof, base=0.002))
    return jobs


def test_all_jobs_complete():
    sched = GeometricScheduler(_fleet())
    jobs = _hetero_jobs(60)
    r = sched.run(jobs, mode="geometric")
    assert r.done == 60 and r.failed == 0
    assert sum(len(v) for v in r.assignments.values()) == 60


def test_geometric_makespan_not_worse_than_round_robin():
    sched = GeometricScheduler(_fleet())
    jobs = _hetero_jobs(60)
    rr = sched.run(jobs, mode="round_robin")
    ge = sched.run(jobs, mode="geometric")
    # affinity routing must not make the busiest lane worse than count-balanced RR
    assert ge.makespan <= rr.makespan + 1e-6


def test_failure_is_rerouted_then_succeeds():
    flips = {"n": 0}
    lock = threading.Lock()

    def flaky(_penalty):
        with lock:
            flips["n"] += 1
            if flips["n"] == 1:
                raise RuntimeError("transient")
        return "ok"

    fleet = _fleet()
    for w in fleet:
        w.max_retries = 3
    jobs = [Job("flaky", {"KO": 1.0}, work=flaky, base=0.0)]
    r = GeometricScheduler(fleet).run(jobs, mode="geometric")
    assert r.done == 1 and r.failed == 0


def test_real_work_callable_runs():
    out = []

    def work(_pen):
        out.append(1)
        return "done"

    jobs = [Job(f"j{i}", {"CA": 1.0}, work=work, base=0.0) for i in range(10)]
    r = GeometricScheduler(_fleet()).run(jobs, mode="geometric")
    assert r.done == 10 and len(out) == 10


def test_edge_empty_and_single_worker():
    assert GeometricScheduler(_fleet()).run([], mode="geometric").done == 0
    solo = [Worker("solo", {"KO": 1.0})]
    r = GeometricScheduler(solo).run(_hetero_jobs(8), mode="geometric")
    assert r.done == 8


def test_needs_workers():
    with pytest.raises(ValueError):
        GeometricScheduler([])


def test_duplicate_job_names_rejected():
    jobs = [Job("dup", {"KO": 1.0}), Job("dup", {"AV": 1.0})]
    with pytest.raises(ValueError):
        GeometricScheduler(_fleet()).run(jobs)


def test_permanent_failure_recorded_not_in_results():
    def always_fail(_pen):
        raise RuntimeError("boom")

    jobs = [Job("bad", {"KO": 1.0}, work=always_fail, base=0.0)]
    r = GeometricScheduler(_fleet(), max_retries=2).run(jobs)
    assert r.failed == 1 and r.done == 0
    assert "bad" not in r.results
    assert r.errors and r.errors[0][0] == "bad"


def test_no_starvation_balanced_jobs():
    # jobs equally far from every specialist must still all complete (defer-cap)
    fleet = _fleet()
    jobs = [Job(f"b{i}", {t: 0.5 for t in TONGUES}, base=0.001) for i in range(20)]
    r = GeometricScheduler(fleet).run(jobs, mode="geometric")
    assert r.done == 20 and r.failed == 0
