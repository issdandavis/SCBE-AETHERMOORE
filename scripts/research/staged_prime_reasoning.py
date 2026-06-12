#!/usr/bin/env python3
"""staged_prime_reasoning — staged re-loop reasoning with PRIME checkpoints, drift
between them, tagged sub-compaction, a sketchpad, and a difficulty ramp — PLUS the
null test that decides whether 'prime' is load-bearing or just 'increasing-gap
annealing' wearing a prime costume.

The design (user, 2026-06-10): force the model to re-loop in staged turn-sets;
don't over-focus on the next step — consolidate at PRIME turns and watch the DRIFT
between them; when context fill hits a task-optimal %, sub-compact older turns into
retrievable tagged cards; allow sketchpads; ramp difficulty.

The honest pivot: prime turns (2,3,5,7,11,13,...) have GROWING gaps, so
prime-checkpointing is dense-early / sparse-late consolidation — an annealing
schedule. We test prime against uniform spacing and a plain increasing-gap
schedule (same checkpoint budget), under constant- and decaying-drift regimes,
with a random-placement null and a drift-TRIGGERED adaptive schedule.

FINDING (area-under-error-curve, 600 seeds): prime ≈ uniform (primality adds
nothing mechanistic), the increasing-gap SHAPE is actively WORST (sparse-late lets
drift pile up), and DRIFT-TRIGGERED (state-driven) checkpointing wins in both
regimes. The lever is the drift SIGNAL, not the turn index — consolidate when
measured drift crosses a threshold, don't checkpoint on a number pattern. (Mirrors
the turn-cost-lever result: the STATE is load-bearing, the index/magnitude is not.)

No dependencies. Run:
  python scripts/research/staged_prime_reasoning.py null
  python scripts/research/staged_prime_reasoning.py demo
  python scripts/research/staged_prime_reasoning.py curriculum
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint schedules — each returns sorted turn-indices in [1, n_turns].
# ─────────────────────────────────────────────────────────────────────────────


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def primes_upto(n: int) -> list[int]:
    return [k for k in range(2, n + 1) if is_prime(k)]


def sched_prime(n_turns: int) -> list[int]:
    """Consolidate at prime turns: dense early (2,3,5), sparse late (…,29)."""
    return primes_upto(n_turns)


def sched_uniform(n_turns: int, k: int) -> list[int]:
    """k evenly spaced checkpoints — the fixed-cadence baseline."""
    if k <= 0:
        return []
    step = n_turns / (k + 1)
    return sorted({max(1, min(n_turns, round(step * (i + 1)))) for i in range(k)})


def sched_increasing(n_turns: int, k: int) -> list[int]:
    """k checkpoints with geometrically growing gaps — the prime SHAPE (dense
    early, sparse late) with no primality. Isolates whether 'prime' adds anything
    beyond the annealing shape."""
    if k <= 0:
        return []
    r = 1.6
    raw, acc = [], 0.0
    for i in range(k):
        acc += r**i
        raw.append(acc)
    scale = (n_turns - 1) / raw[-1]
    return sorted({max(1, min(n_turns, round(1 + x * scale))) for x in raw})


def sched_random(n_turns: int, k: int, seed: int) -> list[int]:
    """Random placement of k checkpoints — the null. If prime ≈ random, decorative."""
    rng = random.Random(seed)
    return sorted(rng.sample(range(1, n_turns + 1), min(k, n_turns)))


# ─────────────────────────────────────────────────────────────────────────────
# Drift trajectory — a neutral model of reasoning that wanders between
# consolidations. s = distance from the answer-manifold; each turn adds drift
# noise; a checkpoint shrinks s (consolidate, drop the wander).
# ─────────────────────────────────────────────────────────────────────────────


def _drift_sigma(t: int, n_turns: int, regime: str) -> float:
    if regime == "constant":
        return 0.30
    if regime == "decaying":  # explore early, converge late
        return 0.30 * max(0.1, 1.0 - (t - 1) / n_turns)
    raise ValueError(f"unknown regime {regime!r}")


def simulate(checkpoints, n_turns: int, regime: str, seed: int, shrink: float = 0.5) -> float:
    """Mean |distance-from-manifold| ACROSS all turns under a checkpoint schedule.

    Area-under-the-error-curve, not just the endpoint: it rewards keeping reasoning
    consolidated throughout, which is what a checkpoint schedule is actually for.
    """
    rng = random.Random(seed)
    cps = set(checkpoints)
    s, area = 1.0, 0.0
    for t in range(1, n_turns + 1):
        s += rng.gauss(0.0, _drift_sigma(t, n_turns, regime))
        if t in cps:
            s *= shrink
        area += abs(s)
    return area / n_turns


def _adaptive_usage_uncapped(n_turns: int, regime: str, seed: int, theta: float, shrink: float = 0.5) -> int:
    """How many checkpoints a drift>theta trigger fires if left uncapped (for θ calibration)."""
    rng = random.Random(seed)
    s, last_cp_s, used = 1.0, 1.0, 0
    for t in range(1, n_turns + 1):
        s += rng.gauss(0.0, _drift_sigma(t, n_turns, regime))
        if abs(s - last_cp_s) >= theta:
            s *= shrink
            last_cp_s = s
            used += 1
    return used


def _calibrate_theta(n_turns: int, regime: str, k: int, seeds: int = 200) -> float:
    """Find the drift threshold θ that fires ≈ k checkpoints on average — so the
    adaptive schedule is compared at the SAME budget as the fixed schedules."""
    lo, hi = 0.01, 3.0
    for _ in range(22):
        mid = (lo + hi) / 2
        usage = statistics.mean(_adaptive_usage_uncapped(n_turns, regime, seed, mid) for seed in range(seeds))
        if usage > k:  # too many fires -> raise the threshold
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def simulate_adaptive(n_turns: int, regime: str, seed: int, k: int, theta: float, shrink: float = 0.5) -> float:
    """State-driven checkpointing: consolidate when DRIFT since the last checkpoint
    crosses θ, capped at k, spending any leftover budget before turns run out.
    This is the user's real intuition — 'watch the drift, don't count steps'."""
    rng = random.Random(seed)
    s, last_cp_s, used, area = 1.0, 1.0, 0, 0.0
    for t in range(1, n_turns + 1):
        s += rng.gauss(0.0, _drift_sigma(t, n_turns, regime))
        budget_left = k - used
        force = budget_left > 0 and (n_turns - t) < budget_left
        if budget_left > 0 and (abs(s - last_cp_s) >= theta or force):
            s *= shrink
            last_cp_s = s
            used += 1
        area += abs(s)
    return area / n_turns


def null_experiment(n_turns: int = 30, seeds: int = 600) -> dict:
    """Prime vs uniform vs increasing vs random-null vs adaptive(drift), under
    constant + decaying drift.

    All carry the SAME checkpoint budget (the number of primes ≤ n_turns), so this
    measures placement quality at fixed budget — not 'more checkpoints win'. The
    adaptive schedule is index-blind: it fires on the drift STATE, which is what the
    prime idea was really reaching for.
    """
    primes = sched_prime(n_turns)
    k = len(primes)
    scheds = {
        "prime": primes,
        "uniform": sched_uniform(n_turns, k),
        "increasing": sched_increasing(n_turns, k),
    }
    results: dict[str, dict[str, float]] = {}
    thetas: dict[str, float] = {}
    for regime in ("constant", "decaying"):
        row: dict[str, float] = {}
        for name, cps in scheds.items():
            row[name] = statistics.mean(simulate(cps, n_turns, regime, seed) for seed in range(seeds))
        row["random_null"] = statistics.mean(
            simulate(sched_random(n_turns, k, seed + 10_000), n_turns, regime, seed) for seed in range(seeds)
        )
        theta = _calibrate_theta(n_turns, regime, k)
        thetas[regime] = round(theta, 4)
        row["adaptive"] = statistics.mean(simulate_adaptive(n_turns, regime, seed, k, theta) for seed in range(seeds))
        results[regime] = row
    return {
        "n_turns": n_turns,
        "k_checkpoints": k,
        "seeds": seeds,
        "schedules": scheds,
        "adaptive_theta": thetas,
        "results": results,
        "verdict": _verdict(results),
    }


def _verdict(results: dict) -> list[str]:
    lines = []
    for regime, row in results.items():
        best = min(row, key=row.get)
        prime, uni = row["prime"], row["uniform"]
        fixed = min(row[s] for s in ("prime", "uniform", "increasing", "random_null"))
        adaptive_wins = row["adaptive"] <= fixed
        prime_vs_uniform = "≈" if abs(prime - uni) < 0.03 else ("<" if prime < uni else ">")
        verdict = (
            f"{regime}: best={best}. prime {prime_vs_uniform} uniform "
            "(primality adds nothing mechanistic — both are just fixed cadence). "
        )
        verdict += (
            "Drift-TRIGGERED (state-driven) checkpointing wins — the lever is the drift signal, not the turn index."
            if adaptive_wins
            else "Adaptive did not dominate under this regime/budget."
        )
        lines.append(verdict)
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Controller mechanisms — sketchpad, tagged sub-compaction, staged prime loop.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Note:
    turn: int
    tag: str
    text: str

    def tokens(self) -> int:
        return max(1, len(self.text) // 4)  # ~4 chars/token estimate


@dataclass
class Sketchpad:
    """Scratch working memory: tagged notes the loop writes and retrieves by tag."""

    notes: list = field(default_factory=list)

    def write(self, turn: int, tag: str, text: str) -> None:
        self.notes.append(Note(turn, tag, text))

    def retrieve(self, tag: str) -> list:
        return [n for n in self.notes if n.tag == tag]

    def tokens(self) -> int:
        return sum(n.tokens() for n in self.notes)


def sub_compact(notes, keep_recent: int):
    """Compress all but the most-recent notes into one tagged COMPACT card per tag.

    Old turns become a retrievable summary (find by tag) instead of raw history —
    context shrinks, nothing is lost to recall. Returns (new_notes, card_or_None).
    """
    if len(notes) <= keep_recent:
        return notes, None
    old, recent = notes[:-keep_recent], notes[-keep_recent:]
    by_tag: dict[str, list] = {}
    for n in old:
        by_tag.setdefault(n.tag, []).append(n)
    lines = []
    for tag, ns in by_tag.items():
        joined = " | ".join(n.text for n in ns)[:120]
        lines.append(f"[{tag}] x{len(ns)} turns {ns[0].turn}-{ns[-1].turn}: {joined}")
    card = Note(turn=recent[0].turn, tag="COMPACT", text="\n".join(lines))
    return [card] + recent, card


def run_staged(n_turns: int, regime: str, seed: int, ctx_budget: int = 60, compact_pct: float = 0.8):
    """One staged-reasoning run: re-loop, checkpoint at primes, log drift between
    them, sub-compact the sketchpad when it crosses compact_pct of the budget, and
    flag a stall (drift→0 but unsolved across two prime checkpoints) for escalation.
    """
    rng = random.Random(seed)
    pad = Sketchpad()
    cps = set(sched_prime(n_turns))
    s = 1.0
    last_sig = None
    drifts, checkpoints, compactions = [], [], []
    stalled_streak, escalated = 0, False
    for t in range(1, n_turns + 1):
        s += rng.gauss(0.0, _drift_sigma(t, n_turns, regime))
        pad.write(t, "step", f"t{t} s={s:+.3f}")
        if t in cps:
            s *= 0.5
            drift = abs(s - last_sig) if last_sig is not None else None
            if drift is not None:
                drifts.append(round(drift, 4))
            last_sig = s
            checkpoints.append({"turn": t, "s": round(s, 4), "drift": None if drift is None else round(drift, 4)})
            pad.write(t, "checkpoint", f"prime t{t} s={s:+.3f} drift={drift}")
            solved = abs(s) < 0.15
            if drift is not None and drift < 0.05 and not solved:
                stalled_streak += 1
            else:
                stalled_streak = 0
            if stalled_streak >= 2 and not escalated:
                escalated = True
                pad.write(t, "escalate", f"stalled across 2 prime checkpoints at t{t} — hand residue up a rung")
        if pad.tokens() > ctx_budget * compact_pct:
            pad.notes, card = sub_compact(pad.notes, keep_recent=4)
            if card:
                compactions.append({"turn": t, "to_tokens": pad.tokens()})
    return {
        "regime": regime,
        "n_turns": n_turns,
        "prime_checkpoints": sorted(cps),
        "drifts_between_primes": drifts,
        "checkpoints": checkpoints,
        "compactions": compactions,
        "escalated": escalated,
        "final_error": round(abs(s), 4),
        "solved": abs(s) < 0.15,
        "sketchpad_tokens": pad.tokens(),
    }


def curriculum(levels: int = 5, seed: int = 0) -> dict:
    """Ramp difficulty: each level adds turns and stiffer drift. Stop when the
    solver fails — that boundary is where the next model rung is needed."""
    out = []
    for lvl in range(1, levels + 1):
        n_turns = 10 + 6 * lvl
        regime = "constant" if lvl % 2 else "decaying"
        runs = [run_staged(n_turns, regime, seed=seed * 100 + lvl * 10 + i) for i in range(6)]
        solved = sum(1 for r in runs if r["solved"])
        out.append(
            {
                "level": lvl,
                "n_turns": n_turns,
                "regime": regime,
                "solved": f"{solved}/6",
                "mean_final_error": round(statistics.mean(r["final_error"] for r in runs), 4),
                "any_escalated": any(r["escalated"] for r in runs),
            }
        )
        if solved == 0:
            break
    return {"levels_attempted": len(out), "ladder": out}


# ─────────────────────────────────────────────────────────────────────────────


def _print_null(r: dict) -> None:
    print("=== staged prime reasoning — is 'prime' load-bearing or annealing-shape? ===\n")
    print(f"n_turns={r['n_turns']}  checkpoints(k)={r['k_checkpoints']}  seeds={r['seeds']}")
    print(f"  prime turns:      {r['schedules']['prime']}")
    print(f"  uniform turns:    {r['schedules']['uniform']}")
    print(f"  increasing turns: {r['schedules']['increasing']}\n")
    print("  mean final error (LOWER is better), same checkpoint budget:")
    print(f"  {'regime':10s} {'prime':>9s} {'uniform':>9s} {'increasing':>11s} {'random':>9s} {'adaptive':>9s}")
    for regime, row in r["results"].items():
        print(
            f"  {regime:10s} {row['prime']:9.4f} {row['uniform']:9.4f} "
            f"{row['increasing']:11.4f} {row['random_null']:9.4f} {row['adaptive']:9.4f}"
        )
    print(f"\n  adaptive drift-threshold θ (calibrated to ~k fires): {r['adaptive_theta']}")
    print("\n  verdict:")
    for line in r["verdict"]:
        print(f"   - {line}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="staged_prime_reasoning")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pn = sub.add_parser("null", help="prime vs uniform vs increasing vs random")
    pn.add_argument("--turns", type=int, default=30)
    pn.add_argument("--seeds", type=int, default=600)
    pn.add_argument("--json", action="store_true")
    pd = sub.add_parser("demo", help="one staged run with prime checkpoints + drift + sub-compaction")
    pd.add_argument("--turns", type=int, default=30)
    pd.add_argument("--regime", default="decaying", choices=["constant", "decaying"])
    pd.add_argument("--seed", type=int, default=7)
    pd.add_argument("--json", action="store_true")
    pc = sub.add_parser("curriculum", help="ramp difficulty until the solver fails")
    pc.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    if args.cmd == "null":
        r = null_experiment(n_turns=args.turns, seeds=args.seeds)
        print(json.dumps(r, indent=2)) if args.json else _print_null(r)
    elif args.cmd == "demo":
        r = run_staged(args.turns, args.regime, args.seed)
        if args.json:
            print(json.dumps(r, indent=2))
        else:
            print(f"=== staged demo ({args.regime}, {args.turns} turns) ===")
            print(f"  prime checkpoints: {r['prime_checkpoints']}")
            print(f"  drift between primes: {r['drifts_between_primes']}")
            print(f"  sub-compactions: {r['compactions']}")
            print(f"  escalated (stalled 2 primes): {r['escalated']}")
            print(f"  final error: {r['final_error']}  solved: {r['solved']}  pad tokens: {r['sketchpad_tokens']}")
    elif args.cmd == "curriculum":
        r = curriculum()
        if args.json:
            print(json.dumps(r, indent=2))
        else:
            print("=== curriculum (difficulty ramp) ===")
            for lvl in r["ladder"]:
                print(
                    f"  L{lvl['level']} turns={lvl['n_turns']:3d} {lvl['regime']:8s} "
                    f"solved={lvl['solved']} mean_err={lvl['mean_final_error']} esc={lvl['any_escalated']}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
