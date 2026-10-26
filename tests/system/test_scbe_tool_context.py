from datetime import datetime, timezone
import math

import pytest

from scripts.system.scbe_tool_context import evaluate_tool_context, poincare_distance


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def _call(command: str, context: dict | None = None) -> dict:
    payload = {
        "tool_name": "functions.exec_command",
        "tool_input": {"cmd": command},
        "session_id": "session-1",
    }
    if context is not None:
        payload["scbe_context"] = context
    return evaluate_tool_context(payload, {"action": "execute"}, now=NOW)


def test_poincare_distance_is_zero_at_same_point_and_rejects_boundary():
    assert poincare_distance([0.1, -0.2], [0.1, -0.2]) == pytest.approx(0.0)
    assert poincare_distance([0.1, 0.0], [0.0, 0.1]) > 0.0
    with pytest.raises(ValueError):
        poincare_distance([1.0, 0.0], [0.0, 0.0])


def test_universal_read_needs_no_lease():
    result = _call("git status --short")
    assert result["capability"] == "read"
    assert result["availability"] == "universal"
    assert result["lease_status"] == "not_required"
    assert result["policy_eligible"] is True


def test_cloud_tool_requires_matching_active_lease():
    missing = _call(
        "kaggle kernels list --mine",
        {"permission_mode": "cloud-dispatch", "enforce_capability_window": True},
    )
    assert missing["capability"] == "network_or_cloud"
    assert missing["policy_eligible"] is False
    assert missing["admission_hint"] == "hold_for_active_lease"

    active = _call(
        "kaggle kernels list --mine",
        {
            "permission_mode": "cloud-dispatch",
            "enforce_capability_window": True,
            "lease": {
                "not_before": "2026-10-26T11:00:00Z",
                "expires_at": "2026-10-26T13:00:00Z",
                "capabilities": ["network_or_cloud"],
            },
        },
    )
    assert active["lease_status"] == "active"
    assert active["policy_eligible"] is True


def test_expired_or_wrong_capability_lease_is_inactive():
    expired = _call(
        "kaggle kernels list --mine",
        {
            "permission_mode": "cloud-dispatch",
            "lease": {
                "not_before": "2026-10-26T09:00:00Z",
                "expires_at": "2026-10-26T10:00:00Z",
                "capabilities": ["network_or_cloud"],
            },
        },
    )
    wrong = _call(
        "kaggle kernels list --mine",
        {
            "permission_mode": "cloud-dispatch",
            "lease": {
                "not_before": "2026-10-26T11:00:00Z",
                "expires_at": "2026-10-26T13:00:00Z",
                "capabilities": ["read"],
            },
        },
    )
    assert expired["lease_valid"] is False
    assert wrong["lease_valid"] is False


def test_layer_derivatives_report_tool_axis_convergence_without_granting_authority():
    baseline_context = {
        "permission_mode": "observe",
        "position_6d": [0.10, 0.05, 0.0, 0.0, 0.0, 0.0],
        "trusted_center_6d": [0.0] * 6,
        "phase_deviation": 0.2,
        "layer_state_14": [0.15] * 14,
        "layer_derivatives_14": [-0.01] * 14,
    }
    result = _call("git status --short", baseline_context)
    assert result["geometry_authority"] == "telemetry_only"
    assert math.isfinite(result["hyperbolic_distance"])
    assert len(result["tool_axis_14"]) == 14
    assert math.isfinite(result["tool_axis_alignment"])
    assert math.isfinite(result["tool_axis_convergence"])
    assert 0.0 < result["route_score"] <= 1.0
    assert result["policy_eligible"] is True


def test_invalid_poincare_position_is_recorded_as_telemetry_error():
    result = _call(
        "git status --short",
        {"position_6d": [1.0, 0, 0, 0, 0, 0], "trusted_center_6d": [0.0] * 6},
    )
    assert "geometry_error" in result
    assert result["policy_eligible"] is True
