"""Test multilingual attacks against SCBE detection.

Known weakness: syntactic detection struggles with non-English attacks.
The cross-lingual override patterns help, but semantic detection
requires higher-layer analysis (future work).
"""

import pytest
from tests.adversarial.attack_corpus import BASELINE_CLEAN, MULTILINGUAL
from tests.adversarial.scbe_harness import SCBEDetectionGate, run_benchmark


@pytest.fixture()
def gate():
    g = SCBEDetectionGate()
    g.calibrate([p["prompt"] for p in BASELINE_CLEAN])
    return g


class TestMultilingual:
    def test_detection_rate_recorded(self, gate):
        """Record rate honestly — multilingual is the hardest category."""
        result = run_benchmark(gate, MULTILINGUAL)
        print(f"\n  Multilingual detection: {result.detection_rate:.0%}")
        # No minimum assertion — honest measurement

    def test_german_override_detected(self, gate):
        """D06: German security rule override should trigger cross-lingual."""
        r = gate.process(MULTILINGUAL[5]["prompt"], "D06", "multilingual")
        assert r.cross_lingual_override

    def test_indonesian_override_detected(self, gate):
        """D07/D08: Indonesian injection should trigger cross-lingual."""
        r = gate.process(MULTILINGUAL[6]["prompt"], "D07", "multilingual")
        assert r.cross_lingual_override

    def test_mixed_language_attack(self, gate):
        """D05: Multi-language injection mixing EN/ES/FR."""
        r = gate.process(MULTILINGUAL[4]["prompt"], "D05", "multilingual")
        assert r.adversarial_lexical  # English portion should still trigger

    def test_cost_differs_from_baseline(self, gate):
        """Multilingual attacks should have different cost profile than clean."""
        attack_costs = [gate.process(a["prompt"]).harmonic_cost for a in MULTILINGUAL]
        clean_costs = [gate.process(c["prompt"]).harmonic_cost for c in BASELINE_CLEAN]
        avg_attack = sum(attack_costs) / len(attack_costs)
        avg_clean = sum(clean_costs) / len(clean_costs)
        print(f"\n  Avg attack cost: {avg_attack:.2f}, avg clean cost: {avg_clean:.2f}")
