"""Chapter 1 — The Harmonic Wall.

Validates that every Python example in
`book/ai-governance-fundamentals/chapter-01-harmonic-wall.md` runs against
the live SCBE codebase and produces output matching the chapter's claims.
The runner asserts both that no example raises and that any expected-output
block matches captured stdout line-by-line.

If this test fails, the chapter is no longer trustworthy — either the code
path the chapter describes changed or the chapter's expected output drifted.
"""

from __future__ import annotations

from tests.book._runner import run_chapter


def test_chapter_01_examples_all_run() -> None:
    result = run_chapter("ai-governance-fundamentals", 1)
    assert result["examples_failed"] == 0
    assert result["examples_run"] >= 2, "chapter 1 must ship at least the two demo examples"


def test_chapter_01_safety_score_is_bounded() -> None:
    """Chapter-level invariant beyond the examples: H is always in (0, 1]."""
    from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
        HamiltonianTracker,
    )

    tracker = HamiltonianTracker()
    # Probe a sweep of personalities so the invariant is checked across the
    # input space, not just the chapter's two named examples.
    cases = [
        [0.0] * 21,
        [0.5] * 21,
        [1.0] * 21,
        [0.9, 0.1] * 10 + [0.5],
    ]
    for personality in cases:
        for tags in (set(), {"aggressive"}, {"reckless", "deceptive"}):
            h = tracker.update(personality, tags)
            assert 0.0 < h <= 1.0, f"H out of bound: {h} for personality={personality} tags={tags}"


def test_chapter_01_drift_is_monotone() -> None:
    """A more-drifted call MUST score strictly lower than the safe baseline.

    This is the second guarantee the chapter makes. If this regresses, the
    chapter's "monotone in drift" claim is wrong and we have to retract it.
    """
    from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
        HamiltonianTracker,
    )

    tracker = HamiltonianTracker()
    h_safe = tracker.update([0.5] * 21, set())
    h_drift = tracker.update([0.9, 0.1] * 10 + [0.5], {"aggressive"})
    assert h_drift < h_safe, f"drift did not lower score: safe={h_safe} drifted={h_drift}"
