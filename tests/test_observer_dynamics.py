"""Tests for observer_dynamics -- the decision-semantics all-at-once observer (CSP / CBJ).

The load-bearing, skeptic-grade assertions:
  * the retroactive gap is NON-zero for a genuinely FUTURE-DEPENDENT violation (escalation never resolved
    -- unknowable at the escalate);
  * the retroactive gap is ZERO for a forward-DETECTABLE contradiction (the fair forward baseline catches
    it) -- i.e. no 'weak baseline' inflation;
  * Conflict-Directed Backjumping targets the EARLIEST (root-cause) record, beating a one-step rewind;
  * the metric is deterministic; the repair loop has an oscillation guard.
"""

from __future__ import annotations

from python.scbe.observer_dynamics import (
    ALLOW,
    DENY,
    ESCALATE,
    REFUSED,
    DecisionRecord,
    earliest_repair_point,
    is_admissible,
    markovian_committed_conflicts,
    resolve_by_jumpback,
    retroactive_consistency_gap,
)


def _r(seq, decision, route=None, input_id=None, **meta):
    return DecisionRecord(seq=seq, input_id=input_id or ("i%d" % seq), decision=decision, route=route, meta=meta)


# ---- the future-dependent gap is real -----------------------------------------------------------
def test_future_dependent_violation_counts_toward_the_gap():
    # an ESCALATE that is never resolved: a forward observer cannot know at the escalate that nothing
    # later resolves it -> the all-at-once view retracts it; the fair forward observer flags nothing.
    recs = [_r(0, ESCALATE, route="safety", input_id="a"), _r(1, ALLOW, route="other", input_id="b")]
    gap = retroactive_consistency_gap(recs)
    assert gap.retroactive_gap >= 1
    assert 0 in gap.retracted_indices
    assert gap.forward_conflicts == 0  # the fair forward observer could not have caught it


def test_forward_detectable_contradiction_has_zero_gap_no_inflation():
    # ALLOW then DENY on the same route: the FAIR forward observer catches it at the late record (running
    # set), so it must NOT inflate the retroactive gap -- this is the 'block-offload +24' honesty bar.
    recs = [_r(0, ALLOW, route="deploy"), _r(1, DENY, route="deploy")]
    gap = retroactive_consistency_gap(recs)
    assert gap.global_violations >= 1  # the global view still sees the contradiction
    assert gap.forward_conflicts >= 1  # but so does the fair forward observer
    assert gap.retroactive_gap == 0  # ...so it is NOT counted as a global-only gain


# ---- CBJ jumps to the root cause, beating a one-step rewind -------------------------------------
def test_cbj_targets_the_earliest_root_cause_not_one_step_back():
    # contradiction surfaces at index 2 but its root is index 0; a one-step rewind would target index 1.
    recs = [_r(0, ALLOW, route="deploy"), _r(1, ALLOW, route="unrelated"), _r(2, DENY, route="deploy")]
    target = earliest_repair_point(recs)
    assert target == 0  # CBJ -> the root, not max(involved)-1 == 1 (the one-step-rewind target)


def test_jumpback_repairs_the_history_at_the_root():
    recs = [_r(0, ALLOW, route="deploy"), _r(1, ALLOW, route="unrelated"), _r(2, DENY, route="deploy")]

    def flip_allow_to_deny(rs, idx):
        return DENY if rs[idx].decision == ALLOW else None

    trace = resolve_by_jumpback(recs, flip_allow_to_deny)
    assert trace.admissible is True
    assert trace.jumps and trace.jumps[0] == 0  # jumped to the root cause
    assert is_admissible(trace.records)
    assert recs[0].decision == ALLOW  # original input not mutated (repair worked on a copy)


# ---- honesty: determinism, clean case, oscillation guard ----------------------------------------
def test_clean_history_is_admissible_zero_gap():
    recs = [_r(0, ALLOW, route="deploy"), _r(1, ALLOW, route="deploy")]
    assert is_admissible(recs)
    assert retroactive_consistency_gap(recs).retroactive_gap == 0


def test_metric_is_deterministic():
    recs = [_r(0, ESCALATE, input_id="a"), _r(1, ALLOW, route="r"), _r(2, DENY, route="r")]
    a = retroactive_consistency_gap(recs)
    b = retroactive_consistency_gap(recs)
    assert (a.retroactive_gap, a.retracted_indices, a.forward_conflicts) == (
        b.retroactive_gap,
        b.retracted_indices,
        b.forward_conflicts,
    )


def test_jumpback_oscillation_guard_terminates():
    # a policy that never actually resolves the conflict must not loop forever
    recs = [_r(0, ALLOW, route="deploy"), _r(1, DENY, route="deploy")]

    def no_op(rs, idx):
        return rs[idx].decision  # re-assign the same value -> never fixes -> must be caught by the guard

    trace = resolve_by_jumpback(recs, no_op, max_iterations=64)
    assert trace.admissible is False
    assert trace.iterations < 64  # stopped by the oscillation guard, not the iteration cap


def test_post_refusal_success_is_forward_caught_not_inflated():
    # REFUSED then ALLOW on the same input_id: the fair forward observer catches it -> zero gap
    recs = [_r(0, REFUSED, input_id="x"), _r(1, ALLOW, input_id="x")]
    gap = retroactive_consistency_gap(recs)
    assert gap.forward_conflicts >= 1 and gap.retroactive_gap == 0
    assert any(i == 1 for i, _ in markovian_committed_conflicts(recs))
