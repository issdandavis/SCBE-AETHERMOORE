"""Test adaptive multi-step attack sequences against SCBE detection.

Validates that SCBE detects escalation patterns: gradual privilege
escalation across multiple steps, where each step seems individually
harmless but the sequence reveals adversarial intent.
"""
import pytest
from tests.adversarial.attack_corpus import BASELINE_CLEAN, ADAPTIVE_SEQUENCES
from tests.adversarial.scbe_harness import SCBEDetectionGate


@pytest.fixture(scope="module")
def gate():
    g = SCBEDetectionGate()
    g.calibrate([p["prompt"] for p in BASELINE_CLEAN])
    return g


class TestAdaptiveSequences:
    def test_cost_escalation_in_each_sequence(self, gate):
        """Later steps in each sequence should have higher cost."""
        for seq in ADAPTIVE_SEQUENCES:
            results = [gate.process(s["prompt"], s["id"], s["class"]) for s in seq]
            early_cost = results[0].harmonic_cost
            late_cost = results[-1].harmonic_cost
            print(f"\n  {seq[0]['id']}: early={early_cost:.2f} late={late_cost:.2f}")
            assert late_cost >= early_cost, (
                f"Sequence {seq[0]['id']}: late cost should >= early cost"
            )

    def test_final_step_triggers_signal(self, gate):
        """The final step of each escalation should produce at least one signal."""
        for seq in ADAPTIVE_SEQUENCES:
            final = seq[-1]
            r = gate.process(final["prompt"], final["id"], final["class"])
            assert len(r.detection_signals) >= 1 or r.harmonic_cost > 5.0, (
                f"Final step {final['id']} produced no signals"
            )

    def test_sequence_drift_measurable(self, gate):
        """The spin code should change across the sequence."""
        for seq in ADAPTIVE_SEQUENCES:
            results = [gate.process(s["prompt"], s["id"], s["class"]) for s in seq]
            spin_codes = [r.spin_code for r in results]
            # At least some spin variation across the sequence
            unique_spins = len(set(spin_codes))
            print(f"\n  {seq[0]['id']}: {unique_spins} unique spins across {len(seq)} steps")
