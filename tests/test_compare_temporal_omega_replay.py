from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.research.compare_temporal_omega_replay import (
    EXPONENTS,
    collect_policy_summaries,
    generate_demo_events,
    load_telemetry_events,
    replay_event_against_policy,
    select_policy_alpha,
)


def test_fixed_two_replay_preserves_live_gate_on_demo_events() -> None:
    events = generate_demo_events(seed=17, turns=6)
    points = [replay_event_against_policy(event, "fixed_2", idx) for idx, event in enumerate(events, start=1)]

    assert points
    assert all(point.decision_flipped is False for point in points)
    for point in points:
        assert point.alpha_value == pytest.approx(2.0)
        assert point.counterfactual_omega == pytest.approx(point.actual_omega, rel=1e-9)
        assert point.counterfactual_harm_score == pytest.approx(point.actual_harm_score, rel=1e-9)


def test_load_telemetry_events_reads_json_and_jsonl(tmp_path: Path) -> None:
    events = generate_demo_events(seed=21, turns=2)

    json_path = tmp_path / "demo.json"
    json_path.write_text(json.dumps({"history": [{"telemetry": events[0]}]}), encoding="utf-8")

    jsonl_path = tmp_path / "demo.jsonl"
    jsonl_path.write_text("\n".join(json.dumps(event) for event in events[1:]), encoding="utf-8")

    loaded = load_telemetry_events([json_path, jsonl_path], demo_seed=7, demo_turns=3)
    assert len(loaded) == len(events)
    assert loaded[0]["schema_version"] == events[0]["schema_version"]


def test_schedule_policies_switch_on_expected_boundaries() -> None:
    assert select_policy_alpha("schedule_guardrail", x_factor=0.75, layer="L2") == pytest.approx(EXPONENTS["sqrt2"])
    assert select_policy_alpha("schedule_guardrail", x_factor=1.50, layer="L2") == pytest.approx(EXPONENTS["2"])
    assert select_policy_alpha("schedule_guardrail", x_factor=2.50, layer="L2") == pytest.approx(EXPONENTS["e"])

    assert select_policy_alpha("schedule_phi_bridge", x_factor=1.50, layer="L2") == pytest.approx(EXPONENTS["phi"])
    assert select_policy_alpha("schedule_layer_guard", x_factor=1.50, layer="L1") == pytest.approx(EXPONENTS["sqrt2"])
    assert select_policy_alpha("schedule_layer_guard", x_factor=2.50, layer="L3") == pytest.approx(EXPONENTS["e"])


def test_policy_summary_reports_fixed_two_as_zero_flip_baseline() -> None:
    events = generate_demo_events(seed=13, turns=5)
    _, summaries = collect_policy_summaries(events, ["fixed_2", "schedule_guardrail"])
    summary_map = {summary.policy_name: summary for summary in summaries}

    assert summary_map["fixed_2"].decision_flip_rate == pytest.approx(0.0)
    assert summary_map["fixed_2"].decision_match_rate == pytest.approx(1.0)
