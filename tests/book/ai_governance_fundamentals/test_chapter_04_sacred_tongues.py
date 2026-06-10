"""Chapter 4 — Sacred Tongues weighting.

Validates that every Python example in
`book/ai-governance-fundamentals/chapter-04-sacred-tongues.md` runs against
the live LanguesMetric and produces output matching the chapter's claims.
"""

from __future__ import annotations

from tests.book._runner import run_chapter


def test_chapter_04_examples_all_run() -> None:
    result = run_chapter("ai-governance-fundamentals", 4)
    assert result["examples_failed"] == 0
    assert (
        result["examples_run"] >= 3
    ), "chapter 4 must ship the weights demo, the cost-ratio demo, and the per-tongue projection"


def test_chapter_04_phi_progression_is_strictly_increasing() -> None:
    """Higher-index tongues must always outweigh lower-index ones, by phi each
    step. Chapter claim: 'DR costs 11x as much as KO.'"""
    from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import TONGUE_WEIGHTS

    for i in range(1, len(TONGUE_WEIGHTS)):
        assert (
            TONGUE_WEIGHTS[i] > TONGUE_WEIGHTS[i - 1]
        ), f"phi progression broken at index {i}: {TONGUE_WEIGHTS[i - 1]} -> {TONGUE_WEIGHTS[i]}"

    ratio = TONGUE_WEIGHTS[-1] / TONGUE_WEIGHTS[0]
    assert 10.5 < ratio < 11.5, f"DR/KO ratio drifted from chapter claim of ~11x: {ratio}"


def test_chapter_04_drifted_strictly_outcosts_aligned() -> None:
    """The drifted hyperspace point must score strictly higher than the
    aligned one. This is the cost-ratio claim of the chapter."""
    from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
        LanguesMetric,
        HyperspacePoint,
    )

    metric = LanguesMetric()
    aligned = HyperspacePoint(time=0.0, intent=0.05, policy=0.5, trust=0.85, risk=0.15, entropy=0.25)
    drifted = HyperspacePoint(time=0.0, intent=0.7, policy=0.5, trust=0.3, risk=0.8, entropy=0.7)

    L_a = metric.compute(aligned)
    L_d = metric.compute(drifted)

    assert L_d > L_a, f"drifted cost {L_d} did not exceed aligned cost {L_a}"


def test_chapter_04_dr_dominates_drifted_projection() -> None:
    """The DR (entropy) projection must outscore every other single-tongue
    projection on the drifted point. Without this, the chapter's "DR
    carries 39% of the total drifted cost" claim is false."""
    from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
        LanguesMetric,
        HyperspacePoint,
        TONGUES,
    )

    metric = LanguesMetric()
    drifted = HyperspacePoint(time=0.0, intent=0.7, policy=0.5, trust=0.3, risk=0.8, entropy=0.7)

    projections = {t: metric.compute(drifted, active_tongues=[t]) for t in TONGUES}
    dr = projections["DR"]
    for t, L in projections.items():
        if t == "DR":
            continue
        assert dr > L, f"DR projection {dr} should exceed {t} projection {L}"
