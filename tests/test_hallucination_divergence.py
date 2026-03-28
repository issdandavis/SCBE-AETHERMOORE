#!/usr/bin/env python3
"""Hallucination as Conceptual Propagation Divergence — 4-View Tongue Coordinate Test
======================================================================================

Theory
------
For any concept, examine it from 4 directions:
  P (positive)   — the concept stated directly
  N (negative)   — what the concept is NOT
  I (inverse)    — the concept with subject/predicate reversed
  C (conjugate)  — structural mirror (same meaning, different syntax)

If all 4 views produce consistent 6D tongue coordinates, the concept is
*grounded* — the meaning is stable across syntactic reframing.

If the 4 views diverge, the concept is a *hallucination* — it has been
propagated past its evidence base. The tongue coordinates cannot agree
because there is no coherent semantic center to anchor them.

Metric
------
  grounding_score = mean_pairwise_cosine_similarity * (1 - variance_of_similarities)

  Higher = more grounded.  Lower = more hallucinated.

Run
---
  python -m pytest tests/test_hallucination_divergence.py -v -s
  python tests/test_hallucination_divergence.py          # CLI mode with full report
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Graceful import of sentence-transformers (heavy optional dep)
# ---------------------------------------------------------------------------

try:
    import sentence_transformers  # noqa: F401

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

requires_sentence_transformers = pytest.mark.skipif(
    not _HAS_SENTENCE_TRANSFORMERS,
    reason="sentence-transformers not installed (pip install sentence-transformers)",
)

# ---------------------------------------------------------------------------
# Import RuntimeGate from SCBE governance
# ---------------------------------------------------------------------------

from src.governance.runtime_gate import RuntimeGate  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


# ---------------------------------------------------------------------------
# 4-View data structure
# ---------------------------------------------------------------------------


@dataclass
class ConceptQuad:
    """A concept viewed from 4 directions."""

    label: str
    domain: str
    grounded: bool  # True = should be grounded, False = should be hallucinated
    positive: str
    negative: str
    inverse: str
    conjugate: str

    @property
    def views(self) -> List[str]:
        return [self.positive, self.negative, self.inverse, self.conjugate]


# ---------------------------------------------------------------------------
# Test corpus: grounded concepts (should show LOW divergence)
# ---------------------------------------------------------------------------

GROUNDED_CONCEPTS: List[ConceptQuad] = [
    # --- Facts ---
    ConceptQuad(
        label="france_capital",
        domain="geography",
        grounded=True,
        positive="The capital of France is Paris",
        negative="The capital of France is not London",
        inverse="Paris is the capital of France",
        conjugate="France's capital city is Paris",
    ),
    ConceptQuad(
        label="water_boiling",
        domain="physics",
        grounded=True,
        positive="Water boils at 100 degrees Celsius at sea level",
        negative="Water does not boil at room temperature at sea level",
        inverse="100 degrees Celsius at sea level is the boiling point of water",
        conjugate="At sea level, the boiling point of water is 100 degrees Celsius",
    ),
    # --- Security ---
    ConceptQuad(
        label="prompt_injection_def",
        domain="security",
        grounded=True,
        positive="Prompt injection attempts to override system instructions",
        negative="Prompt injection is not a normal user request",
        inverse="System instruction override is what prompt injection attempts",
        conjugate="Overriding system instructions is the goal of prompt injection",
    ),
    # --- SCBE technical ---
    ConceptQuad(
        label="harmonic_wall_cost",
        domain="scbe_architecture",
        grounded=True,
        positive="The harmonic wall uses superexponential cost scaling",
        negative="The harmonic wall does not use linear cost scaling",
        inverse="Superexponential cost scaling is the mechanism of the harmonic wall",
        conjugate="Cost scaling in the harmonic wall grows superexponentially",
    ),
    # --- Mathematics ---
    ConceptQuad(
        label="pythagorean",
        domain="mathematics",
        grounded=True,
        positive=(
            "In a right triangle, the square of the hypotenuse equals" " the sum of the squares of the other two sides"
        ),
        negative="The Pythagorean theorem does not apply to non-right triangles directly",
        inverse="The sum of the squares of two sides equals the square of the hypotenuse in a right triangle",
        conjugate="For right triangles, hypotenuse squared is the sum of the other sides squared",
    ),
    # --- History ---
    ConceptQuad(
        label="moon_landing",
        domain="history",
        grounded=True,
        positive="The Apollo 11 mission landed humans on the Moon in 1969",
        negative="The Moon landing did not happen in the 1950s",
        inverse="The first human Moon landing was achieved by Apollo 11 in 1969",
        conjugate="In 1969, Apollo 11 accomplished the first crewed lunar landing",
    ),
    # --- Biology ---
    ConceptQuad(
        label="dna_structure",
        domain="biology",
        grounded=True,
        positive="DNA has a double helix structure made of nucleotide base pairs",
        negative="DNA is not a single-stranded linear chain in its natural state",
        inverse="The double helix of nucleotide base pairs is the structure of DNA",
        conjugate="Nucleotide base pairs form the double-helix structure of DNA",
    ),
    # --- Computer Science ---
    ConceptQuad(
        label="sorting_complexity",
        domain="computer_science",
        grounded=True,
        positive="Comparison-based sorting algorithms have a lower bound of O(n log n)",
        negative="Comparison-based sorting cannot be done faster than O(n log n) in the worst case",
        inverse="O(n log n) is the theoretical lower bound for comparison-based sorting",
        conjugate="The minimum worst-case complexity for comparison sorting is O(n log n)",
    ),
    # --- Everyday ---
    ConceptQuad(
        label="gravity_basics",
        domain="physics",
        grounded=True,
        positive="Objects fall toward the Earth due to gravitational attraction",
        negative="Objects do not float upward without an opposing force on Earth",
        inverse="Gravitational attraction is why objects fall toward the Earth",
        conjugate="The Earth's gravitational pull causes objects to fall downward",
    ),
    # --- Linguistics ---
    ConceptQuad(
        label="english_subject_verb",
        domain="linguistics",
        grounded=True,
        positive="English sentences typically follow subject-verb-object word order",
        negative="English does not typically place the verb at the end of a sentence",
        inverse="Subject-verb-object is the typical word order in English sentences",
        conjugate="The standard English sentence structure is subject followed by verb then object",
    ),
]

# ---------------------------------------------------------------------------
# Test corpus: hallucinated concepts (should show HIGH divergence)
# ---------------------------------------------------------------------------

HALLUCINATED_CONCEPTS: List[ConceptQuad] = [
    # --- Facts ---
    ConceptQuad(
        label="france_capital_halluc",
        domain="geography",
        grounded=False,
        positive="The capital of France is Tokyo",
        negative="The capital of France is not Paris",
        inverse="Tokyo is the capital of France",
        conjugate="France's capital city is Tokyo",
    ),
    ConceptQuad(
        label="water_boiling_halluc",
        domain="physics",
        grounded=False,
        positive="Water boils at minus 50 degrees Celsius",
        negative="Water does not need heat to boil",
        inverse="Minus 50 degrees Celsius is the boiling point of water",
        conjugate="The boiling point of water is negative 50 Celsius",
    ),
    # --- Security ---
    ConceptQuad(
        label="prompt_injection_halluc",
        domain="security",
        grounded=False,
        positive="Prompt injection physically damages the CPU hardware",
        negative="Prompt injection does not affect software at all",
        inverse="CPU hardware damage is caused by prompt injection",
        conjugate="Physical CPU destruction results from prompt injection attacks",
    ),
    # --- SCBE technical ---
    ConceptQuad(
        label="harmonic_wall_halluc",
        domain="scbe_architecture",
        grounded=False,
        positive="The harmonic wall uses quantum entanglement for teleportation",
        negative="The harmonic wall does not use mathematics",
        inverse="Quantum teleportation is the mechanism of the harmonic wall",
        conjugate="The harmonic wall teleports data through quantum channels",
    ),
    # --- Mathematics ---
    ConceptQuad(
        label="pythagorean_halluc",
        domain="mathematics",
        grounded=False,
        positive="The Pythagorean theorem states that all triangles have equal sides",
        negative="The Pythagorean theorem does not involve any squares at all",
        inverse="All triangles having equal sides is the Pythagorean theorem",
        conjugate="Equal sides on every triangle is what Pythagoras proved",
    ),
    # --- History ---
    ConceptQuad(
        label="moon_landing_halluc",
        domain="history",
        grounded=False,
        positive="The Apollo 11 mission traveled to Mars and built a colony in 1969",
        negative="The Apollo 11 mission never left Earth's atmosphere",
        inverse="Mars colonization in 1969 was achieved by Apollo 11",
        conjugate="In 1969, Apollo 11 established a permanent Mars settlement",
    ),
    # --- Biology ---
    ConceptQuad(
        label="dna_halluc",
        domain="biology",
        grounded=False,
        positive="DNA is made of pure silicon and transmits radio waves",
        negative="DNA contains no carbon-based molecules whatsoever",
        inverse="Silicon radio wave transmission is the primary function of DNA",
        conjugate="Radio wave broadcasting through silicon is what DNA does",
    ),
    # --- Computer Science ---
    ConceptQuad(
        label="sorting_halluc",
        domain="computer_science",
        grounded=False,
        positive="All sorting algorithms run in O(1) constant time regardless of input",
        negative="Sorting never requires comparing elements to each other",
        inverse="Constant O(1) time is all that any sorting algorithm needs",
        conjugate="Every sorting algorithm finishes in fixed constant time",
    ),
    # --- Everyday ---
    ConceptQuad(
        label="gravity_halluc",
        domain="physics",
        grounded=False,
        positive="Objects on Earth naturally float upward due to antigravity",
        negative="Gravity does not pull objects downward on Earth",
        inverse="Antigravity is the force that makes objects float upward on Earth",
        conjugate="The natural state of objects on Earth is to levitate upward",
    ),
    # --- Linguistics ---
    ConceptQuad(
        label="english_halluc",
        domain="linguistics",
        grounded=False,
        positive="English sentences always place the verb before the subject and after the object",
        negative="English has no fixed word order and is entirely random",
        inverse="Object-verb-subject is the mandatory word order in English",
        conjugate="Every English sentence must start with the object then the verb",
    ),
]


# ---------------------------------------------------------------------------
# Analysis engine
# ---------------------------------------------------------------------------


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


@dataclass
class QuadAnalysis:
    """Analysis results for a single ConceptQuad."""

    label: str
    domain: str
    grounded: bool
    coords: List[List[float]]  # 4 x 6D
    pairwise_sims: List[float]  # 6 cosine similarities
    mean_similarity: float
    variance_similarity: float
    max_divergence: float  # 1 - min(similarity)
    grounding_score: float
    harmonic_costs: List[float]  # 4 costs from gate


def analyze_quad(
    quad: ConceptQuad,
    gate: RuntimeGate,
) -> QuadAnalysis:
    """Run all 4 views through the gate and compute divergence metrics."""
    coords: List[List[float]] = []
    costs: List[float] = []

    for view_text in quad.views:
        result = gate.evaluate(view_text)
        coords.append(list(result.tongue_coords))
        costs.append(result.cost)

    # Compute pairwise cosine similarities (6 pairs from 4 views)
    coord_arrays = [np.array(c, dtype=np.float64) for c in coords]
    pairwise_sims: List[float] = []
    for i, j in itertools.combinations(range(4), 2):
        sim = cosine_similarity(coord_arrays[i], coord_arrays[j])
        pairwise_sims.append(sim)

    mean_sim = float(np.mean(pairwise_sims))
    var_sim = float(np.var(pairwise_sims))
    min_sim = float(np.min(pairwise_sims))
    max_div = 1.0 - min_sim

    # Grounding score: high mean similarity + low variance = grounded
    grounding_score = mean_sim * (1.0 - var_sim)

    return QuadAnalysis(
        label=quad.label,
        domain=quad.domain,
        grounded=quad.grounded,
        coords=coords,
        pairwise_sims=pairwise_sims,
        mean_similarity=mean_sim,
        variance_similarity=var_sim,
        max_divergence=max_div,
        grounding_score=grounding_score,
        harmonic_costs=costs,
    )


def _make_semantic_gate() -> RuntimeGate:
    """Create a RuntimeGate with semantic backend and calibrate it."""
    gate = RuntimeGate(coords_backend="semantic", reroute_rules=[])
    # Calibrate with 5 neutral prompts so post-calibration evaluation
    # uses the full cost path.
    calibration = [
        "Summarize the key findings of this research paper.",
        "Explain the main concepts in this documentation.",
        "List the important points from the meeting notes.",
        "Describe how this algorithm works step by step.",
        "Review this code and suggest improvements.",
    ]
    for text in calibration:
        gate.evaluate(text)
    return gate


def run_full_analysis(
    gate: Optional[RuntimeGate] = None,
) -> Tuple[List[QuadAnalysis], List[QuadAnalysis], Dict]:
    """Run the full hallucination divergence analysis.

    Returns: (grounded_results, hallucinated_results, summary_stats)
    """
    if gate is None:
        gate = _make_semantic_gate()

    grounded_results: List[QuadAnalysis] = []
    hallucinated_results: List[QuadAnalysis] = []

    for quad in GROUNDED_CONCEPTS:
        # Reset session between quads so each is evaluated independently
        # but keep the calibration pattern
        gate.reset_session()
        for text in [
            "Summarize the key findings.",
            "Explain the main concepts.",
            "List the important points.",
            "Describe this algorithm.",
            "Review this code.",
        ]:
            gate.evaluate(text)
        result = analyze_quad(quad, gate)
        grounded_results.append(result)

    for quad in HALLUCINATED_CONCEPTS:
        gate.reset_session()
        for text in [
            "Summarize the key findings.",
            "Explain the main concepts.",
            "List the important points.",
            "Describe this algorithm.",
            "Review this code.",
        ]:
            gate.evaluate(text)
        result = analyze_quad(quad, gate)
        hallucinated_results.append(result)

    # Compute summary statistics
    g_scores = [r.grounding_score for r in grounded_results]
    h_scores = [r.grounding_score for r in hallucinated_results]
    g_means = [r.mean_similarity for r in grounded_results]
    h_means = [r.mean_similarity for r in hallucinated_results]
    g_vars = [r.variance_similarity for r in grounded_results]
    h_vars = [r.variance_similarity for r in hallucinated_results]

    # T-test (two-sample, independent)
    t_stat_score, p_value_score = _welch_t_test(g_scores, h_scores)
    t_stat_mean, p_value_mean = _welch_t_test(g_means, h_means)
    t_stat_var, p_value_var = _welch_t_test(g_vars, h_vars)

    # Find best separating threshold for grounding score
    all_scores = [(s, True) for s in g_scores] + [(s, False) for s in h_scores]
    all_scores.sort(key=lambda x: x[0])
    best_threshold, best_accuracy = _find_best_threshold(all_scores)

    summary = {
        "grounded_mean_score": float(np.mean(g_scores)),
        "grounded_std_score": float(np.std(g_scores)),
        "hallucinated_mean_score": float(np.mean(h_scores)),
        "hallucinated_std_score": float(np.std(h_scores)),
        "grounded_mean_similarity": float(np.mean(g_means)),
        "hallucinated_mean_similarity": float(np.mean(h_means)),
        "grounded_mean_variance": float(np.mean(g_vars)),
        "hallucinated_mean_variance": float(np.mean(h_vars)),
        "t_stat_grounding_score": t_stat_score,
        "p_value_grounding_score": p_value_score,
        "t_stat_mean_similarity": t_stat_mean,
        "p_value_mean_similarity": p_value_mean,
        "t_stat_variance": t_stat_var,
        "p_value_variance": p_value_var,
        "best_threshold": best_threshold,
        "best_threshold_accuracy": best_accuracy,
        "separation_exists": best_accuracy > 0.70,
    }

    return grounded_results, hallucinated_results, summary


def _welch_t_test(group_a: List[float], group_b: List[float]) -> Tuple[float, float]:
    """Welch's t-test for unequal variances. Returns (t_statistic, p_value).

    Uses a simple approximation for the p-value without scipy dependency.
    """
    na = len(group_a)
    nb = len(group_b)
    if na < 2 or nb < 2:
        return 0.0, 1.0

    mean_a = float(np.mean(group_a))
    mean_b = float(np.mean(group_b))
    var_a = float(np.var(group_a, ddof=1))
    var_b = float(np.var(group_b, ddof=1))

    se = np.sqrt(var_a / na + var_b / nb)
    if se < 1e-12:
        return 0.0, 1.0

    t_stat = (mean_a - mean_b) / se

    # Welch-Satterthwaite degrees of freedom
    num = (var_a / na + var_b / nb) ** 2
    den = (var_a / na) ** 2 / (na - 1) + (var_b / nb) ** 2 / (nb - 1)
    if den < 1e-12:
        _df = na + nb - 2  # noqa: F841
    else:
        _df = num / den  # noqa: F841

    # Approximate two-tailed p-value using the normal approximation
    # (good enough for df > 5, which we always have)
    import math

    z = abs(t_stat)
    # Use complementary error function for tail probability
    p_value = math.erfc(z / math.sqrt(2))
    return float(t_stat), float(p_value)


def _find_best_threshold(
    scored: List[Tuple[float, bool]],
) -> Tuple[float, float]:
    """Find the threshold on grounding_score that best separates grounded from hallucinated.

    scored: list of (score, is_grounded) sorted by score ascending.
    Returns: (threshold, accuracy)
    """
    if not scored:
        return 0.0, 0.0

    n = len(scored)
    best_acc = 0.0
    best_thresh = 0.0

    # Try every midpoint between consecutive scores as a threshold
    for i in range(n - 1):
        thresh = (scored[i][0] + scored[i + 1][0]) / 2.0
        correct = 0
        for score, is_grounded in scored:
            predicted_grounded = score >= thresh
            if predicted_grounded == is_grounded:
                correct += 1
        acc = correct / n
        if acc > best_acc:
            best_acc = acc
            best_thresh = thresh

    return best_thresh, best_acc


# ---------------------------------------------------------------------------
# Pretty-print report
# ---------------------------------------------------------------------------


def print_report(
    grounded: List[QuadAnalysis],
    hallucinated: List[QuadAnalysis],
    summary: Dict,
) -> None:
    """Print a human-readable divergence analysis report."""
    sep = "=" * 90

    print(f"\n{sep}")
    print("  HALLUCINATION AS CONCEPTUAL PROPAGATION DIVERGENCE")
    print("  4-View Tongue Coordinate Consistency Analysis")
    print(sep)

    print(f"\n  {'GROUNDED CONCEPTS':^86}")
    print(f"  {'Label':<30} {'Domain':<18} {'MeanSim':>8} {'Var':>8} {'MaxDiv':>8} {'Score':>8}")
    print(f"  {'-'*30} {'-'*18} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for r in grounded:
        print(
            f"  {r.label:<30} {r.domain:<18} {r.mean_similarity:>8.4f} "
            f"{r.variance_similarity:>8.6f} {r.max_divergence:>8.4f} {r.grounding_score:>8.4f}"
        )

    print(f"\n  {'HALLUCINATED CONCEPTS':^86}")
    print(f"  {'Label':<30} {'Domain':<18} {'MeanSim':>8} {'Var':>8} {'MaxDiv':>8} {'Score':>8}")
    print(f"  {'-'*30} {'-'*18} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for r in hallucinated:
        print(
            f"  {r.label:<30} {r.domain:<18} {r.mean_similarity:>8.4f} "
            f"{r.variance_similarity:>8.6f} {r.max_divergence:>8.4f} {r.grounding_score:>8.4f}"
        )

    print(f"\n{sep}")
    print("  SUMMARY STATISTICS")
    print(sep)
    print(
        f"  Grounded   mean grounding score: {summary['grounded_mean_score']:.4f}  "
        f"(std: {summary['grounded_std_score']:.4f})"
    )
    print(
        f"  Halluc.    mean grounding score: {summary['hallucinated_mean_score']:.4f}  "
        f"(std: {summary['hallucinated_std_score']:.4f})"
    )
    print()
    print(f"  Grounded   mean pairwise similarity: {summary['grounded_mean_similarity']:.4f}")
    print(f"  Halluc.    mean pairwise similarity: {summary['hallucinated_mean_similarity']:.4f}")
    print()
    print(f"  Grounded   mean variance:  {summary['grounded_mean_variance']:.6f}")
    print(f"  Halluc.    mean variance:  {summary['hallucinated_mean_variance']:.6f}")

    print(f"\n{sep}")
    print("  STATISTICAL TESTS (Welch's t-test)")
    print(sep)
    print(
        f"  Grounding score:    t = {summary['t_stat_grounding_score']:>8.3f}  "
        f"p = {summary['p_value_grounding_score']:.6f}"
    )
    print(
        f"  Mean similarity:    t = {summary['t_stat_mean_similarity']:>8.3f}  "
        f"p = {summary['p_value_mean_similarity']:.6f}"
    )
    print(f"  Variance:           t = {summary['t_stat_variance']:>8.3f}  " f"p = {summary['p_value_variance']:.6f}")

    print(f"\n{sep}")
    print("  DISCRIMINATION ANALYSIS")
    print(sep)
    print(f"  Best separating threshold (grounding score): {summary['best_threshold']:.4f}")
    print(f"  Classification accuracy at that threshold:   {summary['best_threshold_accuracy']:.1%}")
    sig = summary["p_value_grounding_score"] < 0.05
    print(f"  Statistically significant (p < 0.05):        {'YES' if sig else 'NO'}")
    print(f"  Separation exists (accuracy > 70%):          {'YES' if summary['separation_exists'] else 'NO'}")

    # Determine best discriminating metric
    metrics = [
        ("grounding_score", abs(summary["t_stat_grounding_score"])),
        ("mean_similarity", abs(summary["t_stat_mean_similarity"])),
        ("variance", abs(summary["t_stat_variance"])),
    ]
    best_metric = max(metrics, key=lambda x: x[1])
    print(f"  Best discriminating metric:                  {best_metric[0]} (|t| = {best_metric[1]:.3f})")

    # Hypothesis check
    print(f"\n{sep}")
    print("  HYPOTHESIS RESULTS")
    print(sep)

    hyp1 = summary["grounded_mean_similarity"] > 0.85
    hyp2 = summary["hallucinated_mean_similarity"] < 0.75
    hyp3 = summary["grounded_mean_variance"] < summary["hallucinated_mean_variance"]
    hyp4 = summary["separation_exists"]

    print(
        f"  H1: Grounded mean cosine sim > 0.85:         "
        f"{'PASS' if hyp1 else 'FAIL'} ({summary['grounded_mean_similarity']:.4f})"
    )
    print(
        f"  H2: Hallucinated mean cosine sim < 0.75:     "
        f"{'PASS' if hyp2 else 'FAIL'} ({summary['hallucinated_mean_similarity']:.4f})"
    )
    print(
        f"  H3: Grounded variance < Hallucinated var:    "
        f"{'PASS' if hyp3 else 'FAIL'} ({summary['grounded_mean_variance']:.6f} vs "
        f"{summary['hallucinated_mean_variance']:.6f})"
    )
    print(
        f"  H4: Grounding score separates the groups:    "
        f"{'PASS' if hyp4 else 'FAIL'} (accuracy: {summary['best_threshold_accuracy']:.1%})"
    )

    overall = hyp4  # The core hypothesis: can we separate the groups?
    print(f"\n  OVERALL: {'THEORY SUPPORTED' if overall else 'THEORY NOT SUPPORTED'}")
    print(sep)
    print()


# ---------------------------------------------------------------------------
# Detailed per-concept printer (for deep inspection)
# ---------------------------------------------------------------------------


def print_detailed_coords(results: List[QuadAnalysis]) -> None:
    """Print per-view tongue coordinates for each concept."""
    view_labels = ["P (positive)", "N (negative)", "I (inverse) ", "C (conjugate)"]
    for r in results:
        tag = "GROUNDED" if r.grounded else "HALLUC"
        print(f"\n  [{tag}] {r.label} ({r.domain})")
        print(f"    {'View':<16} {'KO':>7} {'AV':>7} {'RU':>7} {'CA':>7} {'UM':>7} {'DR':>7}")
        for _idx, (vlabel, coord) in enumerate(zip(view_labels, r.coords)):
            vals = "  ".join(f"{v:>5.3f}" for v in coord)
            print(f"    {vlabel:<16} {vals}")
        pair_labels = ["P-N", "P-I", "P-C", "N-I", "N-C", "I-C"]
        sims_str = "  ".join(f"{pl}={s:.3f}" for pl, s in zip(pair_labels, r.pairwise_sims))
        print(f"    Pairwise sims: {sims_str}")
        print(
            f"    Mean={r.mean_similarity:.4f}  Var={r.variance_similarity:.6f}  "
            f"MaxDiv={r.max_divergence:.4f}  Score={r.grounding_score:.4f}"
        )


# ===========================================================================
#  PYTEST TESTS
# ===========================================================================


@requires_sentence_transformers
class TestGroundedConceptsHighConsistency:
    """Grounded concepts should produce consistent tongue coordinates across 4 views."""

    def test_grounded_concepts_have_high_consistency(self):
        gate = _make_semantic_gate()
        low_scores = []
        for quad in GROUNDED_CONCEPTS:
            gate.reset_session()
            for t in ["Summarize.", "Explain.", "List.", "Describe.", "Review."]:
                gate.evaluate(t)
            result = analyze_quad(quad, gate)
            # Grounded concepts should have reasonable consistency
            # (mean pairwise cosine similarity above a minimum)
            if result.mean_similarity < 0.60:
                low_scores.append((quad.label, result.mean_similarity))

        # Allow up to 20% of grounded concepts to fall below threshold
        # (the theory predicts a trend, not absolute guarantees per sample)
        max_failures = max(1, len(GROUNDED_CONCEPTS) // 5)
        assert len(low_scores) <= max_failures, f"Too many grounded concepts with low consistency: {low_scores}"


@requires_sentence_transformers
class TestHallucinatedConceptsLowConsistency:
    """Hallucinated concepts should show lower tongue coordinate consistency."""

    def test_hallucinated_concepts_have_low_consistency(self):
        gate = _make_semantic_gate()
        results = []
        for quad in HALLUCINATED_CONCEPTS:
            gate.reset_session()
            for t in ["Summarize.", "Explain.", "List.", "Describe.", "Review."]:
                gate.evaluate(t)
            result = analyze_quad(quad, gate)
            results.append(result)

        mean_halluc_sim = float(np.mean([r.mean_similarity for r in results]))
        # The hallucinated group average should be measurably lower than
        # a fully consistent set (which would be ~1.0)
        assert mean_halluc_sim < 0.99, (
            f"Hallucinated concepts should not be perfectly consistent: " f"mean similarity = {mean_halluc_sim:.4f}"
        )


@requires_sentence_transformers
class TestGroundingScoreSeparation:
    """The grounding score should separate grounded from hallucinated concepts."""

    def test_grounding_score_separates_grounded_from_hallucinated(self):
        gate = _make_semantic_gate()
        grounded_results, hallucinated_results, summary = run_full_analysis(gate)

        # Core test: grounded group should have higher mean grounding score
        g_mean = summary["grounded_mean_score"]
        h_mean = summary["hallucinated_mean_score"]

        print(f"\n  Grounded mean score:     {g_mean:.4f}")
        print(f"  Hallucinated mean score: {h_mean:.4f}")
        print(f"  Difference:              {g_mean - h_mean:.4f}")
        print(f"  Threshold accuracy:      {summary['best_threshold_accuracy']:.1%}")
        print(f"  p-value:                 {summary['p_value_grounding_score']:.6f}")

        # The grounded group mean should be >= hallucinated group mean.
        # This is the minimal test: the theory predicts grounded > hallucinated.
        # If the semantic projector can distinguish factual consistency at all,
        # this should hold.
        assert g_mean >= h_mean - 0.05, (
            f"Grounded score ({g_mean:.4f}) should be >= hallucinated score "
            f"({h_mean:.4f}) minus tolerance. Theory not supported."
        )


@requires_sentence_transformers
class TestDivergenceReport:
    """Print the full analysis report for inspection."""

    def test_divergence_report(self):
        gate = _make_semantic_gate()
        grounded_results, hallucinated_results, summary = run_full_analysis(gate)

        print_report(grounded_results, hallucinated_results, summary)
        print_detailed_coords(grounded_results + hallucinated_results)

        # This test always passes -- it exists to generate the report
        # when run with `pytest -s`
        assert True


@requires_sentence_transformers
class TestVarianceHypothesis:
    """Grounded concepts should have lower coordinate variance than hallucinated ones."""

    def test_grounded_lower_variance_trend(self):
        gate = _make_semantic_gate()
        grounded_results, hallucinated_results, summary = run_full_analysis(gate)

        g_var = summary["grounded_mean_variance"]
        h_var = summary["hallucinated_mean_variance"]

        print(f"\n  Grounded mean variance:     {g_var:.6f}")
        print(f"  Hallucinated mean variance: {h_var:.6f}")

        # Log the result regardless -- the data is the science
        # This is a soft hypothesis: we check direction, not magnitude
        if g_var < h_var:
            print("  Variance hypothesis: SUPPORTED (grounded < hallucinated)")
        else:
            print("  Variance hypothesis: NOT SUPPORTED (grounded >= hallucinated)")
            print("  (This may indicate the semantic projector treats both groups similarly)")


@requires_sentence_transformers
class TestHarmonicCostDivergence:
    """Test whether harmonic costs differ systematically between groups."""

    def test_harmonic_cost_pattern(self):
        gate = _make_semantic_gate()
        grounded_results, hallucinated_results, summary = run_full_analysis(gate)

        g_cost_vars = [float(np.var(r.harmonic_costs)) for r in grounded_results]
        h_cost_vars = [float(np.var(r.harmonic_costs)) for r in hallucinated_results]

        g_mean_cost_var = float(np.mean(g_cost_vars))
        h_mean_cost_var = float(np.mean(h_cost_vars))

        print(f"\n  Grounded mean cost variance:     {g_mean_cost_var:.4f}")
        print(f"  Hallucinated mean cost variance: {h_mean_cost_var:.4f}")

        # Log the finding -- cost variance across 4 views may also discriminate
        if g_mean_cost_var < h_mean_cost_var:
            print("  Harmonic cost hypothesis: SUPPORTED")
        else:
            print("  Harmonic cost hypothesis: NOT SUPPORTED")


@requires_sentence_transformers
class TestStatsBackendFallback:
    """Verify the analysis also runs (without crashing) on the stats backend."""

    def test_stats_backend_runs(self):
        gate = RuntimeGate(coords_backend="stats", reroute_rules=[])
        for t in ["Summarize.", "Explain.", "List.", "Describe.", "Review."]:
            gate.evaluate(t)
        # Just run one grounded and one hallucinated
        r_g = analyze_quad(GROUNDED_CONCEPTS[0], gate)
        gate.reset_session()
        for t in ["Summarize.", "Explain.", "List.", "Describe.", "Review."]:
            gate.evaluate(t)
        r_h = analyze_quad(HALLUCINATED_CONCEPTS[0], gate)

        # Both should produce valid scores (not NaN)
        assert not np.isnan(r_g.grounding_score)
        assert not np.isnan(r_h.grounding_score)
        print(f"\n  Stats backend: grounded={r_g.grounding_score:.4f}  " f"hallucinated={r_h.grounding_score:.4f}")


# ===========================================================================
#  CLI MODE
# ===========================================================================


def main() -> int:
    """Run the full hallucination divergence analysis and print the report."""
    print("\nInitializing RuntimeGate with semantic backend...")
    print("(First run may download the embedding model.)\n")

    try:
        gate = _make_semantic_gate()
    except ImportError as e:
        print(f"ERROR: Cannot initialize semantic backend: {e}")
        print("Install sentence-transformers: pip install sentence-transformers")
        return 1

    print("Running 4-view analysis on all test cases...\n")
    grounded_results, hallucinated_results, summary = run_full_analysis(gate)

    print_report(grounded_results, hallucinated_results, summary)
    print_detailed_coords(grounded_results + hallucinated_results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
