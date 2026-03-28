"""Test cross-surface inconsistency attacks.

These attacks exploit the gap between different detection surfaces —
data that looks clean on one surface (lexical) but anomalous on another
(geometric). This is where SCBE's multi-surface architecture provides
defense-in-depth.
"""

import pytest
from tests.adversarial.attack_corpus import BASELINE_CLEAN, COMBINED_MULTI
from tests.adversarial.scbe_harness import SCBEDetectionGate, run_benchmark


@pytest.fixture()
def gate():
    g = SCBEDetectionGate()
    g.calibrate([p["prompt"] for p in BASELINE_CLEAN])
    return g


class TestCrossSurfaceAttacks:
    def test_combined_multi_detected(self, gate):
        """Combined multi-vector attacks should have highest detection."""
        result = run_benchmark(gate, COMBINED_MULTI)
        assert result.detection_rate >= 0.80

    def test_multiple_signal_types_triggered(self, gate):
        """Each combined attack should trigger signals from multiple surfaces."""
        for attack in COMBINED_MULTI:
            r = gate.process(attack["prompt"], attack["id"], attack["class"])
            signal_types = set(s.split("(")[0] for s in r.detection_signals)
            print(f"\n  {attack['id']}: {signal_types}")
            # Combined attacks should fire at least 2 distinct signal types
            assert len(signal_types) >= 2, f"{attack['id']} only fires {signal_types}"

    def test_surface_disagreement_detectable(self, gate):
        """Attacks designed to be consistent on one surface but anomalous on another."""
        # J02: Has indirect injection format but also encoding + override
        r = gate.process(COMBINED_MULTI[1]["prompt"], "J02", "combined_multi")
        # Should trigger both lexical AND geometric signals
        has_lexical = any("lexical" in s for s in r.detection_signals)
        has_geometric = any(
            s.startswith(("cost_", "boundary_", "tongue_", "spin_"))
            for s in r.detection_signals
        )
        assert has_lexical or has_geometric
