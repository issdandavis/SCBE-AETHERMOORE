"""Chapter 2 — The Four-Tier Risk Decision.

Validates that every Python example in
`book/ai-governance-fundamentals/chapter-02-risk-tiers.md` runs against the
live SCBE codebase and produces output matching the chapter's claims.
"""

from __future__ import annotations

from tests.book._runner import run_chapter


def test_chapter_02_examples_all_run() -> None:
    result = run_chapter("ai-governance-fundamentals", 2)
    assert result["examples_failed"] == 0
    assert result["examples_run"] >= 1, "chapter 2 must ship at least the four-case demo"


def test_chapter_02_tier_ladder_is_monotone_in_h() -> None:
    """Higher H must never produce a lower (more punitive) tier."""

    def tier_for(h: float) -> str:
        if h > 0.6:
            return "ALLOW"
        if h > 0.4:
            return "QUARANTINE"
        if h > 0.2:
            return "ESCALATE"
        return "DENY"

    rank = {"ALLOW": 3, "QUARANTINE": 2, "ESCALATE": 1, "DENY": 0}
    # Sweep H from 0 to 1 in 0.05 steps; rank must be non-decreasing.
    last_rank = -1
    h = 0.0
    while h <= 1.0:
        r = rank[tier_for(h)]
        assert r >= last_rank, f"tier ranking went backwards at H={h:.4f}"
        last_rank = r
        h += 0.05


def test_chapter_02_recovery_outscores_persistent_drift() -> None:
    """A slip after a clean history must score strictly higher than the
    same slip after a half-unsafe window. This is the chapter's
    "recovery is real" claim."""
    from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
        HamiltonianTracker,
    )

    clean = HamiltonianTracker()
    for _ in range(9):
        clean.update([0.5] * 21, set())
    h_recovery = clean.update([0.7, 0.3] * 10 + [0.5], {"aggressive"})

    drifted = HamiltonianTracker()
    for _ in range(5):
        drifted.update([0.5] * 21, set())
    for _ in range(5):
        drifted.update([0.5] * 21, {"aggressive"})
    h_drifted = drifted.update([0.7, 0.3] * 10 + [0.5], {"aggressive"})

    assert h_recovery > h_drifted, (
        f"chapter claim broken: recovery H={h_recovery:.4f} should exceed " f"persistent drift H={h_drifted:.4f}"
    )
