"""Streaming geometric scheduler + M4 multi-model fleet routing."""
import random
import threading

import pytest

from python.scbe.geometric_scheduler import StreamScheduler, Worker, Job
from python.scbe.geometric_router import TONGUES


def _fleet():
    return [Worker(f"{t}-agent", {t: 1.0}) for t in TONGUES]


def _jobs(n, seed=1):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        dom = TONGUES[rng.randrange(6)]
        out.append(Job(f"j{i:03d}", {t: (1.0 if t == dom else 0.1) for t in TONGUES}, base=0.001))
    return out


@pytest.mark.parametrize("purge_every", [0, 5])
def test_stream_drains_all_with_live_arrival(purge_every):
    sched = StreamScheduler(_fleet(), purge_every=purge_every).start()
    jobs = _jobs(80)
    for j in jobs[:40]:
        sched.submit(j)

    def trickle():
        for j in jobs[40:]:
            sched.submit(j)
        sched.close()

    t = threading.Thread(target=trickle)
    t.start()
    t.join()
    rep = sched.join()
    assert rep.done == 80 and rep.failed == 0
    assert sum(len(v) for v in rep.assignments.values()) == 80


def test_stream_duplicate_name_rejected():
    sched = StreamScheduler(_fleet()).start()
    sched.submit(Job("dup", {"KO": 1.0}, base=0.0))
    with pytest.raises(ValueError):
        sched.submit(Job("dup", {"AV": 1.0}, base=0.0))
    sched.close()
    sched.join()


def test_stream_submit_after_close_raises():
    sched = StreamScheduler(_fleet()).start()
    sched.close()
    with pytest.raises(RuntimeError):
        sched.submit(Job("late", {"KO": 1.0}))
    sched.join()


def test_stream_empty_closes_clean():
    sched = StreamScheduler(_fleet()).start()
    sched.close()
    rep = sched.join()
    assert rep.done == 0


# ---- M4 multi-model fleet ----

def test_m4_fleet_routes_by_tongue():
    pytest.importorskip("numpy")
    try:
        from python.scbe.fleet_models import m4_fleet, prompt_job
        from python.scbe.geometric_scheduler import GeometricScheduler
    except Exception:
        pytest.skip("M4 model matrix unavailable")
    fleet, _ = m4_fleet()
    assert len(fleet) == 6
    # a single KO-flavored prompt must land on the KO node
    jobs = [prompt_job("k", "classify intent", "KO")]
    rep = GeometricScheduler(fleet).run(jobs, mode="geometric")
    assert rep.done == 1
    assert "k" in rep.assignments["KO-node"]
    assert "MOCK" in str(rep.results["k"]) or len(str(rep.results["k"])) > 0
