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

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

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


# a repair policy: given the records and the jump-back index, return a NEW decision for that record
# (or None to give up on that node). The module supplies the mechanism; the policy is the caller's.
RepairPolicy = Callable[[List[DecisionRecord], int], Optional[str]]


@dataclass
class RepairTrace:
    admissible: bool
    jumps: List[int]  # the sequence of jump-back targets taken (CBJ history)
    iterations: int
    records: List[DecisionRecord]


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
        jumps.append(target)
        recs[target].decision = new_decision
    return RepairTrace(is_admissible(recs, constraints), jumps, len(jumps), recs)
