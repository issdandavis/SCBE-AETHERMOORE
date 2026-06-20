"""Chapter 3 — Decision Records.

Validates that every Python example in
`book/ai-governance-fundamentals/chapter-03-decision-records.md` runs and
produces the JSON the chapter promises, byte-for-byte (after whitespace
normalization).
"""

from __future__ import annotations

from tests.book._runner import run_chapter


def test_chapter_03_examples_all_run() -> None:
    result = run_chapter("ai-governance-fundamentals", 3)
    assert result["examples_failed"] == 0
    assert result["examples_run"] >= 2, "chapter 3 must ship the clean-ALLOW and the hot-ESCALATE examples"


def test_chapter_03_record_is_replayable_from_logged_fields() -> None:
    """A reviewer with the logged d and pd values must be able to reconstruct
    H exactly. This is the chapter's "the record is replayable" claim."""
    from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
        HamiltonianTracker,
    )

    tracker = HamiltonianTracker()
    h_actual = tracker.update([0.9, 0.1] * 10 + [0.5], {"aggressive"})
    d_logged = tracker._cosine_distance([0.9, 0.1] * 10 + [0.5], tracker._centroid)
    pd_logged = 1.0  # one entry, one unsafe

    h_reconstructed = 1.0 / (1.0 + d_logged + 2.0 * pd_logged)
    assert (
        abs(h_actual - h_reconstructed) < 1e-9
    ), f"replay broken: actual H={h_actual} but logged-fields H={h_reconstructed}"
