"""Deterministic lane-grid scheduler for governed agent coordination.

The packet graph runner handles one route through a state graph. This module
adds the cross-lane control surface: rows are lanes, columns are ticks, and
side-steps are explicit same-column consultations before a column commits.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from .packet import Route, hash_state

LANE_GRID_SCHEMA_VERSION = "scbe_lane_grid_scheduler_v1"
ADVANCE_DECISIONS = {"promote", "advance", "+0"}
HOLD_DECISIONS = {"hold", "-0"}
REJECT_DECISIONS = {"reject", "deny"}
SIDE_STEP_KINDS = {"peek", "challenge", "borrow"}


@dataclass(frozen=True)
class LaneSpec:
    """One scheduler row."""

    lane_id: str
    route: Route
    role: str

    def validate(self) -> None:
        if not self.lane_id:
            raise ValueError("lane_id must be non-empty")
        if not self.role:
            raise ValueError("role must be non-empty")
        self.route.validate()


@dataclass(frozen=True)
class SideStep:
    """Same-column lane consultation."""

    from_lane: str
    to_lane: str
    kind: str
    reason: str

    def validate(self, lane_ids: set[str], lane_order: dict[str, int]) -> None:
        if self.from_lane not in lane_ids:
            raise ValueError(f"from_lane {self.from_lane!r} is not a lane")
        if self.to_lane not in lane_ids:
            raise ValueError(f"to_lane {self.to_lane!r} is not a lane")
        if self.kind not in SIDE_STEP_KINDS:
            raise ValueError(f"kind must be one of {sorted(SIDE_STEP_KINDS)}")
        if not self.reason:
            raise ValueError("reason must be non-empty")
        distance = abs(lane_order[self.from_lane] - lane_order[self.to_lane])
        if self.to_lane != "DR" and distance > 1:
            raise ValueError("side-steps may only target a neighbor lane or DR")


@dataclass(frozen=True)
class LaneCell:
    """One lane output at one scheduler column."""

    lane_id: str
    column: int
    state_hash: str
    proposal: str
    decision: str
    metrics: dict[str, Any] = field(default_factory=dict)
    side_steps: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        if not self.lane_id:
            raise ValueError("lane_id must be non-empty")
        if self.column < 0:
            raise ValueError("column must be >= 0")
        if not self.state_hash:
            raise ValueError("state_hash must be non-empty")
        if self.decision not in ADVANCE_DECISIONS | HOLD_DECISIONS | REJECT_DECISIONS:
            raise ValueError("decision must be promote/advance/+0, hold/-0, or reject/deny")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LaneGridResult:
    """Complete scheduler trace."""

    schema_version: str
    grid_id: str
    task_id: str
    final_column: int
    final_decision: str
    halted_reason: str
    columns: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


LaneHandler = Callable[[LaneSpec, int, str, list[LaneCell]], LaneCell]


def default_lane_handler(lane: LaneSpec, column: int, base_state_hash: str, previous: list[LaneCell]) -> LaneCell:
    """Default deterministic handler: emit a non-pushing continue decision."""

    previous_hashes = [cell.state_hash for cell in previous if cell.lane_id == lane.lane_id]
    state_hash = hash_state(base_state_hash, lane.lane_id, str(column), *previous_hashes[-1:])
    return LaneCell(
        lane_id=lane.lane_id,
        column=column,
        state_hash=state_hash,
        proposal=f"{lane.lane_id} lane continues {lane.role}",
        decision="+0",
        metrics={"route": lane.route.tongue, "permission": lane.route.permission},
    )


class LaneGridScheduler:
    """Column scheduler with -0 HOLD and convergence gates."""

    def __init__(
        self,
        *,
        grid_id: str,
        lanes: Iterable[LaneSpec],
        convergence_columns: Iterable[int] = (),
        side_steps: Iterable[SideStep] = (),
        handler: LaneHandler = default_lane_handler,
        quorum_min: int = 3,
        judge_lane: str = "DR",
    ) -> None:
        if not grid_id:
            raise ValueError("grid_id must be non-empty")
        self.grid_id = grid_id
        self.lanes = list(lanes)
        if not self.lanes:
            raise ValueError("at least one lane is required")
        for lane in self.lanes:
            lane.validate()
        self.lane_ids = {lane.lane_id for lane in self.lanes}
        if len(self.lane_ids) != len(self.lanes):
            raise ValueError("lane_id values must be unique")
        self.lane_order = {lane.lane_id: index for index, lane in enumerate(self.lanes)}
        self.convergence_columns = {column for column in convergence_columns if column >= 0}
        self.side_steps = list(side_steps)
        for side_step in self.side_steps:
            side_step.validate(self.lane_ids, self.lane_order)
        self.handler = handler
        if quorum_min <= 0:
            raise ValueError("quorum_min must be > 0")
        self.quorum_min = quorum_min
        self.judge_lane = judge_lane

    def _side_steps_for(self, lane_id: str) -> list[dict[str, Any]]:
        return [asdict(step) for step in self.side_steps if step.from_lane == lane_id]

    def _column_decision(self, column: int, cells: list[LaneCell]) -> tuple[str, str]:
        decisions = {cell.lane_id: cell.decision for cell in cells}
        if any(decision in REJECT_DECISIONS for decision in decisions.values()):
            return "reject", "lane_reject"
        if any(decision in HOLD_DECISIONS for decision in decisions.values()):
            return "hold", "lane_hold"
        if column in self.convergence_columns:
            advance_count = sum(1 for decision in decisions.values() if decision in ADVANCE_DECISIONS)
            judge_ok = decisions.get(self.judge_lane) in ADVANCE_DECISIONS
            if advance_count < self.quorum_min or not judge_ok:
                return "hold", "convergence_quorum_not_met"
        return "advance", "column_committed"

    def run(self, *, task_id: str, base_state_hash: str, max_columns: int = 4) -> LaneGridResult:
        if not task_id:
            raise ValueError("task_id must be non-empty")
        if not base_state_hash:
            raise ValueError("base_state_hash must be non-empty")
        if max_columns <= 0:
            raise ValueError("max_columns must be > 0")

        history: list[LaneCell] = []
        columns: list[dict[str, Any]] = []
        final_column = 0
        final_decision = "hold"
        halted_reason = "max_columns"

        for column in range(max_columns):
            cells: list[LaneCell] = []
            for lane in self.lanes:
                cell = self.handler(lane, column, base_state_hash, history)
                cell = LaneCell(
                    lane_id=cell.lane_id,
                    column=cell.column,
                    state_hash=cell.state_hash,
                    proposal=cell.proposal,
                    decision=cell.decision,
                    metrics=dict(cell.metrics),
                    side_steps=self._side_steps_for(cell.lane_id),
                    created_at=cell.created_at,
                )
                cell.validate()
                if cell.lane_id != lane.lane_id:
                    raise ValueError("handler returned a cell for the wrong lane")
                if cell.column != column:
                    raise ValueError("handler returned a cell for the wrong column")
                cells.append(cell)

            decision, reason = self._column_decision(column, cells)
            columns.append(
                {
                    "column": column,
                    "decision": decision,
                    "reason": reason,
                    "cells": [cell.to_dict() for cell in cells],
                }
            )
            history.extend(cells)
            final_column = column
            final_decision = decision
            halted_reason = reason
            if decision != "advance":
                break

        return LaneGridResult(
            schema_version=LANE_GRID_SCHEMA_VERSION,
            grid_id=self.grid_id,
            task_id=task_id,
            final_column=final_column,
            final_decision=final_decision,
            halted_reason=halted_reason,
            columns=columns,
        )


def build_six_tongue_lane_grid(
    *,
    convergence_columns: Iterable[int] = (2,),
    side_steps: Iterable[SideStep] = (),
) -> LaneGridScheduler:
    """Canonical six-lane grid for Sacred Tongues coordination."""

    lanes = [
        LaneSpec("KO", Route(tongue="KO", domain="intent", permission="read"), "intent analyst"),
        LaneSpec("AV", Route(tongue="AV", domain="creative", permission="read"), "creative advocate"),
        LaneSpec("RU", Route(tongue="RU", domain="security", permission="read"), "risk reader"),
        LaneSpec("CA", Route(tongue="CA", domain="compute", permission="read"), "compute optimizer"),
        LaneSpec("UM", Route(tongue="UM", domain="governance", permission="read"), "policy arbiter"),
        LaneSpec("DR", Route(tongue="DR", domain="synthesis", permission="merge"), "judge and synthesizer"),
    ]
    return LaneGridScheduler(
        grid_id="scbe-six-tongue-lane-grid-v1",
        lanes=lanes,
        convergence_columns=convergence_columns,
        side_steps=side_steps,
        quorum_min=3,
        judge_lane="DR",
    )


__all__ = [
    "LANE_GRID_SCHEMA_VERSION",
    "LaneCell",
    "LaneGridResult",
    "LaneGridScheduler",
    "LaneSpec",
    "SideStep",
    "build_six_tongue_lane_grid",
    "default_lane_handler",
]
