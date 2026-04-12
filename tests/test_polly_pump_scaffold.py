import math

import pytest

from src.polly_pump.anchors import (
    OrientationFrame,
    SymbolicLocator,
    ZoomAnchor,
    compute_anchor_transition,
)
from src.polly_pump.packet import ModalityProfile
from src.polly_pump.stabilizer import PumpStabilizer


def test_normalize_tongues_returns_probability_vector():
    stabilizer = PumpStabilizer()
    profile = stabilizer.normalize_tongues({"KO": 2.0, "AV": 1.0, "RU": 1.0, "CA": 0.0, "UM": 0.0, "DR": 0.0})
    assert len(profile) == 6
    assert math.isclose(sum(profile), 1.0, rel_tol=0.0, abs_tol=1e-9)
    assert profile[0] > profile[1]


def test_null_pressure_increases_with_missing_channels():
    stabilizer = PumpStabilizer(active_threshold=0.15)
    dense = stabilizer.compute_null_pressure([1, 1, 1, 1, 1, 1])
    sparse = stabilizer.compute_null_pressure([10, 0, 0, 0, 0, 0])
    assert dense < sparse


def test_harmony_prefers_coverage_and_retrieval():
    stabilizer = PumpStabilizer()
    weak = stabilizer.compute_harmony(
        [10, 0, 0, 0, 0, 0],
        ModalityProfile(visual=1.0, audio=0.0, empirical=0.0),
        retrieval_density=0.0,
    )
    strong = stabilizer.compute_harmony(
        [1, 1, 1, 1, 1, 1],
        ModalityProfile(visual=1.0, audio=1.0, empirical=1.0),
        retrieval_density=0.9,
    )
    assert strong > weak


def test_anchor_transition_prefers_close_aligned_same_hall():
    close = ZoomAnchor(
        anchor_id="a",
        symbolic_locator=SymbolicLocator("wing_a", "hall_facts", "auth"),
        scale_band=1.0,
        gateway_type="zoom",
        orientation=OrientationFrame(bearing_deg=0.0, celestial_anchor="orion"),
        manifold_position=(0.0, 0.0, 0.0),
    )
    near = ZoomAnchor(
        anchor_id="b",
        symbolic_locator=SymbolicLocator("wing_a", "hall_facts", "auth"),
        scale_band=1.1,
        gateway_type="zoom",
        orientation=OrientationFrame(bearing_deg=10.0, celestial_anchor="orion"),
        manifold_position=(0.02, 0.01, 0.0),
    )
    far = ZoomAnchor(
        anchor_id="c",
        symbolic_locator=SymbolicLocator("wing_b", "hall_events", "billing"),
        scale_band=3.0,
        gateway_type="tunnel",
        orientation=OrientationFrame(bearing_deg=170.0, celestial_anchor="sirius"),
        manifold_position=(0.8, 0.8, 0.8),
    )
    near_transition = compute_anchor_transition(close, near)
    far_transition = compute_anchor_transition(close, far)
    assert near_transition.transition_cost < far_transition.transition_cost


def test_build_packet_carries_null_pattern_and_clamps_density():
    stabilizer = PumpStabilizer()
    packet = stabilizer.build_packet(
        [10, 0, 0, 0, 0, 0],
        governance_posture="observe",
        routing_hint="hall_facts/auth",
        modality=ModalityProfile(visual=0.3, audio=0.2, empirical=0.5),
        retrieval_density=2.0,
    )
    assert packet.retrieval_density == pytest.approx(1.0)
    assert len(packet.null_pattern) == 6
    assert packet.null_pressure > 0.0
