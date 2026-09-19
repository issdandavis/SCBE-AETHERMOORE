"""Deterministic tests for composition-aware fleet coordination."""

from __future__ import annotations

import pytest

from src.fleet.composition_coordinator import (
    CoordinationPolicy,
    FleetComposition,
    FleetCompositionCoordinator,
    FleetMember,
    FleetTask,
    NetworkCondition,
    composition_geometry,
    simulate_mission,
    task_fit,
    transition_measure,
)


def axis(index: int) -> tuple[float, ...]:
    values = [0.0] * 6
    values[index] = 1.0
    return tuple(values)


def member(member_id: str, index: int, *, cost: float = 1.0) -> FleetMember:
    tongues = ("KO", "AV", "RU", "CA", "UM", "DR")
    return FleetMember(
        member_id=member_id,
        tongue=tongues[index],
        capability_vector=axis(index),
        base_cost=cost,
        reliability=1.0,
        latency_ticks=1,
    )


def fixtures() -> tuple[FleetComposition, FleetComposition, FleetComposition]:
    clone = FleetComposition(
        "clone-line",
        tuple(
            FleetMember(
                member_id=f"clone-{idx}",
                tongue="KO",
                capability_vector=axis(0),
                base_cost=0.5,
                reliability=1.0,
            )
            for idx in range(5)
        ),
        "DR",
    )
    partial = FleetComposition(
        "partial",
        tuple(member(f"role-{idx}", idx) for idx in range(3)),
        "DR",
    )
    full = FleetComposition(
        "full-spectrum",
        tuple(member(f"role-{idx}", idx) for idx in range(6)),
        "DR",
    )
    return clone, partial, full


def test_clone_line_is_rank_one_and_full_spectrum_has_no_blind_dimension() -> None:
    clone, _partial, full = fixtures()
    clone_geometry = composition_geometry(clone)
    full_geometry = composition_geometry(full)

    assert clone_geometry.rank == 1
    assert clone_geometry.blind_dimensions == 5
    assert full_geometry.rank == 6
    assert full_geometry.blind_dimensions == 0


def test_task_fit_exposes_a_clone_blind_direction() -> None:
    clone, _partial, full = fixtures()
    task = FleetTask("dr-task", axis(5), required_governance_tier="DR")

    assert task_fit(clone, task).coverage == pytest.approx(0.0)
    assert task_fit(clone, task).blind_residual == pytest.approx(1.0)
    assert task_fit(full, task).coverage == pytest.approx(1.0)


def test_transition_is_stable_to_self_and_directional_between_rosters() -> None:
    _clone, partial, full = fixtures()

    assert transition_measure(full, full, inertia=0.9).stability == 1.0
    assert transition_measure(full, full, inertia=0.9).cost == 0.0

    growing = transition_measure(partial, full, inertia=0.5)
    shrinking = transition_measure(full, partial, inertia=0.5)
    assert 0.0 <= growing.stability <= 1.0
    assert 0.0 <= shrinking.stability <= 1.0
    assert growing.stability != shrinking.stability
    assert growing.cost != shrinking.cost


def test_governance_is_a_hard_gate_before_geometry() -> None:
    low = FleetComposition("low", (member("low-member", 0),), "KO")
    coordinator = FleetCompositionCoordinator([low])
    task = FleetTask("critical", axis(0), required_governance_tier="DR")

    decision = coordinator.select(
        task,
        policy=CoordinationPolicy.COMPOSITION_AWARE,
        previous_composition_id=None,
        network=NetworkCondition("nominal"),
    )

    assert decision.outcome == "DENY"
    assert decision.selected_composition_id is None
    assert decision.candidate_evaluations == 0


def test_composition_aware_router_selects_coverage_over_cheap_blind_clones() -> None:
    clone, _partial, full = fixtures()
    coordinator = FleetCompositionCoordinator([clone, full])
    task = FleetTask("dr-task", axis(5), required_governance_tier="DR", risk=0.9)

    decision = coordinator.select(
        task,
        policy=CoordinationPolicy.COMPOSITION_AWARE,
        previous_composition_id=None,
        network=NetworkCondition("nominal"),
    )

    assert decision.selected_composition_id == "full-spectrum"
    assert decision.candidate_evaluations == 2
    assert decision.control_cost == pytest.approx(2 * 0.005 + 2 * 0.08)


def test_composition_aware_router_holds_when_no_roster_meets_coverage_contract() -> None:
    clone, _partial, _full = fixtures()
    coordinator = FleetCompositionCoordinator([clone])
    task = FleetTask("blind", axis(5), required_governance_tier="KO", minimum_coverage=0.9)

    decision = coordinator.select(
        task,
        policy=CoordinationPolicy.COMPOSITION_AWARE,
        previous_composition_id=None,
        network=NetworkCondition("nominal"),
    )

    assert decision.outcome == "HOLD"
    assert decision.selected_composition_id is None
    assert decision.candidate_evaluations == 1


def test_composition_aware_router_prefers_a_deadline_valid_roster() -> None:
    slow = FleetComposition(
        "slow",
        (FleetMember("slow-member", "KO", axis(0), base_cost=0.1, reliability=1.0, latency_ticks=20),),
        "KO",
    )
    fast = FleetComposition(
        "fast",
        (FleetMember("fast-member", "KO", axis(0), base_cost=2.0, reliability=1.0, latency_ticks=1),),
        "KO",
    )
    task = FleetTask("urgent", axis(0), deadline_ticks=5)

    decision = FleetCompositionCoordinator([slow, fast]).select(
        task,
        policy=CoordinationPolicy.COMPOSITION_AWARE,
        previous_composition_id=None,
        network=NetworkCondition("nominal"),
    )

    assert decision.selected_composition_id == "fast"


def test_stability_guard_holds_a_valid_roster_until_minimum_dwell() -> None:
    expensive = FleetComposition(
        "expensive",
        (FleetMember("expensive-member", "KO", axis(0), base_cost=5.0, reliability=1.0),),
        "KO",
    )
    cheap = FleetComposition(
        "cheap",
        (FleetMember("cheap-member", "KO", axis(0), base_cost=0.1, reliability=1.0),),
        "KO",
    )
    task = FleetTask("steady", axis(0), deadline_ticks=20)
    coordinator = FleetCompositionCoordinator([expensive, cheap])

    held = coordinator.select(
        task,
        policy=CoordinationPolicy.STABILITY_GUARDED,
        previous_composition_id="expensive",
        previous_dwell_tasks=1,
        network=NetworkCondition("nominal"),
    )
    released = coordinator.select(
        task,
        policy=CoordinationPolicy.STABILITY_GUARDED,
        previous_composition_id="expensive",
        previous_dwell_tasks=coordinator.MINIMUM_DWELL_TASKS,
        network=NetworkCondition("nominal"),
    )

    assert held.selected_composition_id == "expensive"
    assert released.selected_composition_id == "cheap"


def test_size_matched_distance_control_bills_every_candidate() -> None:
    clone, partial, full = fixtures()
    coordinator = FleetCompositionCoordinator([clone, partial, full])
    task = FleetTask("mixed", (1, 1, 1, 1, 1, 1), required_governance_tier="KO")

    decision = coordinator.select(
        task,
        policy=CoordinationPolicy.DISTANCE,
        previous_composition_id=None,
        network=NetworkCondition("nominal"),
    )

    assert decision.candidate_evaluations == 3
    assert len(decision.assessments) == 3
    assert decision.control_cost == pytest.approx(3 * 0.005 + 3 * 0.04)


def test_decision_receipt_is_deterministic() -> None:
    clone, partial, full = fixtures()
    task = FleetTask("stable", (1, 0, 1, 0, 1, 0), required_governance_tier="KO")
    network = NetworkCondition("nominal")

    first = FleetCompositionCoordinator([clone, partial, full]).select(
        task,
        policy=CoordinationPolicy.COMPOSITION_AWARE,
        previous_composition_id=None,
        network=network,
    )
    second = FleetCompositionCoordinator([full, clone, partial]).select(
        task,
        policy=CoordinationPolicy.COMPOSITION_AWARE,
        previous_composition_id=None,
        network=network,
    )

    assert first == second
    assert len(first.receipt_digest) == 64


def test_custody_retransmit_converges_while_permanent_loss_does_not() -> None:
    _clone, _partial, full = fixtures()
    tasks = [
        FleetTask(f"task-{idx}", axis(idx % 6), required_governance_tier="KO", deadline_ticks=50) for idx in range(12)
    ]

    custody = simulate_mission(
        [full],
        tasks,
        policy=CoordinationPolicy.STICKY,
        network=NetworkCondition("custody", drop_probability=1.0, custody_retransmit=True),
        seed=7,
    )
    loss = simulate_mission(
        [full],
        tasks,
        policy=CoordinationPolicy.STICKY,
        network=NetworkCondition("loss", drop_probability=1.0, custody_retransmit=False),
        seed=7,
    )

    assert custody.state_converged is True
    assert custody.retransmissions == len(tasks)
    assert custody.permanent_losses == 0
    assert loss.state_converged is False
    assert loss.permanent_losses == len(tasks)
    assert loss.completed == 0


def test_duplicate_delivery_is_deduplicated_and_simulation_replays_exactly() -> None:
    _clone, _partial, full = fixtures()
    tasks = [
        FleetTask(f"task-{idx}", axis(idx % 6), required_governance_tier="KO", deadline_ticks=50) for idx in range(18)
    ]
    network = NetworkCondition("duplicates", duplicate_probability=1.0)

    first = simulate_mission(
        [full],
        tasks,
        policy=CoordinationPolicy.STICKY,
        network=network,
        seed=11,
    )
    second = simulate_mission(
        [full],
        tasks,
        policy=CoordinationPolicy.STICKY,
        network=network,
        seed=11,
    )

    assert first == second
    assert first.duplicates == len(tasks)
    assert first.transmissions == 2 * len(tasks)
    assert first.completed <= len(tasks)
    assert first.state_converged is True


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="6 values"):
        FleetMember("bad", "KO", (1.0, 0.0))
    with pytest.raises(ValueError, match="zero vector"):
        FleetTask("bad", (0.0,) * 6)
    with pytest.raises(ValueError, match="unique"):
        repeated = member("same", 0)
        FleetComposition("bad", (repeated, repeated), "KO")
