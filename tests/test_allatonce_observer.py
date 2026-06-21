"""allatonce_observer: a global-constraint (all-at-once) check over the SCBE observer transcript.

Tests that the whole-history constraint pass catches integrity/consistency violations the step-local
(Markovian) forward-chain seal cannot -- specifically RE-CHAINED tampers that fool the forward walk.
This is a software ANALOGY to Adlam's all-at-once physics, not physics (see the module docstring).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.allatonce_observer import (  # noqa: E402
    ObserverState,
    allatonce_violations,
    is_admissible_mosaic,
    markovian_violations,
    markovian_violations_strong,
    measure,
    rechain,
)
from python.scbe.desktop_access import default_registry  # noqa: E402


def _clean_state() -> ObserverState:
    reg = default_registry()
    reg.invoke("open_app", {"app": "files"})
    reg.invoke("run_allowed_command", {"command": "rm -rf /"}, confirm="x")  # REFUSED
    reg.invoke("open_app", {"app": "editor"})
    reg.invoke("run_allowed_command", {"command": "ls"}, confirm="user")  # ALLOWED (guarded+confirm)
    return ObserverState.from_registry(reg)


def test_clean_transcript_passes_both_observers():
    s = _clean_state()
    assert markovian_violations(s) == []  # forward chain intact
    assert is_admissible_mosaic(s) is True  # in the intersection of all global constraints
    r = measure(s)
    assert r.local_passes and r.global_passes
    assert r.extra_caught == 0  # nothing for the global view to add on a clean mosaic


def test_naive_edit_is_caught_by_BOTH_views():
    # A crude edit that does NOT re-chain breaks the forward seal -- the local view already catches it.
    s = _clean_state()
    s.records[0]["result"] = "tampered"
    assert markovian_violations(s) != []  # local catches it (seal mismatch)
    assert is_admissible_mosaic(s) is False  # global catches it too
    # this is the BASELINE case: no global ADVANTAGE here, both see it
    r = measure(s)
    assert r.local_passes is False and r.global_passes is False


def test_rechained_reorder_FOOLS_local_but_global_catches_it():
    # THE LOAD-BEARING CASE. Reorder two records, then recompute the whole seal chain so the forward
    # walk passes. The local (Markovian) observer is fooled; the all-at-once hop_monotone constraint
    # -- a fact about the WHOLE sequence, not record N vs N-1 -- still rejects it.
    s = _clean_state()
    s.records[0], s.records[2] = s.records[2], s.records[0]
    rechain(s)
    assert markovian_violations(s) == []  # forward seal FOOLED
    viols = allatonce_violations(s)
    assert viols["hop_monotone"], "global hop-order check must fire"
    assert is_admissible_mosaic(s) is False
    r = measure(s)
    assert r.local_passes is True and r.global_passes is False  # the divergence
    assert r.extra_caught > 0  # the metric: violations only the global view sees


def test_rechained_ungrounded_confirm_caught_only_globally():
    # Strip the confirm off a guarded ALLOWED record (a success that 'comes from nowhere'), re-chain.
    # The grounding constraint learns an action is GUARDED from a NEEDS_CONFIRM seen ANYWHERE in the
    # mosaic (a whole-history lookup), so the fixture includes one such record -- itself a realistic
    # transcript event (a guarded call made without confirm).
    reg = default_registry()
    reg.invoke("open_app", {"app": "files"})
    reg.invoke("run_allowed_command", {"command": "ls"})  # NEEDS_CONFIRM: establishes 'guarded' globally
    reg.invoke("run_allowed_command", {"command": "ls"}, confirm="user")  # ALLOWED (guarded+confirm)
    s = ObserverState.from_registry(reg)
    for rec in s.records:
        if rec.get("action") == "run_allowed_command" and rec.get("decision") == "ALLOWED":
            rec.pop("confirm", None)  # now an ungrounded guarded success
    rechain(s)
    assert markovian_violations(s) == []  # local fooled
    assert allatonce_violations(s)["confirm_grounding"]  # global grounding check fires
    assert measure(s).extra_caught > 0


def test_rechained_success_after_refusal_caught_only_globally():
    # Append an ALLOWED record whose (action, params) were REFUSED earlier in the SAME mosaic, then
    # re-chain. The forward observer at the new record sees nothing wrong locally; the contradicting
    # fact is an EARLIER record. The whole-history constraint catches the contradiction.
    s = _clean_state()
    # the REFUSED record was run_allowed_command {"command":"rm -rf /"} with confirm="x"
    refused = next(r for r in s.records if r.get("decision") == "REFUSED")
    forged = {
        "hop": len(s.records) + 1,
        "action": refused["action"],
        "params": refused["params"],
        "decision": "ALLOWED",
        "result": "ran: rm -rf /",
        "confirm": "x",
    }
    s.records.append(forged)
    rechain(s)
    assert markovian_violations(s) == []  # local fooled (and hop is correct, so that constraint is clean)
    v = allatonce_violations(s)
    assert v["hop_monotone"] == []  # isolate: the ONLY thing wrong is the cross-record contradiction
    assert v["no_post_refusal_success"], "global post-refusal-success check must fire"
    assert measure(s).extra_caught > 0


def test_fair_baseline_collapses_the_inflated_integrity_number():
    # The skeptic's honesty bar (the 'block-offload +24' lesson): a FAIR forward baseline (continue past
    # breaks + a LOCAL hop-successor check + running sets) ALSO catches the re-chained reorder. So at the
    # INTEGRITY layer the honest global-only gain (extra_vs_strong) collapses to 0 -- the genuine
    # all-at-once advantage is at the DECISION layer (observer_dynamics), not here.
    s = _clean_state()
    s.records[0], s.records[2] = s.records[2], s.records[0]
    rechain(s)
    r = measure(s)
    assert markovian_violations_strong(s) != []  # the fair baseline is NOT fooled by the re-chain
    assert r.extra_caught > 0  # it beats the WEAK shipped verify()...
    assert r.extra_vs_strong == 0  # ...but adds nothing over a FAIR forward baseline (honest)


def test_metric_is_deterministic():
    # The metric is a pure function of the transcript: same input -> identical report, every time.
    s1 = _clean_state()
    s1.records[0], s1.records[2] = s1.records[2], s1.records[0]
    rechain(s1)
    s2 = _clean_state()
    s2.records[0], s2.records[2] = s2.records[2], s2.records[0]
    rechain(s2)
    a, b = measure(s1), measure(s2)
    assert (a.local_count, a.global_count, a.extra_caught) == (b.local_count, b.global_count, b.extra_caught)


def test_intersection_semantics_one_failed_constraint_makes_inadmissible():
    # Adlam: reality must lie in the INTERSECTION of all constraints. One non-empty constraint =>
    # not admissible, even though every OTHER constraint is satisfied.
    s = _clean_state()
    s.records[0], s.records[2] = s.records[2], s.records[0]
    rechain(s)
    v = allatonce_violations(s)
    satisfied = [k for k, viols in v.items() if not viols]
    assert len(satisfied) >= 1  # most constraints are still happy
    assert any(v.values())  # but at least one is violated
    assert is_admissible_mosaic(s) is False  # so the mosaic is rejected
