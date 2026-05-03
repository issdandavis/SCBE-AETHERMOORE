from __future__ import annotations

import pytest

from src.agent_comms import (
    LANE_GRID_SCHEMA_VERSION,
    LaneCell,
    LaneGridScheduler,
    LaneSpec,
    Route,
    SideStep,
    build_six_tongue_lane_grid,
    hash_state,
)


def test_six_tongue_lane_grid_advances_through_convergence_column() -> None:
    grid = build_six_tongue_lane_grid(
        convergence_columns=(2,),
        side_steps=[
            SideStep(from_lane="RU", to_lane="CA", kind="borrow", reason="risk before compute"),
            SideStep(from_lane="UM", to_lane="DR", kind="challenge", reason="judge policy before commit"),
        ],
    )

    result = grid.run(task_id="grid-test", base_state_hash=hash_state("grid-test"), max_columns=3)

    assert result.schema_version == LANE_GRID_SCHEMA_VERSION
    assert result.final_decision == "advance"
    assert result.final_column == 2
    assert [column["column"] for column in result.columns] == [0, 1, 2]
    assert result.columns[2]["decision"] == "advance"
    assert len(result.columns[0]["cells"]) == 6
    ru_cell = next(cell for cell in result.columns[0]["cells"] if cell["lane_id"] == "RU")
    assert ru_cell["side_steps"][0]["to_lane"] == "CA"


def test_lane_grid_minus_zero_holds_column() -> None:
    def hold_handler(lane: LaneSpec, column: int, base_state_hash: str, _previous: list[LaneCell]) -> LaneCell:
        decision = "-0" if lane.lane_id == "RU" and column == 1 else "+0"
        return LaneCell(
            lane_id=lane.lane_id,
            column=column,
            state_hash=hash_state(base_state_hash, lane.lane_id, str(column)),
            proposal="test proposal",
            decision=decision,
        )

    grid = LaneGridScheduler(
        grid_id="hold-grid",
        lanes=[
            LaneSpec("KO", Route(tongue="KO", domain="intent", permission="read"), "intent"),
            LaneSpec("RU", Route(tongue="RU", domain="security", permission="read"), "risk"),
            LaneSpec("DR", Route(tongue="DR", domain="synthesis", permission="merge"), "judge"),
        ],
        convergence_columns=(2,),
        handler=hold_handler,
    )

    result = grid.run(task_id="hold-test", base_state_hash=hash_state("hold-test"), max_columns=4)

    assert result.final_decision == "hold"
    assert result.final_column == 1
    assert result.halted_reason == "lane_hold"
    assert len(result.columns) == 2


def test_convergence_column_requires_judge_lane() -> None:
    def no_judge_handler(lane: LaneSpec, column: int, base_state_hash: str, _previous: list[LaneCell]) -> LaneCell:
        decision = "-0" if lane.lane_id == "DR" and column == 0 else "+0"
        return LaneCell(
            lane_id=lane.lane_id,
            column=column,
            state_hash=hash_state(base_state_hash, lane.lane_id, str(column)),
            proposal="test proposal",
            decision=decision,
        )

    grid = LaneGridScheduler(
        grid_id="judge-grid",
        lanes=[
            LaneSpec("KO", Route(tongue="KO", domain="intent", permission="read"), "intent"),
            LaneSpec("RU", Route(tongue="RU", domain="security", permission="read"), "risk"),
            LaneSpec("DR", Route(tongue="DR", domain="synthesis", permission="merge"), "judge"),
        ],
        convergence_columns=(0,),
        handler=no_judge_handler,
    )

    result = grid.run(task_id="judge-test", base_state_hash=hash_state("judge-test"), max_columns=2)

    assert result.final_decision == "hold"
    assert result.halted_reason == "lane_hold"


def test_side_step_must_target_neighbor_or_dr() -> None:
    with pytest.raises(ValueError, match="neighbor lane or DR"):
        build_six_tongue_lane_grid(
            side_steps=[
                SideStep(from_lane="KO", to_lane="CA", kind="peek", reason="too far without judge"),
            ]
        )


def test_side_step_to_dr_can_cross_rows() -> None:
    grid = build_six_tongue_lane_grid(
        side_steps=[
            SideStep(from_lane="KO", to_lane="DR", kind="challenge", reason="judge escalation"),
        ]
    )

    result = grid.run(task_id="dr-side-step", base_state_hash=hash_state("dr-side-step"), max_columns=1)

    ko_cell = next(cell for cell in result.columns[0]["cells"] if cell["lane_id"] == "KO")
    assert ko_cell["side_steps"][0]["to_lane"] == "DR"
