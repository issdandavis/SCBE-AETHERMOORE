#!/usr/bin/env python3
"""
Rubik's-Cube Coding System — speed benchmark.
=============================================

Measures how fast the cube turns one binary/opcode CORE into compilable source
across all language FACES. The "build speed" of the polyglot system: given N
CA-opcode programs, emit each to all registered languages and report throughput
(programs/s, language-files/s, lines/s, chars/s), plus a correctness spot-check.

Pure-Python + stdlib so it runs anywhere — including a Kaggle kernel (free CPU).
Run:  python scripts/benchmark/rubix_cube_speed_benchmark.py [--programs N] [--len L]
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe import polyglot as P  # noqa: E402

# scalar ops by stack arity (keep generated programs shape-valid / compilable)
_BIN = [o for o in (set(P.BINOPS) | set(P.CMPS) | P.FUNC2) if o in P.SCALAR_OPS]
_UN = [o for o in P.FUNC1 if o in P.SCALAR_OPS]


def random_program(length: int, rng: random.Random) -> list:
    """A shape-valid op sequence over a depth-3 seed stack (never underflows)."""
    depth, ops = 3, []
    for _ in range(length):
        if depth >= 2 and (depth <= 1 or rng.random() < 0.6):
            ops.append(rng.choice(_BIN))
            depth -= 1  # pop2 push1
        else:
            ops.append(rng.choice(_UN))  # pop1 push1 (depth unchanged)
        if depth < 1:
            depth = 1
    return P.program_bytes(*ops)


def run(n_programs: int, prog_len: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    langs = P.languages()
    programs = [random_program(prog_len, rng) for _ in range(n_programs)]

    t0 = time.perf_counter()
    files = lines = chars = 0
    for prog in programs:
        for lang in langs:
            src = P.emit(prog, lang, runnable=True)
            files += 1
            lines += src.count("\n") + 1
            chars += len(src)
    dt = time.perf_counter() - t0

    return {
        "languages": len(langs),
        "programs": n_programs,
        "prog_len": prog_len,
        "files_emitted": files,
        "seconds": dt,
        "programs_per_s": n_programs / dt,
        "files_per_s": files / dt,
        "kloc_per_s": (lines / 1000) / dt,
        "mchars_per_s": (chars / 1e6) / dt,
        "total_lines": lines,
    }


# --- parallelism + tangentialism (geometric routing of work to workers) -----


def _emit_chunk(packed):
    """Worker: emit a chunk of programs to all languages (top-level = picklable)."""
    progs, langs = packed
    f = li = c = 0
    for p in progs:
        for lang in langs:
            s = P.emit(p, lang, runnable=True)
            f += 1
            li += s.count("\n") + 1
            c += len(s)
    return f, li, c


# scalar ops carry a tongue flavor: comparisons -> KO (control), math -> CA.
_OP_TONGUE = {}
for _o in P.CMPS:
    _OP_TONGUE[_o] = "KO"
for _o in set(P.BINOPS) | P.FUNC2 | P.FUNC1:
    _OP_TONGUE.setdefault(_o, "CA")


def _prog_profile(ops):
    prof = {"KO": 0.0, "AV": 0.0, "RU": 0.0, "CA": 0.0, "UM": 0.0, "DR": 0.0}
    for o in ops:
        prof[_OP_TONGUE.get(o, "CA")] += 1.0
    s = sum(prof.values()) or 1.0
    return {k: v / s for k, v in prof.items()}


def _geometric_split(programs, workers):
    """Route programs to worker-agents through the tongue manifold (tangent tracks)."""
    from python.scbe.geometric_router import Agent, Task, route_fleet, TONGUES

    agents = [Agent(f"w{i}", {TONGUES[i % 6]: 1.0}) for i in range(workers)]
    tasks = [Task(str(i), _prog_profile(programs[i])) for i in range(len(programs))]
    routes = route_fleet(agents, tasks, pressure=0.5, tour=False)
    chunks = [[programs[int(name)] for name in r.tasks] for r in routes]
    return [c for c in chunks if c]


def run_parallel(n_programs, prog_len, workers, geometric=False, seed=7):
    import multiprocessing as mp

    rng = random.Random(seed)
    langs = P.languages()
    programs = [random_program(prog_len, rng) for _ in range(n_programs)]
    if geometric:
        chunks = _geometric_split(programs, workers)
    else:
        chunks = [programs[i::workers] for i in range(workers)]
    t0 = time.perf_counter()
    with mp.Pool(workers) as pool:
        results = pool.map(_emit_chunk, [(c, langs) for c in chunks])
    dt = time.perf_counter() - t0
    files = sum(r[0] for r in results)
    lines = sum(r[1] for r in results)
    return {
        "workers": workers,
        "geometric": geometric,
        "languages": len(langs),
        "programs": n_programs,
        "files_emitted": files,
        "seconds": dt,
        "programs_per_s": n_programs / dt,
        "files_per_s": files / dt,
        "kloc_per_s": lines / 1000 / dt,
        "chunk_sizes": [len(c) for c in chunks],
    }


def spot_check(seed: int = 7) -> dict:
    """Confirm correctness isn't sacrificed for speed: python emit runs correctly."""
    rng = random.Random(seed)
    prog = random_program(6, rng)
    src = P.emit(prog, "python")
    ns: dict = {}
    exec(compile(src, "bench.py", "exec"), ns)  # noqa: S102 - benchmark self-test
    val = ns["tongue_fn"](2.0, 3.0, 4.0)
    return {"python_runs": isinstance(val, (int, float)), "value": val}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--programs", type=int, default=5000)
    ap.add_argument("--len", dest="prog_len", type=int, default=12)
    ap.add_argument("--workers", type=int, default=0, help="parallel workers (0 = serial)")
    ap.add_argument(
        "--geometric", action="store_true", help="route work to workers through the tongue manifold (tangent tracks)"
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.workers and args.workers > 1:
        import multiprocessing

        cores = multiprocessing.cpu_count()
        ser = run(args.programs, args.prog_len)
        par = run_parallel(args.programs, args.prog_len, args.workers, geometric=args.geometric)
        speedup = ser["seconds"] / par["seconds"]
        if args.json:
            import json

            print(json.dumps({"serial": ser, "parallel": par, "speedup": speedup}, indent=2))
            return 0
        mode = "geometric (tangent tracks)" if args.geometric else "round-robin chunks"
        print("Rubik's-Cube Coding System — PARALLEL speed benchmark")
        print(
            f"  faces: {ser['languages']}   programs: {args.programs:,} x {args.prog_len} ops   "
            f"cores: {cores}   workers: {args.workers}   routing: {mode}"
        )
        print(f"  serial   : {ser['programs_per_s']:>9,.0f} programs/s   {ser['files_per_s']:>10,.0f} files/s")
        print(
            f"  parallel : {par['programs_per_s']:>9,.0f} programs/s   {par['files_per_s']:>10,.0f} files/s "
            f"  ({speedup:.1f}x over serial)"
        )
        print(f"  worker track sizes: {par['chunk_sizes']}")
        return 0

    r = run(args.programs, args.prog_len)
    chk = spot_check()
    r["correctness_python_runs"] = chk["python_runs"]

    if args.json:
        import json

        print(json.dumps(r, indent=2))
        return 0

    print("Rubik's-Cube Coding System — speed benchmark")
    print(f"  faces (languages):     {r['languages']}")
    print(f"  programs x prog_len:   {r['programs']:,} x {r['prog_len']} ops")
    print(f"  source files emitted:  {r['files_emitted']:,}  ({r['total_lines']:,} lines)")
    print(f"  wall time:             {r['seconds']:.3f}s")
    print("  ---- throughput ----")
    print(f"  {r['programs_per_s']:>10,.0f}  programs/s  (each -> all {r['languages']} languages)")
    print(f"  {r['files_per_s']:>10,.0f}  language-files/s")
    print(f"  {r['kloc_per_s']:>10,.1f}  KLOC/s emitted")
    print(f"  {r['mchars_per_s']:>10,.2f}  M chars/s")
    print(f"  correctness spot-check (python emit runs): {r['correctness_python_runs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
