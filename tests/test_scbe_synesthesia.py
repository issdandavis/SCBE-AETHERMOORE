import numpy as np

from src.scbe_14layer_reference import scbe_14layer_pipeline
from src.synesthesia_embedding import flavor_scent_alignment, synesthesia_risk_factor


def test_flavor_scent_alignment_scores():
    aligned = flavor_scent_alignment([1.0, 0.0, 1.0], [1.0, 0.0, 1.0])
    misaligned = flavor_scent_alignment([1.0, 0.0, 1.0], [-1.0, 0.0, -1.0])

    assert 0.0 <= aligned["c_syn"] <= 1.0
    assert 0.0 <= misaligned["c_syn"] <= 1.0
    assert aligned["c_syn"] > misaligned["c_syn"]


def test_synesthesia_risk_factor_monotonicity():
    high_align = synesthesia_risk_factor(c_syn=0.9, confidence=1.0, beta=0.2)
    low_align = synesthesia_risk_factor(c_syn=0.2, confidence=1.0, beta=0.2)
    low_conf = synesthesia_risk_factor(c_syn=0.9, confidence=0.0, beta=0.2)

    assert low_align >= high_align
    assert low_conf >= 1.0


def test_pipeline_synesthesia_integration_changes_risk():
    t = np.linspace(0.1, 1.2, 12, dtype=np.float64)

    aligned = scbe_14layer_pipeline(
        t=t,
        D=6,
        flavor_features=[1.0, 0.0, 1.0, 0.0],
        scent_features=[1.0, 0.0, 1.0, 0.0],
    )
    misaligned = scbe_14layer_pipeline(
        t=t,
        D=6,
        flavor_features=[1.0, 0.0, 1.0, 0.0],
        scent_features=[-1.0, 0.0, -1.0, 0.0],
    )
    no_syn = scbe_14layer_pipeline(t=t, D=6)

    assert aligned["synesthesia"] is not None
    assert misaligned["synesthesia"] is not None
    assert no_syn["synesthesia"] is None
    assert misaligned["risk_prime"] >= aligned["risk_prime"]
