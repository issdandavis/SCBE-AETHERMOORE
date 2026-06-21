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
    decision_bits,
    earliest_repair_point,
    energy_of_solve,
    is_admissible,
    markovian_committed_conflicts,
    resolve_by_jumpback,
    resolve_by_jumpback_metered,
    resolve_by_jumpback_reversible,
    retroactive_consistency_gap,
    unwind,
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
    # a policy that genuinely TOGGLES the root (ALLOW<->DENY) without ever resolving reproduces a seen
    # global state; the SIGNATURE guard (not the same-value no-op break) must stop it. Route has three
    # records so toggling node 0 alone can never clear the ALLOW/DENY contradiction -> it cycles.
    recs = [_r(0, ALLOW, route="deploy"), _r(1, DENY, route="deploy"), _r(2, ALLOW, route="deploy")]

    def toggle(rs, idx):
        return DENY if rs[idx].decision == ALLOW else ALLOW  # always a REAL change -> genuine oscillation

    trace = resolve_by_jumpback(recs, toggle, max_iterations=64)
    assert trace.admissible is False
    assert 0 < trace.iterations < 64  # stopped by the oscillation guard after cycling, not the cap


def test_post_refusal_success_is_forward_caught_not_inflated():
    # REFUSED then ALLOW on the same input_id: the fair forward observer catches it -> zero gap
    recs = [_r(0, REFUSED, input_id="x"), _r(1, ALLOW, input_id="x")]
    gap = retroactive_consistency_gap(recs)
    assert gap.forward_conflicts >= 1 and gap.retroactive_gap == 0
    assert any(i == 1 for i, _ in markovian_committed_conflicts(recs))


# ---- energy ledger: the solve's thermodynamic cost (Landauer wired into the repair loop) ---------
def _flip(rs, idx):
    return DENY if rs[idx].decision == ALLOW else None


def _root_conflict(n):
    # record 0 ALLOWs route r, the last DENYs it -- one root contradiction fixed by ONE re-decide at 0,
    # regardless of n. Middle records are CLEAN ALLOWs on unique routes (no contradiction, no unresolved
    # escalation) so the ONLY violation is the root -- the repair must actually COMPLETE, not give up.
    recs = [DecisionRecord(0, "in0", ALLOW, route="r")]
    recs += [DecisionRecord(i, "in%d" % i, ALLOW, route="r%d" % i) for i in range(1, n - 1)]
    recs += [DecisionRecord(n - 1, "in%d" % (n - 1), DENY, route="r")]
    return recs


def test_decision_bits_is_small_domain_not_a_64bit_word():
    # honesty: overwriting a decision erases log2(domain) bits, NOT a register width
    assert decision_bits(4) == 2  # ALLOW/DENY/ESCALATE/REFUSED
    assert decision_bits(2) == 1
    assert decision_bits(1) == 0  # a single-option domain carries no information
    assert decision_bits(5) == 3  # ceil(log2(5))


def test_metered_solve_charges_one_overwrite_and_repairs():
    recs = _root_conflict(4)
    trace, ledger = resolve_by_jumpback_metered(recs, _flip, domain_size=4)
    assert trace.admissible is True
    assert len(trace.jumps) == 1  # one root re-decide cleared it
    assert ledger.bits_erased == 2  # one overwrite * decision_bits(4)
    assert ledger.joules() > 0.0  # the irreversible discard pays the Landauer floor


def test_energy_is_flat_as_history_grows_not_linear():
    # THE load-bearing claim: the erasure cost is the CONFLICT DEPTH (one root re-decide), independent of
    # history length. Grow the history 100x and the bits erased / joules must NOT change.
    # GUARD: the repair must actually COMPLETE (admissible) -- a solve that BAILS early would also look
    # "flat" but for a dishonest reason. Assert both histories are genuinely repaired.
    assert resolve_by_jumpback_metered(_root_conflict(5), _flip)[0].admissible is True
    assert resolve_by_jumpback_metered(_root_conflict(500), _flip)[0].admissible is True
    e_small = energy_of_solve(_root_conflict(5), _flip)
    e_big = energy_of_solve(_root_conflict(500), _flip)
    assert e_big.history_len == 100 * e_small.history_len  # the history really did grow 100x
    assert e_small.rewrites == e_big.rewrites == 1  # ...but the same single root re-decide repairs both
    assert e_small.irreversible_bits_erased == e_big.irreversible_bits_erased  # FLAT, not linear
    assert e_small.irreversible_joules == e_big.irreversible_joules
    assert e_big.energy_is_sublinear is True  # 1 rewrite << 500 records
    assert e_big.naive_linear_bits > e_big.irreversible_bits_erased  # the linear ceiling is far higher


def test_reversible_solve_erases_nothing_and_unwinds_losslessly():
    # the Bennett trade: the reversible solve pays 0 Landauer but logs the old decision (space). Running
    # the repair backward (unwind) recovers the EXACT pre-repair history -- proof nothing was lost.
    recs = _root_conflict(6)
    trace, undo = resolve_by_jumpback_reversible(recs, _flip)
    assert trace.admissible is True
    e = energy_of_solve(recs, _flip)
    assert e.reversible_joules == 0.0  # erases nothing during the solve
    assert e.reversible_undo_log_entries == e.rewrites  # the space paid instead (== the rewrites)
    restored = unwind(trace.records, undo)
    assert [r.decision for r in restored] == [r.decision for r in recs]  # lossless: run then unwind == start


def test_metered_and_reversible_reach_the_same_repaired_state():
    # both variants run the identical CBJ loop; only the bookkeeping differs -> identical final decisions
    recs = _root_conflict(8)
    m_trace, _ = resolve_by_jumpback_metered(recs, _flip)
    r_trace, _ = resolve_by_jumpback_reversible(recs, _flip)
    assert [x.decision for x in m_trace.records] == [x.decision for x in r_trace.records]
    assert m_trace.jumps == r_trace.jumps  # same jump-back targets


def test_reaffirming_same_value_halts_without_a_phantom_charge():
    # the adversarial 'overclaim' fix: re-affirming the conflicting decision (new == old) erases NO
    # information, so the meter must bill 0 and the solve must halt -- a charge == a genuine OVERWRITE.
    recs = [_r(0, ALLOW, route="deploy"), _r(1, DENY, route="deploy")]

    def reaffirm(rs, idx):
        return rs[idx].decision  # keep the same value -> nothing discarded

    trace, ledger = resolve_by_jumpback_metered(recs, reaffirm)
    assert trace.admissible is False  # nothing actually changed, so it is not repaired
    assert trace.jumps == []  # a no-op is not a jump-back
    assert ledger.bits_erased == 0  # ...and erasing nothing costs nothing (no phantom Landauer charge)


def test_energy_tracks_conflict_depth_through_a_real_cascade():
    # a genuine depth-2 cascade: fixing the root (ALLOW->ESCALATE) re-exposes a NEW conflict at the SAME
    # index (an unresolved escalation), cleared by a second re-decide (ESCALATE->DENY). The energy must be
    # TWO overwrites' worth -- and still FLAT as the history grows 100x (cost tracks depth, not length).
    def two_step(rs, idx):
        d = rs[idx].decision
        if d == ALLOW:
            return ESCALATE
        if d == ESCALATE:
            return DENY
        return None

    assert resolve_by_jumpback_metered(_root_conflict(5), two_step)[0].admissible is True  # cascade completes
    e_small = energy_of_solve(_root_conflict(5), two_step)
    e_big = energy_of_solve(_root_conflict(500), two_step)
    assert e_small.rewrites == e_big.rewrites == 2  # genuine depth-2, not the single-jump root case
    assert e_small.irreversible_bits_erased == e_big.irreversible_bits_erased == 4  # 2 overwrites * 2 bits
    assert e_big.energy_is_sublinear is True  # 2 rewrites << 500 records


def test_public_resolve_equals_metered_trace_across_paths():
    # lock the refactor: resolve_by_jumpback (None hook) must produce the SAME RepairTrace as the metered
    # solve across genuine-flip, reaffirm-no-op, and give-up policies -- any future hook-core divergence fails
    cases = [
        (_root_conflict(6), _flip),
        ([_r(0, ALLOW, route="d"), _r(1, DENY, route="d")], lambda rs, i: rs[i].decision),  # reaffirm
        ([_r(0, ALLOW, route="d"), _r(1, DENY, route="d")], lambda rs, i: None),  # give up
    ]
    for recs, pol in cases:
        pub = resolve_by_jumpback(recs, pol)
        met, _ = resolve_by_jumpback_metered(recs, pol)
        assert pub.admissible == met.admissible
        assert pub.jumps == met.jumps
        assert [r.decision for r in pub.records] == [r.decision for r in met.records]
