"""allatonce_observer: an all-at-once / global-constraint check over the SCBE observer transcript.

WHAT THIS IS (and is NOT)
=========================
SCBE's "observer" is the governance/measurement layer that watches an input stream and emits a
forward-chained, SHA-256-sealed transcript of decisions (see desktop_access.ActionRegistry). Today
every record is decided and sealed STEP BY STEP, forward in time -- a Markov chain: record N is bound
only to record N-1 (its `_prev` seal), and `verify()` walks that chain.

This module is a small, deterministic experiment that applies Emily Adlam's ALL-AT-ONCE /
GLOBAL-CONSTRAINT picture of physical law to that observer. In Adlam's frame a law is not a
step-by-step time-evolution rule; it is a CONSTRAINT on the WHOLE history at once -- the actual
"Humean mosaic" must lie in the INTERSECTION of all constraints (the sudoku analogy: rules apply to
the whole grid simultaneously, not left-to-right). The load-bearing consequence she draws is that
"the result of a measurement can depend on global facts even if there is no record of those facts in
the state of the world immediately prior to the measurement" -- i.e. forward, locally-screened
checking can MISS facts that a whole-history check catches.

So the question this module makes MECHANICAL and MEASURABLE is:

    Over a fixed transcript, how many integrity/consistency violations does a WHOLE-TRANSCRIPT
    constraint pass catch that the step-local (Markovian) forward-chain seal CANNOT see?

The transcript is treated as a candidate "mosaic". The Markovian observer is the existing
forward-chain `verify()` (local: each record vs the one before). The all-at-once observer is a set of
GLOBAL constraints evaluated over the entire record set simultaneously; an admissible mosaic must lie
in the intersection of ALL of them (every constraint returns no violations). The deterministic METRIC
is the delta: violations the global pass reports that the local pass reports as fine.

HONEST CAVEAT (read before quoting this anywhere): this is an ANALOGY to Adlam's physics, not
physics. There is no quantum mechanics here, no Humean mosaic of spacetime events, no Tsirelson
bound, no retrocausality. "Global consistency" here just means "a deterministic predicate over the
full Python list of records." It is a software integrity check inspired by a metaphor. Consistency is
NOT correctness (a globally-consistent transcript can still describe wrong actions), and these
constraints are an UNKEYED check over an in-memory list -- they detect a forger no better than the
underlying seal does (a privileged in-process attacker who re-chains everything defeats both). See
desktop_access._seal's HONEST LIMIT.

Run:
    python -m python.scbe.allatonce_observer
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

# Reuse the EXISTING seal -- we are not inventing a new integrity primitive, only adding a
# whole-history pass on top of the same sealed records the observer already produces.
from .desktop_access import _seal

Record = Dict[str, Any]
# a constraint maps the WHOLE transcript -> list of (record_index, human-readable reason)
Constraint = Callable[[List[Record]], List[Tuple[int, str]]]


# ---------------------------------------------------------------------------
# (a) OBSERVER STATE REPRESENTATION
# ---------------------------------------------------------------------------
# The observer state IS the transcript: an ordered list of sealed records. Each record (produced by
# the existing ActionRegistry) carries at minimum:
#   hop      : 1-based position the record CLAIMS to occupy
#   action   : the verb that was invoked
#   params   : the (deep-copied) arguments
#   decision : ALLOWED / REFUSED / DENIED / NEEDS_CONFIRM / ERROR / NO_ACTION
#   result   : the handler result or refusal reason
#   _prev    : the seal of the previous record (or the session nonce for the first)
#   seal     : SHA-256 over the record body (everything except `seal`)
# `nonce` anchors the head of the chain. The pair (nonce, records) is the candidate "mosaic".


@dataclass
class ObserverState:
    """The whole observer history as one object -- the candidate Humean mosaic."""

    nonce: str
    records: List[Record] = field(default_factory=list)

    @classmethod
    def from_registry(cls, reg: Any) -> "ObserverState":
        """Snapshot a desktop_access.ActionRegistry's sealed transcript as a mosaic."""
        # deep copy via json round-trip so later edits to the registry don't mutate the snapshot
        recs = json.loads(json.dumps(reg.transcript, default=str))
        return cls(nonce=reg.nonce, records=recs)


# ---------------------------------------------------------------------------
# (b) MARKOVIAN BASELINE  --  decide each step from LOCAL state only
# ---------------------------------------------------------------------------
def markovian_violations(state: ObserverState) -> List[Tuple[int, str]]:
    """The step-local observer: exactly what desktop_access.verify() does, made to report WHICH
    record it first trips on. Each record is checked against only (i) its own body via the seal and
    (ii) the immediately-prior seal via `_prev`. This is the forward, temporally-local view: the
    present record is judged using only the record right before it. It is a Markov chain over seals.

    Returns the list of (index, reason) it can see -- it stops at the FIRST break, because a broken
    link means every downstream `_prev` is computed off a value it can no longer trust (that is the
    honest limit of a purely forward check: one early break blinds it to everything after).
    """
    prev = state.nonce
    for i, r in enumerate(state.records):
        if r.get("seal") != _seal(r):
            return [(i, "local: record body does not match its own seal")]
        if r.get("_prev") != prev:
            return [(i, "local: _prev does not match the previous seal (chain broken)")]
        prev = r["seal"]
    return []


def markovian_violations_strong(state: ObserverState) -> List[Tuple[int, str]]:
    """A FAIR forward baseline (the study skeptic's bar). The strongest forward observer that still has
    NO whole-history view: it does NOT stop at the first break, it ALSO checks the local hop successor
    (hop == position+1), and it keeps running refused/guarded sets. `measure().extra_vs_strong` is the
    HONEST global-only gain over THIS -- not over the weaker shipped verify(). Per the skeptic, the only
    thing this baseline structurally cannot catch is a FUTURE-dependent fact (e.g. a NEEDS_CONFIRM that
    appears AFTER the ungrounded ALLOWED); that residual is the genuine all-at-once advantage. (The
    deeper decision-level version of that advantage lives in observer_dynamics.py.)"""
    out: List[Tuple[int, str]] = []
    prev = state.nonce
    refused: set = set()
    guarded: set = set()
    for i, r in enumerate(state.records):
        if r.get("seal") != _seal(r):
            out.append((i, "strong-fwd: body != seal"))
        if r.get("_prev") != prev:
            out.append((i, "strong-fwd: _prev != previous seal"))
        if r.get("hop") != i + 1:
            out.append((i, "strong-fwd: hop != position+1 (local successor check)"))
        if r.get("decision") == "NEEDS_CONFIRM":
            guarded.add(r.get("action"))
        if r.get("decision") == "ALLOWED" and r.get("action") in guarded and "confirm" not in r:
            out.append((i, "strong-fwd: ungrounded guarded success"))
        key = (r.get("action"), json.dumps(r.get("params"), sort_keys=True, default=str))
        if r.get("decision") == "ALLOWED" and key in refused:
            out.append((i, "strong-fwd: post-refusal success"))
        if r.get("decision") == "REFUSED":
            refused.add(key)
        prev = r.get("seal", prev)
    return out


# ---------------------------------------------------------------------------
# (c) ALL-AT-ONCE VARIANT  --  GLOBAL constraints over the WHOLE transcript at once
# ---------------------------------------------------------------------------
# Each constraint is a predicate over the ENTIRE record list. An admissible mosaic is one in the
# INTERSECTION of all constraints (every constraint returns []). Crucially these look at GLOBAL facts
# -- relations among records anywhere in the history -- not just record N vs N-1. This is where the
# "depends on global facts not in the immediately-prior state" idea becomes concrete and testable.


def c_seal_integrity(records: List[Record]) -> List[Tuple[int, str]]:
    """Every record's body must match its own seal -- evaluated for ALL records, not stop-at-first.
    Unlike the Markovian pass, a break early does not blind it to a break late."""
    return [(i, "global: body != seal") for i, r in enumerate(records) if r.get("seal") != _seal(r)]


def c_chain_linkage(records: List[Record], nonce: str) -> List[Tuple[int, str]]:
    """Forward linkage as a GLOBAL relation: record i's `_prev` must equal record i-1's seal for ALL
    i (head bound to nonce). Reported for every break, so a re-chained middle that the forward walk
    would accept-then-trip-once is fully enumerated."""
    out: List[Tuple[int, str]] = []
    expected = nonce
    for i, r in enumerate(records):
        if r.get("_prev") != expected:
            out.append((i, "global: _prev != previous seal"))
        expected = r.get("seal", expected)
    return out


def c_hop_monotone(records: List[Record]) -> List[Tuple[int, str]]:
    """GLOBAL ordering invariant: the `hop` field each record CLAIMS must be exactly its position+1,
    strictly increasing by 1 with no gaps or repeats. A reorder/insert/delete that someone bothered
    to RE-CHAIN (so the forward seal walk passes!) still leaves the hop sequence globally wrong --
    this is a fact about the whole sequence the local link check cannot represent. This is the
    sudoku-style 'the whole column must be a permutation' rule."""
    return [
        (i, "global: hop %r out of order (expected %d)" % (r.get("hop"), i + 1))
        for i, r in enumerate(records)
        if r.get("hop") != i + 1
    ]


def c_confirm_grounding(records: List[Record]) -> List[Tuple[int, str]]:
    """GLOBAL grounding / 'no fact comes from nowhere' (Adlam rejects closed loops whose variables are
    determined by nothing). An ALLOWED record for a GUARDED-class action claims it was confirmed; that
    confirmation must be grounded by a `confirm` field present in the SAME record. A record asserting
    it ran a guarded op while carrying no confirmation is self-justifying -> illegitimate. (We key off
    a NEEDS_CONFIRM seen anywhere in the mosaic for the same action to know it is guarded -- a
    whole-history lookup, not a prior-state lookup.)"""
    guarded = {r.get("action") for r in records if r.get("decision") == "NEEDS_CONFIRM"}
    return [
        (i, "global: action %r ran ALLOWED without a recorded confirm (ungrounded)" % r.get("action"))
        for i, r in enumerate(records)
        if r.get("decision") == "ALLOWED" and r.get("action") in guarded and "confirm" not in r
    ]


def c_no_post_refusal_success(records: List[Record]) -> List[Tuple[int, str]]:
    """GLOBAL frequency/consistency constraint that needs facts AFTER the record: once a destructive
    op for an action is REFUSED, the same (action, params) must never appear later as ALLOWED in the
    mosaic. A purely forward observer at the ALLOWED record sees nothing wrong locally -- the
    contradicting fact lives in an EARLIER record AND the rule about it only resolves when the whole
    history is in view. This is the 'measurement depends on global facts not in the prior state' case
    made mechanical: legitimacy of record j depends on record i for i<j with no link between them."""
    refused = {
        (r.get("action"), json.dumps(r.get("params"), sort_keys=True, default=str))
        for r in records
        if r.get("decision") == "REFUSED"
    }
    return [
        (i, "global: %r ran ALLOWED after an identical call was REFUSED earlier" % r.get("action"))
        for i, r in enumerate(records)
        if r.get("decision") == "ALLOWED"
        and (r.get("action"), json.dumps(r.get("params"), sort_keys=True, default=str)) in refused
    ]


def allatonce_violations(state: ObserverState) -> Dict[str, List[Tuple[int, str]]]:
    """Evaluate the FULL constraint set over the WHOLE transcript at once. The mosaic is admissible
    iff it lies in the intersection of all constraints (every list empty)."""
    return {
        "seal_integrity": c_seal_integrity(state.records),
        "chain_linkage": c_chain_linkage(state.records, state.nonce),
        "hop_monotone": c_hop_monotone(state.records),
        "confirm_grounding": c_confirm_grounding(state.records),
        "no_post_refusal_success": c_no_post_refusal_success(state.records),
    }


def is_admissible_mosaic(state: ObserverState) -> bool:
    """True iff the transcript lies in the intersection of ALL global constraints (Adlam's 'reality
    must be in the intersection of all constraints', made into a boolean over a finite record set)."""
    return all(not v for v in allatonce_violations(state).values())


# ---------------------------------------------------------------------------
# (d) THE DETERMINISTIC METRIC  +  (e) WHAT IT MEASURES
# ---------------------------------------------------------------------------
@dataclass
class CaughtReport:
    local_count: int  # violations the Markovian (forward, local) observer reports
    global_count: int  # total violations the all-at-once observer reports
    extra_caught: int  # global_count - (violations the local view also sees) == the METRIC
    local_passes: bool  # did the Markov chain say "sealed/intact"?
    global_passes: bool  # is the mosaic admissible (intersection of all constraints)?
    detail: Dict[str, List[Tuple[int, str]]]  # per-constraint global violations
    local_detail: List[Tuple[int, str]]  # what the local view saw
    strong_count: int = 0  # violations a FAIR forward baseline (markovian_violations_strong) also catches
    extra_vs_strong: int = 0  # the HONEST global-only gain over the fair baseline (skeptic's number)


def measure(state: ObserverState) -> CaughtReport:
    """THE METRIC, computed deterministically.

    extra_caught = (# violations the all-at-once pass finds) - (# the Markovian pass also finds)

    Mechanically:
      1. local = markovian_violations(state)            # forward, prior-state-only
      2. glob  = allatonce_violations(state)            # whole-history constraints
      3. global_count = total entries across glob
      4. The Markovian pass can only ever see seal/linkage breaks AT or BEFORE its first trip. So the
         number it "also sees" is len(local) (0 or 1 by construction). extra_caught is everything the
         global pass found beyond that. extra_caught > 0  <=>  the global view caught something the
         local view is blind to.

    WHAT IT MEASURES: the count (and identity) of integrity/consistency violations that depend on
    GLOBAL facts -- re-chained reorders/inserts (hop_monotone), ungrounded guarded successes
    (confirm_grounding), and a success that contradicts an earlier refusal (no_post_refusal_success).
    These are exactly the cases Adlam highlights: the legitimacy of a record depends on facts that are
    NOT in the immediately-prior state, so the forward/local observer cannot see them.
    """
    local = markovian_violations(state)
    strong = markovian_violations_strong(state)
    glob = allatonce_violations(state)
    global_count = sum(len(v) for v in glob.values())
    extra = max(0, global_count - len(local))
    return CaughtReport(
        local_count=len(local),
        global_count=global_count,
        extra_caught=extra,
        local_passes=(len(local) == 0),
        global_passes=all(not v for v in glob.values()),
        detail=glob,
        local_detail=local,
        strong_count=len(strong),
        extra_vs_strong=max(0, global_count - len(strong)),  # the honest gain vs a FAIR forward baseline
    )


# ---------------------------------------------------------------------------
# A re-chaining tamper helper: this is the adversary that DEFEATS the Markovian seal but is caught
# all-at-once. It edits a record and recomputes seals forward so the local chain walk passes.
# ---------------------------------------------------------------------------
def rechain(state: ObserverState) -> ObserverState:
    """Recompute the whole forward seal chain in place so markovian_violations() passes again. A
    privileged in-process attacker can do this (see _seal's HONEST LIMIT). We use it to manufacture a
    transcript the LOCAL observer accepts but the GLOBAL observer should still reject when a
    whole-history invariant (hop order, grounding, post-refusal success) was broken."""
    prev = state.nonce
    for r in state.records:
        r["_prev"] = prev
        r.pop("seal", None)
        r["seal"] = _seal(r)
        prev = r["seal"]
    return state


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
def _demo_state() -> Tuple[ObserverState, ObserverState]:
    """Build a clean transcript via the real registry, then produce a RE-CHAINED tampered copy whose
    forward seal passes but whose whole-history facts are broken."""
    from .desktop_access import default_registry

    reg = default_registry()
    reg.invoke("open_app", {"app": "files"})
    reg.invoke("run_allowed_command", {"command": "rm -rf /"}, confirm="x")  # REFUSED (destructive)
    reg.invoke("run_allowed_command", {"command": "ls"})  # NEEDS_CONFIRM: marks the action guarded
    reg.invoke("run_allowed_command", {"command": "ls"}, confirm="user")  # ALLOWED (guarded+confirm)
    clean = ObserverState.from_registry(reg)

    tampered = ObserverState.from_registry(reg)
    # Attack 1: reorder records 0 and 2 (hop fields now globally wrong) ...
    tampered.records[0], tampered.records[2] = tampered.records[2], tampered.records[0]
    # Attack 2: strip the confirm off the guarded ALLOWED record (ungrounded success) ...
    for r in tampered.records:
        if r.get("action") == "run_allowed_command" and r.get("decision") == "ALLOWED":
            r.pop("confirm", None)
    # ... then RE-CHAIN so the forward/local seal walk is fooled into passing.
    rechain(tampered)
    return clean, tampered


def main() -> int:
    clean, tampered = _demo_state()

    print("ALL-AT-ONCE OBSERVER  --  global-constraint check over the SCBE transcript\n")
    print("CLEAN transcript (%d records):" % len(clean.records))
    rc = measure(clean)
    print("  Markovian (local) passes :", rc.local_passes)
    print("  all-at-once admissible   :", rc.global_passes)
    print("  extra caught by global   :", rc.extra_caught)

    print("\nTAMPERED + RE-CHAINED transcript (forward seal recomputed to fool the local walk):")
    rt = measure(tampered)
    print("  Markovian (local) passes :", rt.local_passes, " <- the forward seal is FOOLED")
    print("  all-at-once admissible   :", rt.global_passes, "  <- the whole-history view is NOT")
    print("  extra vs SHIPPED verify():", rt.extra_caught, " (real but over-credits: shipped seal is weak)")
    print("  extra vs FAIR baseline   :", rt.extra_vs_strong, " <- the HONEST number (skeptic-fair; a fair")
    print("                                forward checker with a local hop check catches the re-chain too)")
    for name, viols in rt.detail.items():
        if viols:
            print("    [%s] %s" % (name, viols))
    print("\nNOTE: at this INTEGRITY layer the global pass ~ a fair forward checker; the genuine")
    print("all-at-once advantage (future-dependent retractions, CBJ jump-back) is in observer_dynamics.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
