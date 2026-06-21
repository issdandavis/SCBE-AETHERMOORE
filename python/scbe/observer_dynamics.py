"""observer_dynamics: measurable observer-state dynamics over governance DECISIONS (CSP / all-at-once).

Companion to allatonce_observer.py. That module works at the INTEGRITY layer (seals over a transcript --
"was this mutated?"). This one works at the DECISION-SEMANTICS / VALIDITY layer ("does the whole
completed history of decisions satisfy the global rules, even if a later decision retroactively
invalidates an earlier one?"). It makes Emily Adlam's all-at-once / Sudoku move executable as a
Constraint Satisfaction Problem (CSP):

    variables  = the decision at each step (DecisionRecord)
    domains    = the allowed decisions (ALLOW / DENY / ESCALATE / route names ...)
    constraints= global rules over the WHOLE history (no contradiction on a route; an ESCALATE must be
                 resolved later; a call REFUSED once must not later succeed)
    solution   = a whole history in the intersection of all constraints (a "valid completed grid")

THE LOAD-BEARING, NON-RELABEL CLAIM (validated by the study's adversarial skeptic): a purely forward
("Markovian") observer commits each decision from the state so far and NEVER revisits it. Some
violations only become visible LATER -- a decision at step j contradicts one already committed at step
i < j. No forward observer, however strong, can have caught that at step i (the deciding fact was in
its future). The all-at-once observer re-solves the whole history and RETRACTS the earlier decision.
The measurable delta is the RETROACTIVE-CONSISTENCY GAP, and it is reported against a FAIR forward
baseline (one that keeps running sets and continues past breaks) -- so the gap counts only genuinely
future-dependent retractions, not weak-baseline bookkeeping (the codebase's 'block-offload +24' lesson).

Conflict-Directed Backjumping (CBJ): when the global pass finds a violation, its conflict set names the
records involved; the EARLIEST of them is the jump-back target -- re-decide from there, not one step
back. That is the mechanism behind "inferred retroactive jump-back to the error's root cause".

HONEST CAVEATS: this is an engineering ANALOGY to Adlam's physics, not physics. Consistency is NOT
correctness (a globally consistent history can still be wrong). The constraint set is illustrative, not
canonical. The repair policy (how a node re-decides) is pluggable -- the module provides the MECHANISM
(detect -> conflict set -> earliest jump-back -> re-solve with an oscillation guard), not a universal fix.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .reversible_circuit import ROOM_T_K, EnergyLedger

# decision categories the observer can emit (the CSP domain, kept open as plain strings)
ALLOW, DENY, ESCALATE, REFUSED = "ALLOW", "DENY", "ESCALATE", "REFUSED"


@dataclass
class DecisionRecord:
    """One observer decision. `seq` is the logical position (deterministic; no wall clock, so the gap is
    reproducible). `input_id` ties related inputs together; `route` is the lane the decision is about."""

    seq: int
    input_id: str
    decision: str
    route: Optional[str] = None
    verdict: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    """A structured global-constraint violation -- the CSP conflict set, with the jump-back target."""

    rule: str
    message: str
    involved: List[int]  # record indices participating in the conflict (the conflict set)

    @property
    def earliest_index(self) -> int:
        return min(self.involved)


# a constraint maps the WHOLE history -> its violations (global, not step-local)
Constraint = Callable[[List[DecisionRecord]], List[Violation]]


# ---------------------------------------------------------------------------
# Example global constraints (the "Sudoku rules" for the SCBE decision observer)
# ---------------------------------------------------------------------------
def no_contradictory_route_decisions(records: List[DecisionRecord]) -> List[Violation]:
    """A route must not carry both ALLOW and DENY across the whole history (a global contradiction)."""
    by_route: Dict[str, List[int]] = {}
    for i, r in enumerate(records):
        if r.route:
            by_route.setdefault(r.route, []).append(i)
    out: List[Violation] = []
    for route, idxs in by_route.items():
        decisions = {records[i].decision for i in idxs}
        if ALLOW in decisions and DENY in decisions:
            out.append(Violation("no_contradictory_route_decisions", "route %r has both ALLOW and DENY" % route, idxs))
    return out


def escalation_must_be_resolved(records: List[DecisionRecord]) -> List[Violation]:
    """An ESCALATE on an input must be resolved by a LATER ALLOW/DENY that names it (meta['resolves']).
    Unresolved-at-end is a whole-history fact (you cannot know at the ESCALATE whether it resolves)."""
    out: List[Violation] = []
    for i, r in enumerate(records):
        if r.decision == ESCALATE:
            resolved_at = [j for j, rr in enumerate(records) if j > i and rr.meta.get("resolves") == r.input_id]
            if not resolved_at:
                out.append(Violation("escalation_must_be_resolved", "escalation %r never resolved" % r.input_id, [i]))
    return out


def no_post_refusal_success(records: List[DecisionRecord]) -> List[Violation]:
    """If an input_id was REFUSED, the same input_id must not later appear as ALLOW (legitimacy of the
    later record depends on an earlier one with no forward link -- a genuinely global fact)."""
    refused = {r.input_id for r in records if r.decision == REFUSED}
    out: List[Violation] = []
    for i, r in enumerate(records):
        if r.decision == ALLOW and r.input_id in refused:
            first = next(j for j, rr in enumerate(records) if rr.input_id == r.input_id and rr.decision == REFUSED)
            out.append(
                Violation("no_post_refusal_success", "%r ran ALLOW after being REFUSED" % r.input_id, [first, i])
            )
    return out


DEFAULT_CONSTRAINTS: List[Constraint] = [
    no_contradictory_route_decisions,
    escalation_must_be_resolved,
    no_post_refusal_success,
]


def global_violations(records: List[DecisionRecord], constraints: Optional[List[Constraint]] = None) -> List[Violation]:
    out: List[Violation] = []
    for c in constraints or DEFAULT_CONSTRAINTS:
        out.extend(c(records))
    return out


def is_admissible(records: List[DecisionRecord], constraints: Optional[List[Constraint]] = None) -> bool:
    return not global_violations(records, constraints)


# ---------------------------------------------------------------------------
# FAIR Markovian baseline: a forward observer that is as strong as possible WITHOUT revisiting a
# committed decision. It keeps running sets (refused-so-far, route-decisions-so-far) and flags a conflict
# the instant a NEW record contradicts the past -- but it can only ever blame the CURRENT (latest)
# record, because the earlier one is already committed. This is the honest baseline the skeptic demanded.
# ---------------------------------------------------------------------------
def markovian_committed_conflicts(records: List[DecisionRecord]) -> List[Tuple[int, str]]:
    """Forward pass with running state. Returns (index_of_the_LATE_record, reason) for each conflict the
    forward observer can notice -- always blaming the latest arrival, never able to revisit the earlier."""
    seen_route: Dict[str, set] = {}
    refused: set = set()
    out: List[Tuple[int, str]] = []
    for i, r in enumerate(records):
        if r.route:
            prior = seen_route.setdefault(r.route, set())
            if (r.decision == DENY and ALLOW in prior) or (r.decision == ALLOW and DENY in prior):
                out.append(
                    (i, "forward: %r contradicts an already-committed decision on route %r" % (r.decision, r.route))
                )
            prior.add(r.decision)
        if r.decision == ALLOW and r.input_id in refused:
            out.append((i, "forward: %r ran ALLOW after an earlier REFUSED" % r.input_id))
        if r.decision == REFUSED:
            refused.add(r.input_id)
    return out


# ---------------------------------------------------------------------------
# THE METRIC: the retroactive-consistency gap
# ---------------------------------------------------------------------------
@dataclass
class GapReport:
    forward_conflicts: int  # conflicts the FAIR forward observer can flag (always at the late record)
    global_violations: int  # violations the all-at-once pass finds over the whole history
    retroactive_gap: int  # decisions the global view RETRACTS that no forward observer could have caught
    retracted_indices: List[int]  # the EARLIER records the global view invalidates (the jump-back seeds)
    detail: List[Violation]


def retroactive_consistency_gap(
    records: List[DecisionRecord], constraints: Optional[List[Constraint]] = None
) -> GapReport:
    """Measure, deterministically, the gap between a FAIR forward observer and the all-at-once observer.

    The retroactive gap counts ONLY records implicated in a violation that the FAIR forward observer
    could NOT have flagged -- i.e. genuinely future-dependent ones (a fact that lies in the future of
    the offending record, like an escalation that is never resolved). A contradiction the fair forward
    observer already catches at the late record (it keeps running sets) is EXCLUDED: it is forward-
    detectable, so counting it would be the inflated 'weak baseline' number the skeptic rejected.
    """
    viols = global_violations(records, constraints)
    forward = markovian_committed_conflicts(records)
    forward_flagged = {i for i, _ in forward}  # late indices the fair forward observer already catches
    retracted: set = set()
    future_dependent: List[Violation] = []
    for v in viols:
        if max(v.involved) in forward_flagged:
            continue  # forward catches this one -> NOT a global-only gain (honest, no inflation)
        future_dependent.append(v)
        retracted.update(v.involved)  # only-knowable-globally records (the jump-back seeds)
    return GapReport(
        forward_conflicts=len(forward),
        global_violations=len(viols),
        retroactive_gap=len(retracted),
        retracted_indices=sorted(retracted),
        detail=future_dependent,
    )


# ---------------------------------------------------------------------------
# Conflict-Directed Backjumping (CBJ): the jump-back target + the repair loop
# ---------------------------------------------------------------------------
def earliest_repair_point(
    records: List[DecisionRecord], constraints: Optional[List[Constraint]] = None
) -> Optional[int]:
    """The CBJ jump-back target: the earliest record index across ALL current conflict sets. Re-deciding
    from here (not one step back) is the smallest jump that can resolve a future-dependent inconsistency.
    None if the history is already admissible."""
    viols = global_violations(records, constraints)
    if not viols:
        return None
    return min(v.earliest_index for v in viols)


# ---------------------------------------------------------------------------
# MINIMAL UNSAT CORE (the crisp explanation a SAT solver's get_core() gives -- in pure Python, zero deps).
# A violation's `involved` is a SUFFICIENT conflict set, but not always minimal: a route contradiction names
# EVERY record on the route. minimal_core shrinks it (deletion-based / QuickXplain) to the smallest subset
# that still triggers the same constraint -- e.g. one ALLOW + one DENY. Keeps the auditability moat: it is a
# few lines you can read, not an opaque solver core.
#
# IMPORTANT, and the reason we keep BOTH: a minimal core may legitimately DROP the earliest record (it can
# keep a later ALLOW over the first one), so it is the wrong thing for the jump-back. The repair target stays
# `earliest_repair_point` over the FULL conflict (the root cause); the minimal core is for the EXPLANATION.
# ---------------------------------------------------------------------------
def minimal_core(records: List[DecisionRecord], constraint: Constraint, violation: Violation) -> List[int]:
    """The minimal subset of `violation.involved` that still triggers `constraint` (run on that sub-history).
    Deletion-based: drop a record; if the constraint still fires without it, it was non-essential. Deterministic
    (scans in sorted index order). Returns record indices into `records` -- a crisp, auditable explanation."""
    core = sorted(violation.involved)
    i = 0
    while i < len(core):
        trial = core[:i] + core[i + 1 :]
        sub = [records[j] for j in trial]
        if trial and constraint(sub):  # still inconsistent without records[core[i]] -> it was non-essential
            core = trial  # do not advance: re-test the record now sitting at position i
        else:
            i += 1
    return core


def minimal_cores(
    records: List[DecisionRecord], constraints: Optional[List[Constraint]] = None
) -> List[Dict[str, Any]]:
    """For every current violation: its minimal core (the crisp explanation) AND the jump-back target (the
    earliest of the FULL conflict -- the root cause, which the minimal core may not contain). The honest
    pairing -- minimal for showing the user, full-earliest for the repair."""
    out: List[Dict[str, Any]] = []
    for c in constraints or DEFAULT_CONSTRAINTS:
        for v in c(records):
            out.append(
                {
                    "rule": v.rule,
                    "full_conflict": sorted(v.involved),
                    "minimal_core": minimal_core(records, c, v),
                    "jumpback_target": v.earliest_index,  # root cause = earliest of the FULL conflict
                }
            )
    return out


# a repair policy: given the records and the jump-back index, return a NEW decision for that record
# (or None to give up on that node). The module supplies the mechanism; the policy is the caller's.
RepairPolicy = Callable[[List[DecisionRecord], int], Optional[str]]


@dataclass
class RepairTrace:
    admissible: bool
    jumps: List[int]  # the sequence of jump-back targets taken (CBJ history)
    iterations: int
    records: List[DecisionRecord]


# a rewrite hook: called the instant before a committed decision is overwritten, with
# (target_index, old_decision, new_decision). This is the ONE place the repair loop discards information
# (the old decision) -- the metered and reversible variants pass a hook here to charge it / log it.
RewriteHook = Callable[[int, str, str], None]


def _resolve_with_hook(
    records: List[DecisionRecord],
    repair: RepairPolicy,
    constraints: Optional[List[Constraint]],
    max_iterations: int,
    on_rewrite: Optional[RewriteHook],
) -> RepairTrace:
    """Shared CBJ repair core. Identical to the public resolve_by_jumpback, but fires on_rewrite at the one
    point a decision is overwritten -- so callers can meter (charge the erased old decision) or make it
    reversible (log the old decision) without forking the loop logic."""
    recs = [DecisionRecord(r.seq, r.input_id, r.decision, r.route, r.verdict, dict(r.meta)) for r in records]
    jumps: List[int] = []
    seen: set = set()
    for it in range(max_iterations):
        if is_admissible(recs, constraints):
            return RepairTrace(True, jumps, it, recs)
        target = earliest_repair_point(recs, constraints)
        if target is None:
            return RepairTrace(True, jumps, it, recs)
        signature = (target, tuple((r.decision, r.route) for r in recs))
        if signature in seen:  # oscillation: re-deciding here keeps reproducing a seen state -> stop
            break
        seen.add(signature)
        new_decision = repair(recs, target)
        if new_decision is None:  # policy gives up on this node
            break
        old_decision = recs[target].decision
        if new_decision == old_decision:
            # re-affirming the SAME value erases no information (Landauer charge 0) and cannot resolve a
            # conflict this node is part of -- earliest_repair_point only returns nodes in a conflict set.
            # So it is a no-op with no progress: stop here rather than bill a phantom erase. This keeps a
            # jump == an undo-log entry == a charge == one genuine OVERWRITE (the metered meter is honest).
            break
        if on_rewrite is not None:
            on_rewrite(target, old_decision, new_decision)  # the irreversible discard happens here
        jumps.append(target)
        recs[target].decision = new_decision
    return RepairTrace(is_admissible(recs, constraints), jumps, len(jumps), recs)


def resolve_by_jumpback(
    records: List[DecisionRecord],
    repair: RepairPolicy,
    constraints: Optional[List[Constraint]] = None,
    max_iterations: int = 64,
) -> RepairTrace:
    """Retroactive repair loop (CBJ). While the whole history is inadmissible: find the earliest conflict
    record, ask the policy for a new decision there, apply it, and re-solve the WHOLE history (a later
    fix can expose a new earlier conflict -- cascading repair). An oscillation guard stops if a state
    repeats. This is the 'inferred retroactive jump-back to the error's root cause' loop, the all-at-once
    upgrade to a Markovian one-step rewind."""
    return _resolve_with_hook(records, repair, constraints, max_iterations, None)


# ---------------------------------------------------------------------------
# THERMODYNAMIC COST OF A SOLVE: wire the Landauer ledger (reversible_circuit) into the repair loop.
# A re-decision OVERWRITES a committed decision -> it erases the old decision's information -> Landauer
# charges it. Logging the old decision instead (an undo-log = the tape) erases nothing during the solve,
# but pays in SPACE (Bennett's reversible-computing space-for-energy trade). This makes the substrate's
# "energy-min, not linear" claim a measured number: the erasure cost scales with the CONFLICT DEPTH (the
# CBJ jump-backs), not the history length -- a single root re-decide that cascades is paid for once.
# ---------------------------------------------------------------------------
def decision_bits(domain_size: int) -> int:
    """Information content (bits) of one decision drawn from a domain of `domain_size` options: ceil(log2).
    A decision is from a SMALL domain (ALLOW/DENY/ESCALATE/REFUSED -> 2 bits), NOT a 64-bit word -- so the
    Landauer charge per overwrite is honest, not inflated to a register width."""
    if domain_size <= 1:
        return 0
    return max(1, math.ceil(math.log2(domain_size)))


def resolve_by_jumpback_metered(
    records: List[DecisionRecord],
    repair: RepairPolicy,
    constraints: Optional[List[Constraint]] = None,
    max_iterations: int = 64,
    domain_size: int = 4,
    temperature_k: float = ROOM_T_K,
) -> Tuple[RepairTrace, EnergyLedger]:
    """The IRREVERSIBLE solve: each re-decision overwrites a committed decision, so the ledger charges the
    erased old decision (decision_bits(domain_size) bits at the Landauer floor). Returns (trace, ledger)."""
    ledger = EnergyLedger(temperature_k=temperature_k)
    bits = decision_bits(domain_size)

    def charge(target: int, old: str, new: str) -> None:
        ledger.erase("re-decide #%d (%s->%s)" % (target, old, new), bits)  # discard the old decision

    trace = _resolve_with_hook(records, repair, constraints, max_iterations, charge)
    return trace, ledger


def resolve_by_jumpback_reversible(
    records: List[DecisionRecord],
    repair: RepairPolicy,
    constraints: Optional[List[Constraint]] = None,
    max_iterations: int = 64,
) -> Tuple[RepairTrace, List[Tuple[int, str]]]:
    """The REVERSIBLE solve: same repair, but every overwrite PRESERVES the old decision on an undo-log
    instead of erasing it. Erases nothing during the solve (0 Landauer), at the cost of a growing log (the
    tape). Returns (trace, undo_log); unwind(trace.records, undo_log) restores the exact pre-repair history.

    HONEST: this RELOCATES the energy into space, it does not abolish it. Reclaiming the log later (erasing
    it) pays the same Landauer cost back -- unless you uncompute it (Bennett), which loses the repaired
    state. Free only while you keep the log."""
    undo: List[Tuple[int, str]] = []

    def log_old(target: int, old: str, new: str) -> None:
        undo.append((target, old))  # preserve, do not erase -> the step is reversible

    trace = _resolve_with_hook(records, repair, constraints, max_iterations, log_old)
    return trace, undo


def unwind(records: List[DecisionRecord], undo: List[Tuple[int, str]]) -> List[DecisionRecord]:
    """Run a reversible repair BACKWARD: restore the logged old decisions in reverse order, recovering the
    exact pre-repair history. Proof that the reversible solve lost no information (run-then-unwind == start)."""
    recs = [DecisionRecord(r.seq, r.input_id, r.decision, r.route, r.verdict, dict(r.meta)) for r in records]
    for target, old in reversed(undo):
        recs[target].decision = old
    return recs


@dataclass
class SolveEnergy:
    rewrites: int  # number of irreversible re-decisions the CBJ solve made == conflict depth
    history_len: int  # number of records in the history
    bits_per_decision: int  # decision_bits(domain_size) -- honest small-domain info content
    irreversible_bits_erased: int  # rewrites * bits_per_decision
    irreversible_joules: float  # the Landauer FLOOR the dissipating (overwrite) solve pays (lower bound)
    reversible_joules: float  # 0.0 -- the reversible (undo-log) solve erases nothing during the solve
    reversible_undo_log_entries: int  # the SPACE paid instead (== rewrites): Bennett space-for-energy
    naive_linear_bits: int  # cost if EVERY record were re-decided (linear in history) -- the ceiling
    energy_is_sublinear: bool  # rewrites < history_len: the solve paid for conflict depth, not length


def energy_of_solve(
    records: List[DecisionRecord],
    repair: RepairPolicy,
    constraints: Optional[List[Constraint]] = None,
    max_iterations: int = 64,
    domain_size: int = 4,
    temperature_k: float = ROOM_T_K,
) -> SolveEnergy:
    """Measure the thermodynamic cost of repairing this history both ways. The irreversible solve pays the
    Landauer floor per overwritten decision; the reversible solve pays 0 (trading it for the undo-log). The
    load-bearing, measured claim: the erasure count == CBJ conflict depth, which is independent of history
    length -- so for a fixed-depth root conflict the energy is FLAT as the history grows (not linear)."""
    m_trace, ledger = resolve_by_jumpback_metered(
        records, repair, constraints, max_iterations, domain_size, temperature_k
    )
    _r_trace, undo = resolve_by_jumpback_reversible(records, repair, constraints, max_iterations)
    bits = decision_bits(domain_size)
    n = len(records)
    return SolveEnergy(
        rewrites=len(m_trace.jumps),
        history_len=n,
        bits_per_decision=bits,
        irreversible_bits_erased=ledger.bits_erased,
        irreversible_joules=ledger.joules(),
        reversible_joules=0.0,
        reversible_undo_log_entries=len(undo),
        naive_linear_bits=n * bits,
        energy_is_sublinear=len(m_trace.jumps) < n,
    )


def _root_conflict_history(n: int) -> List[DecisionRecord]:
    """A history of n records where record 0 ALLOWs route "r" and the LAST record DENYs route "r" -- a
    single root contradiction whose fix is one re-decision at index 0, regardless of n. The middle records
    are CLEAN ALLOWs on their own unique routes (each route appears once -> no contradiction, no unresolved
    escalation), so the ONLY violation is the root. This is what shows the erasure cost is flat in n."""
    recs = [DecisionRecord(0, "in0", ALLOW, route="r")]
    recs += [DecisionRecord(i, "in%d" % i, ALLOW, route="r%d" % i) for i in range(1, n - 1)]
    recs += [DecisionRecord(n - 1, "in%d" % (n - 1), DENY, route="r")]
    return recs


def demo() -> Dict[str, object]:
    # flip the root ALLOW to DENY to clear the contradiction (the policy the caller would supply)
    def repair(recs: List[DecisionRecord], target: int) -> Optional[str]:
        return DENY if recs[target].decision == ALLOW else None

    small = _root_conflict_history(5)
    big = _root_conflict_history(500)
    e_small = energy_of_solve(small, repair)
    e_big = energy_of_solve(big, repair)

    # reversible solve loses nothing: run then unwind == the exact start
    trace, undo = resolve_by_jumpback_reversible(big, repair)
    restored = unwind(trace.records, undo)
    reversible_lossless = [r.decision for r in restored] == [r.decision for r in big]

    return {
        "small_repaired": is_admissible(resolve_by_jumpback(small, repair).records),
        "energy_flat_as_history_grows": e_small.irreversible_bits_erased == e_big.irreversible_bits_erased,
        "small_erased_bits": e_small.irreversible_bits_erased,
        "big_erased_bits": e_big.irreversible_bits_erased,
        "history_grew_100x": e_big.history_len == 100 * e_small.history_len,
        "reversible_zero_erasure_in_solve": e_big.reversible_joules == 0.0,  # free only while the log is kept
        "reversible_pays_in_space": e_big.reversible_undo_log_entries == e_big.rewrites,
        "reversible_lossless_unwind": reversible_lossless,
        "_e_small": e_small,
        "_e_big": e_big,
    }


def main() -> int:
    d = demo()
    e_s, e_b = d["_e_small"], d["_e_big"]
    print("OBSERVER ENERGY -- the all-at-once solve's thermodynamic cost (Landauer ledger wired in)")
    print(
        "  small history (n=%d): repaired with %d re-decide(s), erased %d bits, %.3e J"
        % (e_s.history_len, e_s.rewrites, e_s.irreversible_bits_erased, e_s.irreversible_joules)
    )
    print(
        "  big   history (n=%d): repaired with %d re-decide(s), erased %d bits, %.3e J"
        % (e_b.history_len, e_b.rewrites, e_b.irreversible_bits_erased, e_b.irreversible_joules)
    )
    print(
        "  => history grew 100x but ERASURE COST IS FLAT (%s): energy ~ conflict depth, NOT length."
        % d["energy_flat_as_history_grows"]
    )
    print(
        "  reversible solve: %.3e J erased, %d undo-log entries (space-for-energy, Bennett); lossless unwind: %s"
        % (e_b.reversible_joules, e_b.reversible_undo_log_entries, d["reversible_lossless_unwind"])
    )
    print(
        "  honest: Landauer FLOOR (~2.87e-21 J/bit), decision=%d bit(s) not 64; reversible defers cost into the log."
        % e_b.bits_per_decision
    )
    print("  (the floor is a thermodynamic lower bound; a real chip dissipates ~1e9x more -- not a power estimate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
