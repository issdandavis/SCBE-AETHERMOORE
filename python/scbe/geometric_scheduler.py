"""
Geometric scheduler - a real dispatcher built on the tangentialism router.
===========================================================================

The successor to the juggling scheduler: instead of physics-of-throws, it routes
live work to a fleet through the tongue-weighted hyperbolic manifold
([[geometric_router]]). It actually DISPATCHES - spawns worker threads, executes
job callables concurrently, handles failures, and reports real wall-clock makespan.

Design = pull-based affinity work-stealing, hardened after an adversarial review:
  * (perf) all (worker, job) Finsler costs are precomputed ONCE outside the lock,
    and each worker drains its own min-heap - the lock only does O(1) claim/recheck,
    never an O(jobs) metric scan. Each worker's tongue scale is cached (immutable).
  * (affinity) a worker prefers the job it is cheapest at;
  * (anti-over-steal) a worker only TAKES a job it isn't the global-cheapest for
    after that job has been deferred DEFER_CAP times - giving the right specialist
    first refusal, so an idle generalist doesn't grab a specialist's cheap work;
  * (anti-starvation) the defer cap guarantees every job is eventually claimed;
  * (back-pressure) a busy worker simply isn't pulling - the fluid term, for free;
  * (failure) a job that raises is re-queued up to max_retries, then recorded in
    SchedReport.errors. Job names must be unique (validated) so results never collide.

Fleets are modeled as I/O-bound (agents waiting on model/API/tool latency), so
threads give true concurrency and an agent takes LONGER on off-affinity work
(latency penalty grows with Finsler distance). Plug a real `work` callable into a
Job to dispatch actual work; omit it and the scheduler models latency.
"""

from __future__ import annotations

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from python.scbe.geometric_router import (
    Agent, TONGUES, agent_scale, finsler_scaled,
)


@dataclass
class Job:
    name: str
    profile: Any                       # tongue profile (dict or 6-vec)
    work: Optional[Callable[[float], Any]] = None  # work(penalty) -> result
    base: float = 0.01                 # base latency units (seconds, demo scale)


@dataclass
class Worker(Agent):
    """An Agent that can also do work (inherits tongue identity + manifold pos)."""
    _scale: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def scale(self) -> np.ndarray:
        if self._scale is None:
            self._scale = agent_scale(self.tongue)   # cache immutable per-axis scale
        return self._scale


@dataclass
class SchedReport:
    mode: str
    wall: float
    makespan: float
    assignments: Dict[str, List[str]]
    busy: Dict[str, float]
    done: int
    failed: int
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[Tuple[str, str]] = field(default_factory=list)


def _execute(worker: Worker, job: Job) -> Any:
    pen = 1.0 + finsler_scaled(worker.scale, worker.pos, job.profile)
    if job.work is not None:
        return job.work(pen)
    serve = getattr(worker, "serve", None)   # a model/agent worker serves the job itself
    if serve is not None:
        return serve(job, pen)
    time.sleep(job.base * pen)               # else model generic agent latency (I/O-bound)
    return f"{job.name}@{worker.name}"


class GeometricScheduler:
    """Concurrent fleet dispatcher with geometric (or round-robin) routing."""

    def __init__(self, workers: Sequence[Worker], max_retries: int = 2):
        if not workers:
            raise ValueError("need at least one worker")
        self.workers = list(workers)
        self.max_retries = max_retries

    def run(self, jobs: Sequence[Job], mode: str = "geometric") -> SchedReport:
        jobs = list(jobs)
        names = [j.name for j in jobs]
        if len(names) != len(set(names)):
            raise ValueError("job names must be unique (results are keyed by name)")
        W = self.workers
        nW, nJ = len(W), len(jobs)

        busy: Dict[str, float] = {w.name: 0.0 for w in W}
        assigned: Dict[str, List[str]] = {w.name: [] for w in W}
        results: Dict[str, Any] = {}
        errors: List[Tuple[str, str]] = []
        if nJ == 0:
            return SchedReport(mode, 0.0, 0.0, assigned, busy, 0, 0, results, errors)

        # precompute every (worker, job) Finsler cost ONCE, outside the lock
        cost = np.empty((nW, nJ))
        for wi, w in enumerate(W):
            for ji, j in enumerate(jobs):
                cost[wi, ji] = finsler_scaled(w.scale, w.pos, j.profile)
        best = cost.argmin(axis=0)               # job -> index of its cheapest worker
        defer_cap = max(1, nW // 2)

        available = set(range(nJ))
        defers = [0] * nJ
        retries = [0] * nJ
        lock = threading.Lock()

        static: Dict[int, List[int]] = {}
        if mode == "round_robin":
            static = {wi: list(range(wi, nJ, nW)) for wi in range(nW)}

        def loop(wi: int) -> None:
            w = W[wi]
            heap = [(cost[wi, ji], ji) for ji in range(nJ)] if mode == "geometric" else None
            if heap is not None:
                heapq.heapify(heap)
            rr = list(static.get(wi, [])) if mode == "round_robin" else None
            rr_i = 0
            while True:
                idx = None
                with lock:
                    if not available:
                        return
                    if mode == "round_robin":
                        while rr_i < len(rr):
                            ji = rr[rr_i]
                            rr_i += 1
                            if ji in available:
                                available.discard(ji)
                                idx = ji
                                break
                        if idx is None:
                            return
                    else:
                        deferred = []
                        while heap:
                            c, ji = heapq.heappop(heap)
                            if ji not in available:
                                continue
                            if best[ji] == wi:
                                available.discard(ji)
                                idx = ji
                                break
                            # a non-specialist takes a deferred job only if it isn't
                            # drastically worse at it (ratio guard) - protects semantic
                            # routing (a strongly-KO job won't land on a DR model) -
                            # unless the job is badly starved (hard cap forces progress).
                            ratio = cost[wi, ji] / max(cost[best[ji], ji], 1e-9)
                            if (defers[ji] >= defer_cap and ratio <= 4.0) \
                                    or defers[ji] >= defer_cap * 4:
                                available.discard(ji)
                                idx = ji
                                break
                            defers[ji] += 1               # let the specialist take it first
                            deferred.append((c, ji))
                        for item in deferred:
                            heapq.heappush(heap, item)
                if idx is None:
                    # nothing claimable yet (all deferred to specialists) - yield, retry
                    time.sleep(0.0005)
                    continue
                job = jobs[idx]
                t0 = time.perf_counter()
                try:
                    res = _execute(w, job)
                except Exception as exc:  # noqa: BLE001 - re-route on any failure
                    with lock:
                        retries[idx] += 1
                        if retries[idx] <= self.max_retries:
                            available.add(idx)
                            if heap is not None:
                                heapq.heappush(heap, (cost[wi, idx], idx))
                        else:
                            errors.append((job.name, str(exc)))
                    continue
                dt = time.perf_counter() - t0
                with lock:
                    busy[w.name] += dt
                    assigned[w.name].append(job.name)
                    results[job.name] = res

        t0 = time.perf_counter()
        threads = [threading.Thread(target=loop, args=(wi,), name=W[wi].name)
                   for wi in range(nW)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall = time.perf_counter() - t0
        return SchedReport(
            mode=mode, wall=wall, makespan=max(busy.values()) if busy else 0.0,
            assignments=assigned, busy=busy,
            done=sum(len(v) for v in assigned.values()), failed=len(errors),
            results=results, errors=errors,
        )


class StreamScheduler:
    """Online geometric scheduler - jobs arrive over time, workers run continuously.

    Two routing policies, the user's dual-topology:
      * phi   - smooth contraction: each free worker pulls the job it is cheapest at
                (affinity routing) - efficient steady-state flow.
      * purge - periodic Collatz-style shedding: every `purge_every` claims, a worker
                instead grabs the OLDEST waiting job regardless of affinity, clearing
                backlog/clog so no job ages out (snake-skin shedding of the queue).

    submit() can be called from any thread while running; close() stops intake and
    lets workers drain; join() returns the SchedReport.
    """

    def __init__(self, workers: Sequence[Worker], max_retries: int = 2,
                 purge_every: int = 0):
        if not workers:
            raise ValueError("need at least one worker")
        self.workers = list(workers)
        self.max_retries = max_retries
        self.purge_every = purge_every          # 0 = pure phi, no purge passes
        self._cv = threading.Condition()
        self._jobs: Dict[int, Job] = {}         # jid -> job (waiting)
        self._cost: Dict[int, np.ndarray] = {}  # jid -> per-worker cost row
        self._order = 0                          # submit sequence (age)
        self._jid = 0
        self._retries: Dict[int, int] = {}
        self._closed = False
        self._threads: List[threading.Thread] = []
        self.busy = {w.name: 0.0 for w in self.workers}
        self.assigned = {w.name: [] for w in self.workers}
        self.results: Dict[str, Any] = {}
        self.errors: List[Tuple[str, str]] = []
        self._completed = 0
        self._wall_start = None
        self._started = False
        self._names: set = set()

    def submit(self, job: Job) -> None:
        with self._cv:
            if self._closed:
                raise RuntimeError("scheduler is closed")
            if job.name in self._names:
                raise ValueError(f"duplicate job name {job.name!r}")
            self._names.add(job.name)
            jid = self._jid
            self._jid += 1
            self._jobs[jid] = job
            self._cost[jid] = np.array(
                [finsler_scaled(w.scale, w.pos, job.profile) for w in self.workers])
            self._jobs[jid]._order = self._order  # type: ignore[attr-defined]
            self._order += 1
            self._retries[jid] = 0
            self._cv.notify_all()

    def _claim(self, wi: int) -> Optional[int]:
        """Pick a waiting job for worker wi (caller holds the lock). None if none."""
        if not self._jobs:
            return None
        # purge fires off COMPLETED jobs, not claim attempts (which include empties)
        purge = self.purge_every and (self._completed % self.purge_every == self.purge_every - 1)
        if purge:
            jid = min(self._jobs, key=lambda j: getattr(self._jobs[j], "_order", j))
        else:
            jid = min(self._jobs, key=lambda j: self._cost[j][wi])
        return jid

    def _loop(self, wi: int) -> None:
        w = self.workers[wi]
        while True:
            with self._cv:
                while not self._jobs and not self._closed:
                    self._cv.wait()
                if not self._jobs and self._closed:
                    return
                jid = self._claim(wi)
                if jid is None:
                    continue
                job = self._jobs.pop(jid)
                cost_row = self._cost.pop(jid)
            t0 = time.perf_counter()
            try:
                res = _execute(w, job)
            except Exception as exc:  # noqa: BLE001
                with self._cv:
                    self._retries[jid] += 1
                    if self._retries[jid] <= self.max_retries:
                        self._jobs[jid] = job          # re-queue live
                        self._cost[jid] = cost_row
                        self._cv.notify_all()
                    else:
                        self.errors.append((job.name, str(exc)))
                continue
            dt = time.perf_counter() - t0
            with self._cv:
                self.busy[w.name] += dt
                self.assigned[w.name].append(job.name)
                self.results[job.name] = res
                self._completed += 1

    def start(self) -> "StreamScheduler":
        self._started = True
        self._wall_start = time.perf_counter()
        self._threads = [threading.Thread(target=self._loop, args=(wi,), name=w.name)
                         for wi, w in enumerate(self.workers)]
        for t in self._threads:
            t.start()
        return self

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._cv.notify_all()

    def join(self) -> SchedReport:
        if not self._started:
            raise RuntimeError("start() must be called before join()")
        for t in self._threads:
            t.join()
        wall = time.perf_counter() - self._wall_start if self._wall_start else 0.0
        return SchedReport(
            mode=f"stream/{'purge' if self.purge_every else 'phi'}",
            wall=wall, makespan=max(self.busy.values()) if self.busy else 0.0,
            assignments=self.assigned, busy=self.busy,
            done=sum(len(v) for v in self.assigned.values()), failed=len(self.errors),
            results=self.results, errors=self.errors,
        )


def _demo() -> None:
    import random
    rng = random.Random(7)
    fleet = [Worker(f"{t}-agent", {t: 1.0}) for t in TONGUES]
    jobs = []
    for i in range(120):
        dom = TONGUES[rng.randrange(6)]
        prof = {t: (1.0 if t == dom else 0.15 * rng.random()) for t in TONGUES}
        jobs.append(Job(f"job{i:03d}", prof, base=0.006))

    sched = GeometricScheduler(fleet)
    print("Geometric scheduler - real concurrent dispatch (I/O-bound fleet, hardened)\n")
    print(f"  fleet: {len(fleet)} agents   jobs: {len(jobs)} (heterogeneous, one-tongue-flavored)\n")
    rr = sched.run(jobs, mode="round_robin")
    ge = sched.run(jobs, mode="geometric")
    for r in (rr, ge):
        loads = " ".join(f"{n.split('-')[0]}:{len(v)}" for n, v in r.assignments.items())
        print(f"  {r.mode:<12} wall {r.wall:5.2f}s  makespan {r.makespan:5.2f}s  "
              f"done {r.done}/{len(jobs)} fail {r.failed}")
        print(f"               loads  {loads}")
    print(f"\n  geometric wall-clock {100 * (1 - ge.wall / rr.wall):.0f}% faster, "
          f"makespan {100 * (1 - ge.makespan / rr.makespan):.0f}% lower (real dispatch)")
    print("  precomputed costs + per-worker heaps (no Finsler under lock); best-worker")
    print("  preference + defer-cap stops over-stealing and starvation.")


if __name__ == "__main__":
    _demo()
