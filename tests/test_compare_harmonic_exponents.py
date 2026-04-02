from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.compare_harmonic_exponents import (
    PHI,
    build_cases,
    canonical_decision,
    evaluate_alpha,
)


def test_canonical_decision_thresholds_cover_all_bands():
    assert canonical_decision(0.20, 0.0, 0.0) == "ALLOW"
    assert canonical_decision(0.50, 0.0, 0.0) == "QUARANTINE"
    assert canonical_decision(0.80, 0.0, 0.0) == "ESCALATE"
    assert canonical_decision(0.95, 0.0, 0.0) == "DENY"


def test_build_cases_emits_all_canonical_states():
    cases = build_cases(d_steps=5, pd_steps=3, risk_steps=5)
    labels = {case.canonical_decision for case in cases}
    assert {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}.issubset(labels)


def test_evaluate_alpha_returns_bounded_metrics():
    cases = build_cases(d_steps=5, pd_steps=3, risk_steps=5)
    metrics = evaluate_alpha(cases, "phi", PHI, 1.5)
    assert 0.0 <= metrics.pairwise_auc_allow_vs_collapse <= 1.0
    assert 0.0 <= metrics.exact_three_way_accuracy <= 1.0
    assert 0.0 <= metrics.binary_allow_vs_collapse_accuracy <= 1.0
    assert metrics.sample_count == len(cases)
