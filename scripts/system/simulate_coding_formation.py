#!/usr/bin/env python3
"""Deterministic mock run for bijective coding-agent formations.

This is a pure local simulator. It does not call AI models or edit project
files. It ingests a small task packet, chooses a formation path, computes
simple role-fit and handoff-cost scores, and emits replayable receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "formation_simulations"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.build_coding_decks import build_manifest

FORMATION_ROLES = {
    "researcher": {
        "vector": [0.95, 0.25, 0.10, 0.20],
        "tools": ["read", "search"],
        "ring": "outer",
    },
    "scout": {
        "vector": [0.85, 0.45, 0.20, 0.35],
        "tools": ["read", "grep"],
        "ring": "outer",
    },
    "coder": {
        "vector": [0.30, 0.95, 0.40, 0.35],
        "tools": ["read", "write_workspace"],
        "ring": "outer",
    },
    "firefighter": {
        "vector": [0.35, 0.85, 0.95, 0.55],
        "tools": ["read", "write_workspace", "execute_tests"],
        "ring": "outer",
    },
    "file_manager": {
        "vector": [0.45, 0.35, 0.30, 0.90],
        "tools": ["read", "write_workspace"],
        "ring": "outer",
    },
    "context_roller": {
        "vector": [0.70, 0.30, 0.45, 0.95],
        "tools": ["read", "write_context"],
        "ring": "outer",
    },
    "verifier": {
        "vector": [0.40, 0.35, 0.90, 0.80],
        "tools": ["read", "execute_tests"],
        "ring": "inner",
    },
    "integrator": {
        "vector": [0.55, 0.75, 0.75, 0.85],
        "tools": ["read", "write_workspace", "execute_tests"],
        "ring": "inner",
    },
    "planner": {
        "vector": [0.85, 0.45, 0.65, 0.70],
        "tools": ["read"],
        "ring": "inner",
    },
}

FORMATIONS = {
    "scout-coder-verifier": ["scout", "coder", "verifier", "integrator"],
    "researcher-scout-coder-verifier": ["researcher", "scout", "coder", "verifier", "integrator"],
    "firefighter-loop": ["verifier", "firefighter", "verifier", "integrator"],
    "file-manager-cleanup": ["file_manager", "verifier", "integrator"],
    "long-session-coding": [
        "context_roller",
        "researcher",
        "scout",
        "coder",
        "verifier",
        "integrator",
        "context_roller",
    ],
}

ROLE_CARD_PLAY = {
    "researcher": {"card": "source-map", "value": 2, "board_lane": "evidence"},
    "scout": {"card": "path-scan", "value": 2, "board_lane": "plan"},
    "coder": {"card": "bounded-patch", "value": 3, "board_lane": "implementation"},
    "firefighter": {"card": "regression-fix", "value": 4, "board_lane": "repair"},
    "file_manager": {"card": "clean-board", "value": 2, "board_lane": "cleanup"},
    "context_roller": {"card": "rolling-context", "value": 1, "board_lane": "continuity"},
    "verifier": {"card": "gate-check", "value": 3, "board_lane": "verification"},
    "integrator": {"card": "merge-receipt", "value": 3, "board_lane": "integration"},
    "planner": {"card": "intent-split", "value": 2, "board_lane": "plan"},
}

ROLE_DECK_GROUP = {
    "researcher": "pairings",
    "scout": "pairings",
    "coder": "language_views",
    "firefighter": "language_views",
    "file_manager": "stib",
    "context_roller": "binary",
    "verifier": "stib",
    "integrator": "operations",
    "planner": "pairings",
}

DM_TRIBUNAL = {
    "rules_dm": {
        "focus": "legality",
        "prompt": "Keep the move inside owned paths, declared tools, and visible board rules.",
    },
    "math_dm": {
        "focus": "score",
        "prompt": "Choose the move that improves shared board progress and handoff efficiency.",
    },
    "lore_dm": {
        "focus": "continuity",
        "prompt": "Preserve task intent, role identity, and compact context continuity.",
    },
}

KEYWORD_WEIGHTS = {
    "research": [0.9, 0.1, 0.2, 0.2],
    "docs": [0.7, 0.1, 0.2, 0.6],
    "test": [0.2, 0.3, 0.95, 0.4],
    "tests": [0.2, 0.3, 0.95, 0.4],
    "bug": [0.2, 0.6, 0.95, 0.3],
    "crash": [0.2, 0.5, 0.95, 0.3],
    "fix": [0.3, 0.7, 0.8, 0.4],
    "code": [0.2, 0.95, 0.4, 0.3],
    "cli": [0.2, 0.85, 0.45, 0.35],
    "geoseal": [0.4, 0.75, 0.55, 0.45],
    "release": [0.3, 0.3, 0.65, 0.95],
    "cleanup": [0.3, 0.25, 0.45, 0.95],
    "context": [0.65, 0.25, 0.45, 0.95],
    "long": [0.45, 0.25, 0.35, 0.95],
}


@dataclass(frozen=True)
class Receipt:
    schema_version: str
    task_id: str
    formation_id: str
    role: str
    step_index: int
    role_fit: float
    handoff_cost: float
    input_packet_sha256: str
    output_packet_sha256: str
    handoff_signal: str
    board_total_after: int
    board_lane: str
    card_played: str
    deck_card_id: str
    deck_card_type: str
    cooperative_score: float
    tribunal_action: str
    subprompt_sha256: str
    verdict: str


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def packet_hash(packet: dict[str, Any]) -> str:
    return sha256_text(_canonical_json(packet))


def _norm(vector: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vector))


def _cosine(a: list[float], b: list[float]) -> float:
    denom = _norm(a) * _norm(b)
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / denom


def _add(a: list[float], b: list[float]) -> list[float]:
    return [x + y for x, y in zip(a, b)]


def infer_task_vector(task: dict[str, Any]) -> list[float]:
    """Return [research, coding, verification, context_or_file_ops]."""
    text = " ".join(
        str(task.get(key, ""))
        for key in ("goal", "task_id", "formation", "success_gate", "required_signal")
    ).lower()
    for path in task.get("owned_paths", []) + task.get("blocked_paths", []):
        text += " " + str(path).lower()

    vector = [0.1, 0.1, 0.1, 0.1]
    for word, weights in KEYWORD_WEIGHTS.items():
        if word in text:
            vector = _add(vector, weights)
    return [round(v, 6) for v in vector]


def choose_formation(task: dict[str, Any], task_vector: list[float]) -> str:
    requested = str(task.get("formation", "")).strip()
    if requested in FORMATIONS:
        return requested

    goal = str(task.get("goal", "")).lower()
    if any(word in goal for word in ("bug", "crash", "failing", "failure", "fix tests")):
        return "firefighter-loop"
    if any(word in goal for word in ("cleanup", "release", "sort repo", "file")):
        return "file-manager-cleanup"
    if any(word in goal for word in ("long", "multi-hour", "context", "compaction")):
        return "long-session-coding"
    if task_vector[0] > task_vector[1] + 0.4:
        return "researcher-scout-coder-verifier"
    return "scout-coder-verifier"


def _transition_cost(prev_role: str | None, role: str) -> float:
    if prev_role is None:
        return 0.0
    prev = FORMATION_ROLES[prev_role]["vector"]
    curr = FORMATION_ROLES[role]["vector"]
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev, curr)))
    ring_penalty = 0.15 if FORMATION_ROLES[prev_role]["ring"] != FORMATION_ROLES[role]["ring"] else 0.0
    return round(distance + ring_penalty, 6)


def _target_board_total(task_vector: list[float], role_count: int) -> int:
    """Pazaak-style target: simple, deterministic, and bounded.

    The agent's private reasoning/cards are intentionally hidden. The simulator
    only records legal plays on the shared board.
    """
    pressure = sum(task_vector)
    return max(9, min(21, int(round(pressure * 2.5)) + role_count))


def _play_card(role: str, board_total: int, target_total: int) -> dict[str, Any]:
    card = ROLE_CARD_PLAY[role]
    value = int(card["value"])
    if board_total + value > target_total:
        # Legal dampener card: preserve the lane but avoid overshooting the board.
        value = -1 if board_total > 0 else 0
    return {
        "role": role,
        "card": card["card"],
        "value": value,
        "board_lane": card["board_lane"],
        "board_total_before": board_total,
        "board_total_after": board_total + value,
        "target_total": target_total,
        "legal": 0 <= board_total + value <= target_total,
    }


def _select_deck_card(deck: dict[str, Any], task: dict[str, Any], role: str, index: int) -> dict[str, Any]:
    """Select one visible substrate card for the role's move.

    The role's private hand is still hidden. This picks the public card that
    explains which coding substrate the role touched: operation, language
    projection, binary byte, STIB field, or pair route.
    """
    group_name = ROLE_DECK_GROUP[role]
    group = deck["cards"][group_name]
    seed = int(packet_hash({"task": task, "role": role, "index": index, "group": group_name})[:12], 16)
    card = group[seed % len(group)]
    return {
        "deck_group": group_name,
        "card_id": card["card_id"],
        "card_type": card["card_type"],
    }


def _cooperative_score(play: dict[str, Any], role_fit: float, handoff_cost: float) -> float:
    """Reward shared board progress instead of greedy individual gain."""
    target = max(1, int(play["target_total"]))
    after = int(play["board_total_after"])
    closeness = 1.0 - (abs(target - after) / target)
    handoff_efficiency = max(0.0, 1.0 - (handoff_cost / 2.0))
    legal_bonus = 0.15 if play["legal"] else -0.35
    score = (0.45 * closeness) + (0.35 * role_fit) + (0.20 * handoff_efficiency) + legal_bonus
    return round(max(0.0, min(1.0, score)), 6)


def _tenreary_roll(task: dict[str, Any], role: str, index: int, channel: str) -> list[int]:
    digest = packet_hash({"task": task, "role": role, "index": index, "channel": channel})
    return [int(char, 16) % 10 for char in digest[:6]]


def _tribunal_guidance(
    task: dict[str, Any],
    role: str,
    index: int,
    play: dict[str, Any],
    deck_play: dict[str, Any],
    cooperative_score: float,
) -> dict[str, Any]:
    dms: list[dict[str, Any]] = []
    roll_total = 0
    for dm_id, dm in DM_TRIBUNAL.items():
        roll = _tenreary_roll(task, role, index, dm_id)
        score = sum(roll)
        roll_total += score
        dms.append(
            {
                "dm_id": dm_id,
                "focus": dm["focus"],
                "tenreary_roll": roll,
                "roll_score": score,
                "guidance": dm["prompt"],
            }
        )

    if not play["legal"]:
        action = "repair_illegal_move"
    elif cooperative_score >= 0.80:
        action = "advance"
    elif roll_total >= 90:
        action = "press_advantage"
    elif role in {"verifier", "integrator"}:
        action = "tighten_gate"
    else:
        action = "request_evidence"

    subprompt = {
        "schema_version": "scbe_dm_subprompt_v1",
        "role": role,
        "step_index": index,
        "action": action,
        "board_lane": play["board_lane"],
        "workflow_card": play["card"],
        "deck_card_id": deck_play["card_id"],
        "instruction": (
            f"{role}: {action}. Use {play['card']} on {play['board_lane']} with "
            f"{deck_play['card_id']}. Return one compact receipt; do not expose private hand."
        ),
    }
    return {
        "schema_version": "scbe_dm_tribunal_guidance_v1",
        "tribunal_id": "coding-table-dm-tribunal",
        "role": role,
        "step_index": index,
        "dms": dms,
        "roll_total": roll_total,
        "action": action,
        "subprompt": subprompt,
        "subprompt_sha256": packet_hash(subprompt),
    }


def simulate_formation(task: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(task, dict):
        raise ValueError("Task packet must be a JSON object.")
    task_id = str(task.get("task_id", "")).strip()
    if not task_id:
        raise ValueError("Task packet requires task_id.")
    goal = str(task.get("goal", "")).strip()
    if not goal:
        raise ValueError("Task packet requires goal.")

    source_packet_hash = packet_hash(task)
    task_vector = infer_task_vector(task)
    formation_id = choose_formation(task, task_vector)
    roles = FORMATIONS[formation_id]
    deck = build_manifest()
    target_total = _target_board_total(task_vector, len(roles))
    board_total = 0
    board_plays: list[dict[str, Any]] = []

    receipts: list[Receipt] = []
    current_packet = dict(task)
    current_packet["packet_sha256"] = source_packet_hash
    prev_role: str | None = None
    total_fit = 0.0
    total_cost = 0.0

    for index, role in enumerate(roles):
        play = _play_card(role, board_total, target_total)
        deck_play = _select_deck_card(deck, task, role, index)
        play["deck_card_id"] = deck_play["card_id"]
        play["deck_card_type"] = deck_play["card_type"]
        play["deck_group"] = deck_play["deck_group"]
        board_total = int(play["board_total_after"])
        board_plays.append(play)
        input_hash = packet_hash(current_packet)
        role_vector = FORMATION_ROLES[role]["vector"]
        role_fit = round(_cosine(task_vector, role_vector), 6)
        handoff_cost = _transition_cost(prev_role, role)
        cooperative_score = _cooperative_score(play, role_fit, handoff_cost)
        tribunal = _tribunal_guidance(task, role, index, play, deck_play, cooperative_score)
        play["tribunal_action"] = tribunal["action"]
        play["subprompt_sha256"] = tribunal["subprompt_sha256"]
        total_fit += role_fit
        total_cost += handoff_cost
        verdict = "pass" if role_fit >= 0.45 else "review"
        next_packet = {
            "task_id": task_id,
            "formation_id": formation_id,
            "role": role,
            "step_index": index,
            "previous_packet_sha256": input_hash,
            "role_fit": role_fit,
            "handoff_cost": handoff_cost,
            "cooperative_score": cooperative_score,
            "tribunal_guidance": tribunal,
            "board_play": play,
            "deck_card": deck_play,
            "allowed_tools": FORMATION_ROLES[role]["tools"],
            "verdict": verdict,
        }
        output_hash = packet_hash(next_packet)
        signal_to = roles[index + 1] if index + 1 < len(roles) else "complete"
        receipts.append(
            Receipt(
                schema_version="scbe_formation_role_receipt_v1",
                task_id=task_id,
                formation_id=formation_id,
                role=role,
                step_index=index,
                role_fit=role_fit,
                handoff_cost=handoff_cost,
                input_packet_sha256=input_hash,
                output_packet_sha256=output_hash,
                handoff_signal=f"formation-hop:{role}->{signal_to}:simulated",
                board_total_after=board_total,
                board_lane=str(play["board_lane"]),
                card_played=str(play["card"]),
                deck_card_id=str(deck_play["card_id"]),
                deck_card_type=str(deck_play["card_type"]),
                cooperative_score=cooperative_score,
                tribunal_action=str(tribunal["action"]),
                subprompt_sha256=str(tribunal["subprompt_sha256"]),
                verdict=verdict,
            )
        )
        current_packet["tribunal_guidance"] = tribunal
        current_packet = next_packet
        prev_role = role

    average_fit = round(total_fit / len(receipts), 6)
    total_handoff_cost = round(total_cost, 6)
    pass_count = sum(1 for r in receipts if r.verdict == "pass")
    final_verdict = "pass" if pass_count == len(receipts) and average_fit >= 0.65 else "review"
    board_verdict = "pass" if board_total <= target_total and all(play["legal"] for play in board_plays) else "review"
    if board_verdict != "pass":
        final_verdict = "review"
    receipt_payload = [r.__dict__ for r in receipts]
    run_id = sha256_text(_canonical_json({"task": task, "receipts": receipt_payload}))[:16]

    return {
        "schema_version": "scbe_coding_formation_simulation_v1",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task_packet_sha256": source_packet_hash,
        "task_vector": task_vector,
        "formation_id": formation_id,
        "roles": roles,
        "table_game": {
            "schema_version": "scbe_formation_table_game_v1",
            "rules": "Role hands stay private; only legal board plays and receipts are recorded.",
            "game_mode": "deterministic_non_greedy_cooperative",
            "objective": "Advance the shared task board with legal, low-cost handoffs; do not maximize isolated role score.",
            "deck_schema_version": deck["schema_version"],
            "deck_grounded_minimum_cards": deck["counts"]["current_grounded_minimum_cards"],
            "tribunal": {
                "schema_version": "scbe_dm_tribunal_v1",
                "mode": "deterministic_ai_dm_overseer",
                "dm_count": len(DM_TRIBUNAL),
                "dm_ids": list(DM_TRIBUNAL),
                "decision_rule": "Tenreary rolls guide compact sub-prompts; final action remains bounded by legal board moves.",
            },
            "target_total": target_total,
            "final_total": board_total,
            "board_verdict": board_verdict,
            "plays": board_plays,
        },
        "metrics": {
            "average_role_fit": average_fit,
            "total_handoff_cost": total_handoff_cost,
            "pass_count": pass_count,
            "role_count": len(receipts),
        },
        "final_verdict": final_verdict,
        "receipts": receipt_payload,
    }


def _example_task() -> dict[str, Any]:
    return {
        "schema_version": "scbe_bijective_coding_task_v1",
        "task_id": "mock-geoseal-layer-registry-cli",
        "goal": "Add a GeoSeal CLI command and focused tests for the layer runner registry.",
        "formation": "scout-coder-verifier",
        "owned_paths": [
            "src/geoseal_cli.py",
            "tests/terminal/test_geoseal_layer_runner_cli.py",
        ],
        "blocked_paths": ["training-data/", "artifacts/"],
        "required_signal": "formation-hop:scout->coder:bounded-edit",
        "success_gate": "python -m pytest tests/terminal/test_geoseal_layer_runner_cli.py -q",
        "receipt_required": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", help="Path to task packet JSON. If omitted, uses a built-in example.")
    parser.add_argument("--out", help="Output JSON path. Defaults to artifacts/formation_simulations/<run_id>.json")
    parser.add_argument("--json", action="store_true", help="Print the full simulation JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.task:
        task_path = Path(args.task).expanduser().resolve()
        task = json.loads(task_path.read_text(encoding="utf-8"))
    else:
        task = _example_task()

    result = simulate_formation(task)
    out_path = Path(args.out).expanduser().resolve() if args.out else DEFAULT_OUTPUT_ROOT / f"{result['run_id']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            json.dumps(
                {
                    "run_id": result["run_id"],
                    "formation_id": result["formation_id"],
                    "roles": result["roles"],
                    "metrics": result["metrics"],
                    "final_verdict": result["final_verdict"],
                    "output_path": str(out_path),
                },
                indent=2,
                ensure_ascii=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
