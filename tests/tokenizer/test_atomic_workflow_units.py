from src.tokenizer.atomic_workflow_units import (
    ResourceBudget,
    build_atomic_workflow_unit,
    compose_workflow,
)


def test_atomic_workflow_unit_keeps_semantic_and_chemistry_lanes_separate() -> None:
    unit = build_atomic_workflow_unit("scan_area")

    assert unit["semantic_lane"]["role"] == "observe"
    assert unit["chemistry_lane"]["mode"] == "structural_template"
    assert unit["chemistry_lane"]["byte_signature"]["hex"]
    assert set(unit["resource_cost"]) == {"power", "compute", "time", "comms", "wear"}


def test_material_chemistry_lane_only_triggers_on_direct_element_symbols() -> None:
    material = build_atomic_workflow_unit("FeCl")
    code = build_atomic_workflow_unit("def")

    assert material["chemistry_lane"]["mode"] == "material"
    assert material["chemistry_lane"]["material_elements"] == ["Fe", "Cl"]
    assert code["chemistry_lane"]["mode"] == "structural_template"
    assert code["chemistry_lane"]["material_elements"] == []


def test_workflow_composition_degrades_when_falling_budget_blocks_action() -> None:
    report = compose_workflow(
        ["scan_area", "plan_route", "fly_forward", "send_report"],
        budget=ResourceBudget(power=0.22, compute=0.22, time=0.22, comms=0.22, wear=0.22),
        decay_floor=0.20,
    )

    assert report["decision"] == "degrade_or_replan"
    assert report["degradation_events"]
    assert report["degradation_events"][0]["fallback"] == "hold"
    assert report["degradation_events"][0]["mode"] == "steady_state_fallback"
    assert "momentum_after" in report["degradation_events"][0]
    assert report["readvance_attempts"]


def test_workflow_composition_executes_under_sufficient_budget() -> None:
    report = compose_workflow(
        ["scan_area", "measure_state", "plan_route", "send_report"],
        budget=ResourceBudget(power=5.0, compute=5.0, time=5.0, comms=5.0, wear=5.0),
        decay_floor=1.0,
    )

    assert report["decision"] == "execute"
    assert not report["degradation_events"]
    assert report["spent"]["power"] > 0


def test_steady_state_fallback_can_readvance_from_cheaper_footing() -> None:
    report = compose_workflow(
        ["scan_area", "plan_route", "fly_forward"],
        budget=ResourceBudget(power=1.20, compute=1.20, time=1.20, comms=1.20, wear=1.20),
        decay_floor=0.35,
    )

    accepted = [row for row in report["readvance_attempts"] if row["status"] == "accepted"]
    assert accepted
    assert accepted[0]["token"] in {"route_readvance", "stabilize_readvance", "measure_readvance"}
