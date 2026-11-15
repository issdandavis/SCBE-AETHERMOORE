from __future__ import annotations

import unittest

from model_adapter import build_model_view
from test_held_context import fixture_packet


class ModelAdapterTests(unittest.TestCase):
    def test_projection_is_bounded_and_keeps_exact_payloads(self) -> None:
        view = build_model_view(fixture_packet(), current_sequence=100, maximum_tokens=8)
        self.assertEqual(len(view.token_ids), 8)
        self.assertTrue(view.truncated)
        self.assertEqual(view.token_lane_ids, (11,) * 8)
        self.assertIn((10, b"Loop twice; then ABSTAIN."), view.exact_payloads)

    def test_evidence_states_remain_lane_metadata(self) -> None:
        view = build_model_view(fixture_packet(), current_sequence=100)
        evidence_by_lane = {span.lane_id: span.evidence for span in view.lane_spans}
        self.assertNotEqual(evidence_by_lane[20], evidence_by_lane[30])

    def test_expired_lane_is_not_projected(self) -> None:
        view = build_model_view(fixture_packet(), current_sequence=151)
        self.assertNotIn(30, {span.lane_id for span in view.lane_spans})


if __name__ == "__main__":
    unittest.main()
