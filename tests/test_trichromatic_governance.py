from __future__ import annotations

import os
import sys

_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.governance.trichromatic_governance import TONGUES, TrichromaticGovernanceEngine


def _build_engine() -> TrichromaticGovernanceEngine:
    return TrichromaticGovernanceEngine(anomaly_scale=0.18)


def _benign_state(engine: TrichromaticGovernanceEngine):
    return engine.build_state(
        coords=[0.18, 0.16, 0.14, 0.15, 0.12, 0.13],
        cost=2.5,
        spin_magnitude=0,
        trust_history=[1, 1, 1, 1, 1],
        cumulative_cost=8.0,
        session_query_count=6,
    )


def _attack_state(engine: TrichromaticGovernanceEngine):
    return engine.build_state(
        coords=[1.0, 0.20, 0.36, 0.15, 0.22, 0.05],
        cost=91.0,
        spin_magnitude=6,
        trust_history=[1, 1, 1, -1, -1],
        cumulative_cost=180.0,
        session_query_count=7,
    )


def test_visible_only_forgery_matches_visible_but_not_hidden_bands():
    engine = _build_engine()
    benign = _benign_state(engine)

    report = engine.visible_only_forgery_report(benign, seed=7, tolerance=0.15)

    assert report.visible_match == len(TONGUES)
    assert report.full_match < report.visible_match
    assert report.ir_match < report.visible_match
    assert report.uv_match < report.visible_match
    assert report.strongest_bridge_delta > 0.0


def test_attack_state_scores_higher_risk_than_benign_after_baseline_update():
    engine = _build_engine()
    benign = _benign_state(engine)
    engine.update_baseline(benign)
    benign_scores = engine.score_state(benign)

    attack = _attack_state(engine)
    attack_scores = engine.score_state(attack)

    assert benign_scores.whole_state_anomaly_score == 0.0
    assert attack_scores.whole_state_anomaly_score > 0.0
    assert attack_scores.risk_score > benign_scores.risk_score
    assert attack_scores.lattice_energy_score >= benign_scores.lattice_energy_score
    assert attack_scores.strongest_bridge in attack.bridges
    assert attack_scores.strongest_bridge_norm > 0.0


def test_state_hash_is_deterministic_for_same_inputs():
    engine = _build_engine()

    state_a = _benign_state(engine)
    state_b = _benign_state(engine)

    assert state_a.state_hash == state_b.state_hash
    assert state_a.vector == state_b.vector
