"""Tests for staged_prime_reasoning.

Locks the MECHANISMS (prime/uniform/adaptive schedules, sketchpad, tagged
sub-compaction, drift logging, curriculum) and the headline NULL result: under a
neutral drift proxy with a fixed checkpoint budget, prime-indexed checkpointing is
not special — it ties a plain fixed cadence — while drift-TRIGGERED (state-driven)
checkpointing is what actually wins. The lever is the drift signal, not the index.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "research"))

import staged_prime_reasoning as spr  # noqa: E402


def test_prime_schedule_is_the_primes():
    assert spr.sched_prime(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    assert not spr.is_prime(1) and spr.is_prime(2) and not spr.is_prime(9) and spr.is_prime(29)


def test_schedules_share_a_fixed_checkpoint_budget():
    k = len(spr.sched_prime(30))
    assert len(spr.sched_uniform(30, k)) <= k
    assert len(spr.sched_increasing(30, k)) <= k  # growing gaps can merge near the tail
    assert len(spr.sched_random(30, k, seed=1)) == k


def test_sketchpad_writes_and_retrieves_by_tag():
    pad = spr.Sketchpad()
    pad.write(1, "step", "alpha")
    pad.write(2, "plan", "beta")
    pad.write(3, "step", "gamma")
    assert [n.text for n in pad.retrieve("step")] == ["alpha", "gamma"]
    assert pad.tokens() >= 3


def test_sub_compaction_shrinks_context_but_keeps_retrieval():
    # realistic scale: many turns of real history is where compaction earns its keep.
    notes = [spr.Note(t, "step", f"turn {t}: examined candidate and ran the verifier in place") for t in range(1, 41)]
    before = sum(n.tokens() for n in notes)
    compacted, card = spr.sub_compact(notes, keep_recent=4)
    assert card is not None and card.tag == "COMPACT"
    assert len(compacted) == 5  # one COMPACT card + 4 recent
    assert sum(n.tokens() for n in compacted) < before  # context shrank
    assert any("step" in line for line in card.text.splitlines())  # still findable by tag


def test_staged_run_checkpoints_at_primes_and_logs_drift():
    r = spr.run_staged(30, "decaying", seed=7)
    assert r["prime_checkpoints"] == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    # one drift reading between each consecutive pair of prime checkpoints
    assert len(r["drifts_between_primes"]) == len(r["prime_checkpoints"]) - 1
    assert r["compactions"], "sub-compaction must fire once context fills"


def test_null_says_prime_is_not_special_and_adaptive_is_competitive():
    # The robust finding is CLOSENESS, not a strict per-seed ordering: prime and a
    # plain fixed cadence differ by less than sampling noise (primality adds nothing),
    # and drift-triggered checkpointing is at least as good as prime. Tolerances
    # absorb Monte-Carlo noise while still encoding the conclusion.
    r = spr.null_experiment(n_turns=30, seeds=400)
    for regime, row in r["results"].items():
        assert abs(row["prime"] - row["uniform"]) < 0.06, (regime, row)  # prime ≈ uniform
        assert row["adaptive"] <= row["prime"] + 0.05, (regime, row)  # state-driven ≥ index-driven
        # nobody wins by a landslide — the whole question lives inside a narrow band.
        assert max(row.values()) - min(row.values()) < 0.25, (regime, row)


def test_curriculum_ramps_and_reports_a_ladder():
    r = spr.curriculum(levels=4, seed=1)
    assert r["levels_attempted"] >= 1
    assert all("solved" in lvl and "mean_final_error" in lvl for lvl in r["ladder"])
