#!/usr/bin/env python3
"""MAHSS game-gym planner for agent routing.

This turns Pacman/Tetris-style game mechanics into deterministic task-routing
receipts. A weak model can later propose moves; this script is the system that
scores whether the move actually advances the goal.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_PACMAN_BOARD = """
#########
#A..V...#
#.###.#.#
#...#.#S#
#.#...#.#
#B..X...#
#########
""".strip()


MOVE_DELTAS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}


GODOT_SCBE_ENDPOINTS = {
    "codex_evaluate": "/api/game/codex/evaluate",
    "companion_update": "/api/game/companion/update",
    "evolution_check": "/api/game/evolution/check/{companion_id}",
    "combat_result": "/api/game/combat/result",
    "tower_floor": "/api/game/tower/floor/{floor}",
    "event_log": "/api/game/events/log",
    "egg_check": "/api/game/eggs/check",
}


GODOT_EVENT_TYPE_BY_ACTION = {
    "observe": "exploration_action",
    "route": "tower_strategy",
    "execute": "companion_command",
    "verify": "codex_query",
    "receipt": "companion_response",
}


@dataclass(frozen=True)
class PacmanPlan:
    path: tuple[str, ...]
    positions: tuple[tuple[int, int], ...]
    goals_collected: tuple[str, ...]
    hazard_hits: int
    score: float
    receipt: dict[str, Any]


@dataclass(frozen=True)
class TetrisPiece:
    piece_id: str
    lane: str
    role: str
    fit: tuple[float, float, float]
    risk: float
    produces: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class TetrisSlot:
    slot_id: str
    accepts: tuple[str, ...]
    need: tuple[float, float, float]
    risk_capacity: float
    available: tuple[str, ...] = ()


@dataclass(frozen=True)
class TetrisLock:
    slot_id: str
    piece_id: str
    locked: bool
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorldActor:
    actor_id: str
    role: str
    goal: str
    location: str
    tools: tuple[str, ...]
    trust: float


@dataclass(frozen=True)
class WorldAction:
    action_id: str
    actor_id: str
    kind: str
    target: str
    requires_tool: str
    produces: tuple[str, ...]
    risk: float
    world_delta: dict[str, Any]


@dataclass(frozen=True)
class WorldTick:
    tick: int
    actor_id: str
    observation: dict[str, Any]
    proposed_action: str
    policy: dict[str, Any]
    resolved: bool
    world_delta: dict[str, Any]
    memory: dict[str, Any]
    receipt: dict[str, Any]


def _parse_board(board: str) -> tuple[list[list[str]], tuple[int, int], set[tuple[int, int]], dict[tuple[int, int], str]]:
    rows = [list(line.rstrip()) for line in board.strip().splitlines() if line.strip()]
    if not rows:
        raise ValueError("empty board")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("board rows must have equal width")

    start: tuple[int, int] | None = None
    hazards: set[tuple[int, int]] = set()
    goals: dict[tuple[int, int], str] = {}
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if cell == "A":
                start = (r, c)
            elif cell == "X":
                hazards.add((r, c))
            elif cell in {"B", "V", "S"}:
                goals[(r, c)] = cell
    if start is None:
        raise ValueError("board must contain A start cell")
    return rows, start, hazards, goals


def _goal_name(token: str) -> str:
    return {
        "B": "build",
        "V": "verify",
        "S": "ship",
    }.get(token, token)


def plan_pacman(board: str = DEFAULT_PACMAN_BOARD, *, max_depth: int = 18, limit: int = 5) -> dict[str, Any]:
    """Plan Pacman-like routes through build/verify/ship goals while avoiding hazards."""

    grid, start, hazards, goals = _parse_board(board)
    all_goals = frozenset(goals.values())
    queue = deque([(start, tuple(), (start,), frozenset(), 0)])
    seen = {(start, frozenset(), 0)}
    finished: list[PacmanPlan] = []

    while queue:
        pos, moves, positions, collected, hazard_hits = queue.popleft()
        if len(moves) >= max_depth:
            continue
        for move, (dr, dc) in MOVE_DELTAS.items():
            nr, nc = pos[0] + dr, pos[1] + dc
            if nr < 0 or nc < 0 or nr >= len(grid) or nc >= len(grid[0]):
                continue
            cell = grid[nr][nc]
            if cell == "#":
                continue
            next_pos = (nr, nc)
            next_collected = set(collected)
            if next_pos in goals:
                next_collected.add(goals[next_pos])
            next_hazards = hazard_hits + (1 if next_pos in hazards else 0)
            next_moves = (*moves, move)
            next_positions = (*positions, next_pos)
            key = (next_pos, frozenset(next_collected), next_hazards)
            if key in seen:
                continue
            seen.add(key)
            score = (12.0 * len(next_collected)) - (0.75 * len(next_moves)) - (25.0 * next_hazards)
            if next_collected == all_goals:
                finished.append(
                    PacmanPlan(
                        path=next_moves,
                        positions=next_positions,
                        goals_collected=tuple(_goal_name(goal) for goal in sorted(next_collected)),
                        hazard_hits=next_hazards,
                        score=round(score, 3),
                        receipt={
                            "complete": True,
                            "steps": len(next_moves),
                            "hazards": next_hazards,
                            "goals": tuple(_goal_name(goal) for goal in sorted(next_collected)),
                        },
                    )
                )
            queue.append((next_pos, next_moves, next_positions, frozenset(next_collected), next_hazards))

    ranked = sorted(finished, key=lambda plan: (-plan.score, plan.hazard_hits, len(plan.path), plan.path))[:limit]
    return {
        "schema": "scbe_mahss_pacman_plan_v1",
        "game": "pacman",
        "board": ["".join(row) for row in grid],
        "legend": {
            "A": "agent start",
            "B": "build goal",
            "V": "verify goal",
            "S": "ship goal",
            "X": "hazard / unsafe shortcut",
            "#": "wall",
        },
        "max_depth": max_depth,
        "goal_count": len(all_goals),
        "plan_count": len(ranked),
        "plans": [
            {
                "rank": idx + 1,
                "path": list(plan.path),
                "positions": [list(pos) for pos in plan.positions],
                "goals_collected": list(plan.goals_collected),
                "hazard_hits": plan.hazard_hits,
                "score": plan.score,
                "receipt": plan.receipt,
            }
            for idx, plan in enumerate(ranked)
        ],
        "top_move": ranked[0].path[0] if ranked else None,
        "complete": bool(ranked),
    }


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b, strict=True)) ** 0.5


def _score_lock(piece: TetrisPiece, slot: TetrisSlot, available: set[str]) -> TetrisLock:
    reasons: list[str] = []
    if piece.lane not in slot.accepts:
        reasons.append(f"lane {piece.lane} not accepted")
    missing = [req for req in piece.requires if req not in available and req not in slot.available]
    if missing:
        reasons.append(f"missing {missing}")
    if piece.risk > slot.risk_capacity:
        reasons.append(f"risk {piece.risk:.2f} exceeds {slot.risk_capacity:.2f}")
    fit_score = max(0.0, 1.0 - (_distance(piece.fit, slot.need) / (3.0**0.5)))
    risk_score = max(0.0, 1.0 - (piece.risk / max(slot.risk_capacity, 0.001)))
    score = round((0.72 * fit_score) + (0.28 * risk_score), 6)
    if score < 0.55:
        reasons.append(f"score {score:.3f} below lock threshold")
    return TetrisLock(slot.slot_id, piece.piece_id, not reasons, score, tuple(reasons))


def default_tetris_pieces() -> list[TetrisPiece]:
    return [
        TetrisPiece("receiver_model", "receive", "parse request into state", (0.95, 0.55, 0.85), 0.08, ("parsed",)),
        TetrisPiece("router_model", "route", "select backend/tool lane", (0.80, 0.90, 0.85), 0.16, ("route",), ("parsed",)),
        TetrisPiece("tool_executor", "execute", "run bounded tool action", (0.65, 0.75, 0.82), 0.24, ("artifact",), ("route",)),
        TetrisPiece("verifier_model", "verify", "score result and catch drift", (0.70, 0.98, 0.92), 0.10, ("verified",), ("artifact",)),
        TetrisPiece("manager_model", "exception", "handle jam/escalation only", (0.55, 0.92, 0.98), 0.38, ("manager_decision",), ("verified",)),
        TetrisPiece("unsafe_direct_llm", "execute", "model tries to do everything directly", (0.30, 0.20, 0.25), 0.88, ("artifact",)),
    ]


def default_tetris_slots() -> list[TetrisSlot]:
    return [
        TetrisSlot("receiving", ("receive",), (0.95, 0.55, 0.85), 0.20),
        TetrisSlot("sortation_router", ("route",), (0.82, 0.92, 0.90), 0.30, ("parsed",)),
        TetrisSlot("workstation", ("execute",), (0.62, 0.76, 0.86), 0.35, ("route",)),
        TetrisSlot("quality_gate", ("verify",), (0.70, 0.98, 0.95), 0.25, ("artifact",)),
        TetrisSlot("shipping", ("exception", "verify"), (0.60, 0.90, 0.98), 0.45, ("verified",)),
    ]


def plan_tetris(*, limit: int = 5) -> dict[str, Any]:
    """Lock AI/workstation pieces into a warehouse-like route."""

    pieces = default_tetris_pieces()
    slots = default_tetris_slots()
    remaining = list(pieces)
    available: set[str] = set()
    locks: list[TetrisLock] = []

    for slot in slots:
        scored = [_score_lock(piece, slot, available) for piece in remaining]
        valid = [lock for lock in scored if lock.locked]
        if not valid:
            locks.append(TetrisLock(slot.slot_id, "", False, 0.0, ("no piece fit this slot",)))
            continue
        best = max(valid, key=lambda lock: (lock.score, lock.piece_id))
        locks.append(best)
        chosen = next(piece for piece in remaining if piece.piece_id == best.piece_id)
        available.update(chosen.produces)
        available.update(slot.available)
        remaining = [piece for piece in remaining if piece.piece_id != chosen.piece_id]

    rejected = [
        asdict(lock)
        for piece in remaining
        for lock in [_score_lock(piece, slots[min(len(locks) - 1, len(slots) - 1)], available)]
        if not lock.locked
    ][:limit]

    return {
        "schema": "scbe_mahss_tetris_lock_v1",
        "game": "tetris",
        "analogy": "Pieces are models/tools; slots are facility stations. A piece only matters if it locks.",
        "locks": [asdict(lock) for lock in locks],
        "locked_count": sum(1 for lock in locks if lock.locked),
        "rejected_examples": rejected,
        "complete": all(lock.locked for lock in locks),
        "system_law": "deterministic slots judge model moves; models propose pieces but the board decides what locks",
    }


def _default_world() -> tuple[dict[str, Any], list[WorldActor], list[WorldAction]]:
    state = {
        "workspace": {
            "request": "ship a verified local shell improvement",
            "repo_dirty": True,
            "tests_green": False,
            "receipt_written": False,
            "artifact": "",
            "risk": 0.18,
        },
        "quests": {
            "understand": "open",
            "route": "blocked",
            "execute": "blocked",
            "verify": "blocked",
            "ship": "blocked",
        },
        "inventory": ["read_repo", "route_task", "bounded_shell", "pytest", "receipt_writer"],
        "events": [],
    }
    actors = [
        WorldActor("receiver_npc", "receiver", "understand request", "intake", ("read_repo",), 0.92),
        WorldActor("router_npc", "router", "select station", "sortation", ("route_task",), 0.86),
        WorldActor("worker_npc", "worker", "change world state", "workstation", ("bounded_shell",), 0.74),
        WorldActor("verifier_npc", "verifier", "prove output", "quality_gate", ("pytest",), 0.90),
        WorldActor("scribe_npc", "scribe", "write receipt", "shipping", ("receipt_writer",), 0.88),
    ]
    actions = [
        WorldAction(
            "observe_request",
            "receiver_npc",
            "observe",
            "workspace.request",
            "read_repo",
            ("parsed_request",),
            0.05,
            {"quests": {"understand": "done", "route": "open"}, "events": ["receiver parsed request"]},
        ),
        WorldAction(
            "route_to_station",
            "router_npc",
            "route",
            "quests.route",
            "route_task",
            ("route_plan",),
            0.12,
            {"quests": {"route": "done", "execute": "open"}, "events": ["router selected bounded shell workstation"]},
        ),
        WorldAction(
            "apply_bounded_change",
            "worker_npc",
            "execute",
            "workspace.artifact",
            "bounded_shell",
            ("artifact",),
            0.30,
            {
                "workspace": {"artifact": "mahss_game_gym_world_loop", "repo_dirty": True},
                "quests": {"execute": "done", "verify": "open"},
                "events": ["worker changed sandboxed workspace state"],
            },
        ),
        WorldAction(
            "run_quality_gate",
            "verifier_npc",
            "verify",
            "workspace.tests_green",
            "pytest",
            ("green_tests",),
            0.10,
            {"workspace": {"tests_green": True}, "quests": {"verify": "done", "ship": "open"}, "events": ["verifier marked tests green"]},
        ),
        WorldAction(
            "write_shipping_receipt",
            "scribe_npc",
            "receipt",
            "workspace.receipt_written",
            "receipt_writer",
            ("receipt",),
            0.04,
            {"workspace": {"receipt_written": True}, "quests": {"ship": "done"}, "events": ["scribe wrote final receipt"]},
        ),
    ]
    return state, actors, actions


def _merge_delta(state: dict[str, Any], delta: dict[str, Any]) -> None:
    for key, value in delta.items():
        if key == "events":
            state.setdefault("events", []).extend(value)
        elif isinstance(value, dict) and isinstance(state.get(key), dict):
            state[key].update(value)
        else:
            state[key] = value


def _observe(actor: WorldActor, state: dict[str, Any], memory: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "location": actor.location,
        "goal": actor.goal,
        "open_quests": [name for name, status in state["quests"].items() if status == "open"],
        "available_tools": [tool for tool in actor.tools if tool in state["inventory"]],
        "recent_memory": memory[-2:],
        "workspace": dict(state["workspace"]),
    }


def _policy_check(actor: WorldActor, action: WorldAction, state: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if action.actor_id != actor.actor_id:
        reasons.append("wrong_actor")
    if action.requires_tool not in actor.tools:
        reasons.append("actor_lacks_tool")
    if action.requires_tool not in state["inventory"]:
        reasons.append("tool_not_in_inventory")
    if action.risk > actor.trust:
        reasons.append("risk_exceeds_actor_trust")
    if action.kind == "execute" and state["quests"].get("route") != "done":
        reasons.append("execution_before_route")
    if action.kind == "verify" and not state["workspace"].get("artifact"):
        reasons.append("verify_without_artifact")
    allowed = not reasons
    return {
        "allowed": allowed,
        "reasons": reasons,
        "risk": action.risk,
        "actor_trust": actor.trust,
        "required_tool": action.requires_tool,
    }


def _godot_event_payload(
    *,
    tick_number: int,
    actor: WorldActor,
    action: WorldAction,
    policy: dict[str, Any],
    resolved: bool,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Build a payload matching the repo's Godot SCBE client/training concepts."""

    safety_score = max(0.0, min(1.0, actor.trust - (action.risk * 0.5)))
    if not policy["allowed"]:
        safety_score = min(safety_score, 0.35)
    return {
        "event_type": GODOT_EVENT_TYPE_BY_ACTION.get(action.kind, "exploration_action"),
        "session_id": "mahss_game_gym_session",
        "player_id": "aetherdesk_operator",
        "companion_id": actor.actor_id,
        "context": {
            "tongue_vector": [0.18, 0.14, 0.12, 0.24, 0.10, 0.22],
            "location": actor.location,
            "companion_hp_ratio": 1.0,
            "enemy_count": 1 if action.risk >= 0.3 else 0,
            "formation_type": "factory_line",
            "bond_level": max(1, int(actor.trust * 7)),
            "evolution_stage": "operator_shell",
            "status_effects": ["blocked"] if not policy["allowed"] else [],
        },
        "action": {
            "action_id": action.action_id,
            "description": f"{actor.role} performs {action.kind} on {action.target}",
            "source": "companion" if actor.role != "receiver" else "system",
            "confidence": round(actor.trust, 3),
        },
        "outcome": {
            "success": resolved,
            "numeric_result": 1.0 if resolved else -1.0,
            "description": "world state advanced" if resolved else "blocked by policy gate",
            "tongue_shift": [0.0, 0.0, 0.0, 0.03 if resolved else -0.02, 0.0, 0.02 if resolved else 0.0],
            "safety_score": round(safety_score, 3),
        },
        "godot_bridge": {
            "source_script": "game/godot/scripts/scbe/scbe_client.gd",
            "post_endpoint": GODOT_SCBE_ENDPOINTS["event_log"],
            "tick": tick_number,
        },
        "world_snapshot": {
            "quests": dict(state["quests"]),
            "workspace": dict(state["workspace"]),
        },
    }


def simulate_world(*, max_ticks: int = 8) -> dict[str, Any]:
    """Run a deeper NPC-style workflow loop over mutable world state."""

    state, actors, actions = _default_world()
    actor_by_id = {actor.actor_id: actor for actor in actors}
    memory: list[dict[str, Any]] = []
    ticks: list[WorldTick] = []
    completed_actions: set[str] = set()

    for tick_number in range(1, max_ticks + 1):
        candidate = next((action for action in actions if action.action_id not in completed_actions), None)
        if candidate is None:
            break
        actor = actor_by_id[candidate.actor_id]
        observation = _observe(actor, state, memory)
        policy = _policy_check(actor, candidate, state)
        world_delta: dict[str, Any] = {}
        resolved = False
        if policy["allowed"]:
            world_delta = candidate.world_delta
            _merge_delta(state, world_delta)
            completed_actions.add(candidate.action_id)
            resolved = True
        memory_entry = {
            "tick": tick_number,
            "actor": actor.actor_id,
            "action": candidate.action_id,
            "resolved": resolved,
            "produced": list(candidate.produces) if resolved else [],
        }
        memory.append(memory_entry)
        godot_event = _godot_event_payload(
            tick_number=tick_number,
            actor=actor,
            action=candidate,
            policy=policy,
            resolved=resolved,
            state=state,
        )
        receipt = {
            "schema": "scbe_mahss_world_tick_receipt_v1",
            "tick": tick_number,
            "actor": actor.actor_id,
            "action": candidate.action_id,
            "allowed": policy["allowed"],
            "resolved": resolved,
            "quest_state": dict(state["quests"]),
            "workspace_state": dict(state["workspace"]),
            "godot_event_type": godot_event["event_type"],
            "godot_event_endpoint": GODOT_SCBE_ENDPOINTS["event_log"],
        }
        ticks.append(
            WorldTick(
                tick=tick_number,
                actor_id=actor.actor_id,
                observation=observation,
                proposed_action=candidate.action_id,
                policy=policy,
                resolved=resolved,
                world_delta=world_delta,
                memory={**memory_entry, "godot_event": godot_event},
                receipt=receipt,
            )
        )
        if all(status == "done" for status in state["quests"].values()):
            break

    return {
        "schema": "scbe_mahss_world_loop_v1",
        "game": "world",
        "analogy": "NPC workflow engine: actors perceive world state, propose actions, policy resolves effects, receipts update memory.",
        "loop": [
            "world_state",
            "actor_observation",
            "intent_selection",
            "policy_gate",
            "action_resolution",
            "world_delta",
            "memory_update",
            "receipt",
            "next_tick",
        ],
        "actors": [asdict(actor) for actor in actors],
        "ticks": [asdict(tick) for tick in ticks],
        "godot_bridge": {
            "project": "game/godot/project.godot",
            "client_script": "game/godot/scripts/scbe/scbe_client.gd",
            "companion_script": "game/godot/scripts/companion/companion_ai.gd",
            "codex_ui_script": "game/godot/scripts/ui/codex_terminal_ui.gd",
            "endpoints": GODOT_SCBE_ENDPOINTS,
            "event_types": sorted(set(GODOT_EVENT_TYPE_BY_ACTION.values())),
        },
        "final_state": state,
        "complete": all(status == "done" for status in state["quests"].values()),
        "depth_metrics": {
            "tick_count": len(ticks),
            "actor_count": len(actors),
            "event_count": len(state["events"]),
            "receipt_count": len(ticks),
            "state_layers": ["workspace", "quests", "inventory", "events", "memory"],
        },
    }


def build_report(game: str) -> dict[str, Any]:
    reports = []
    if game in {"pacman", "all"}:
        reports.append(plan_pacman())
    if game in {"tetris", "all"}:
        reports.append(plan_tetris())
    if game in {"world", "all"}:
        reports.append(simulate_world())
    if not reports:
        raise ValueError(f"unknown game: {game}")
    return {
        "schema": "scbe_mahss_game_gym_report_v1",
        "purpose": "closed-loop game mechanics for routing free/local LLMs through AetherDesk tools",
        "policy": {
            "model_role": "propose moves",
            "system_role": "score legal moves, enforce tools, write receipts",
            "no_model_calls": True,
        },
        "reports": reports,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", choices=["pacman", "tetris", "world", "all"], default="all")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    payload = build_report(args.game)
    text = json.dumps(payload, indent=2, ensure_ascii=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
