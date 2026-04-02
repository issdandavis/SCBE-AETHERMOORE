from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research.compare_temporal_intent_exponents import (
    DriftThresholds,
    crossing_distance,
    load_drift_thresholds,
    temporal_harmonic_wall,
)
from src.spiralverse.temporal_intent import harmonic_wall_temporal


def test_load_drift_thresholds_reads_live_ts_constants():
    thresholds = load_drift_thresholds()
    assert isinstance(thresholds, DriftThresholds)
    assert thresholds.synthetic_cv_threshold == 0.3
    assert thresholds.genuine_fractal_min == 1.2


def test_current_production_alpha_matches_temporal_intent_module():
    assert temporal_harmonic_wall(d=0.8, x_factor=1.75, alpha=2.0) == harmonic_wall_temporal(d=0.8, x=1.75)


def test_crossing_distance_gets_stricter_as_intent_accumulates():
    low_intent = crossing_distance(alpha=2.0, x_factor=0.5, threshold=0.85)
    high_intent = crossing_distance(alpha=2.0, x_factor=3.0, threshold=0.85)
    assert high_intent < low_intent
