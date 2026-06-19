"""sieve_calc: the prime sieve as a deterministic CALCULATOR for the stepwise step machine.

Today's experiment showed a weak model can't be trusted with exact number work -- it botches the
modulo/objective and even refuses a stated rule. So don't ask it: a `calc` step routes the exact
computation to the prime sieve, which is deterministic and correct by construction, and leaves the
model only the judgement on top (where a misstep rewinds).

This wires two existing real systems into stepwise:
  * src.numtheory  -- Sieve of Eratosthenes + Miller-Rabin: is_prime, factorization.
  * src.prime_category -- a number "triangulated across vectored prime-regions": each region is a
    distinct prime, membership in a region is a divisibility test, and the FULL region-set of a code
    is recovered by FACTORING it (the sieve). That is the "triangulate numbers through different
    vectored regions" primitive, made into a calc step.

The sieve does the locating; stepwise carries the rewind + the verification. The model never does
the arithmetic it gets wrong.

    from python.scbe.stepwise import run_stepwise, scripted_proposer
    run_stepwise(classify_number_task(91), scripted_proposer(["prime", "composite"]))
    # 91 = 7*13: 'prime' missteps -> rewind -> 'composite'; the sieve did the factoring
"""

from __future__ import annotations

from typing import Dict

from src import numtheory as nt
from src.prime_category import PrimeCategories

from .stepwise import Step, Task

# --- prime-sieve calc steps (deterministic; the model is never asked) ----------------


def seed_calc(key: str, value: object) -> Step:
    """A calc step that just plants a known value into state (the task input)."""
    return Step(key, key, calc=lambda st, v=value: v)


def is_prime_calc(key: str, src: str) -> Step:
    """state[key] = is_prime(state[src]) -- via the deterministic sieve, not the model."""
    return Step(key, key, calc=lambda st: nt.is_prime(int(st[src])))


def factor_count_calc(key: str, src: str) -> Step:
    """state[key] = number of DISTINCT prime factors of state[src] (0 for n<=1)."""
    return Step(key, key, calc=lambda st: len(nt.factorization(int(st[src]))) if int(st[src]) > 1 else 0)


def regions_calc(pc: PrimeCategories, key: str, src: str) -> Step:
    """state[key] = the prime-regions state[src] belongs to (factor the code -> region set)."""
    return Step(key, key, calc=lambda st: pc.decode(int(st[src])))


# --- demo tasks: the sieve computes, the model only judges, a misstep rewinds ---------
_LABELS = ("unit", "prime", "prime-power", "composite")


def classify_number_task(n: int) -> Task:
    """The sieve decides primality + distinct-factor count; the model only applies the labeling rule."""

    def correct(st: Dict[str, object]) -> str:
        if n == 1:
            return "unit"
        if st["is_prime"]:
            return "prime"
        return "prime-power" if st["nfac"] == 1 else "composite"

    return Task(
        name="classify(%d)" % n,
        goal="label %d by its prime structure" % n,
        steps=[
            seed_calc("n", n),
            is_prime_calc("is_prime", "n"),
            factor_count_calc("nfac", "n"),
            Step("label", "label", options=lambda st: list(_LABELS), check=lambda st, v: v == correct(st)),
        ],
    )


def route_by_region_task(pc: PrimeCategories, code: int, handlers: Dict[str, str]) -> Task:
    """The sieve triangulates `code` into its regions; the model routes to a matching handler.

    `handlers` maps handler-name -> the region it serves. A correct route picks a handler whose region
    is one the code actually belongs to -- and those regions are recovered deterministically by
    factoring the code (the sieve), never guessed by the model.
    """

    def correct(st: Dict[str, object], v: str) -> bool:
        return v in handlers and handlers[v] in st["regions"]  # type: ignore[operator]

    return Task(
        name="route(%d)" % code,
        goal="route item %d to a handler matching one of its prime-regions" % code,
        steps=[
            seed_calc("code", code),
            regions_calc(pc, "regions", "code"),
            Step("handler", "handler", options=lambda st: list(handlers), check=lambda st, v: correct(st, v)),
        ],
    )


def main(argv: object = None) -> int:
    from .stepwise import run_stepwise, scripted_proposer

    print("SIEVE_CALC  the prime sieve does the exact number work; the model only judges\n")

    print("== classify 91 (=7*13): the model guesses 'prime', the sieve's facts reject it -> rewind ==")
    r = run_stepwise(classify_number_task(91), scripted_proposer(["prime", "composite"]))
    for t in r["trace"]:
        print("  %-9s %-6s %-9s %s" % (t["step"], t["source"], t["status"], t["value"]))
    print(
        "  -> %s   (sieve: is_prime=%s, distinct factors=%s)"
        % (r["answer"], r["state"]["is_prime"], r["state"]["nfac"])
    )

    print("\n== triangulate + route: a code factored into its prime-regions, model routes ==")
    pc = PrimeCategories(["security", "coding", "chemistry", "music"])
    code = pc.code(["coding", "music"])  # 3 * 7 = 21
    handlers = {"scanner": "security", "codegen": "coding", "reactor": "chemistry", "daw": "music"}
    r = run_stepwise(route_by_region_task(pc, code, handlers), scripted_proposer(["scanner", "codegen"]))
    print("  code %d -> regions %s" % (code, r["state"]["regions"]))
    for t in r["trace"]:
        if t["source"] == "model":
            print("  route try: %-8s %s" % (t["value"], t["status"]))
    print("  -> routed to %r (serves region in the code); 'scanner' was a misstep (security not present)" % r["answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
