#!/usr/bin/env python3
"""Analog action primitives for terminal-side AI harness workflows.

Terminus is useful here because it makes command effects concrete: observe,
move, inspect, solve, checkpoint. This module keeps that pattern without
depending on the web game runtime. The deck is small on purpose so agents can
learn stable action dominoes and then compose them into larger workflows.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AnalogAction:
    action_id: str
    symbol: str
    command_shape: str
    intent: str
    precondition: str
    expected_effect: str
    evidence: str
    reset_scope: str
    multi_encoding: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_default_action_deck() -> list[AnalogAction]:
    return [
        AnalogAction(
            action_id="observe-room",
            symbol="O",
            command_shape="ls",
            intent="survey available exits, items, enemies, or provider lanes",
            precondition="current context exists",
            expected_effect="state stays stable; visible affordances are listed",
            evidence="locations/items/models/pairs appear in output",
            reset_scope="read_only",
            multi_encoding={"terminal": "ls", "training": "observe", "tongue": "KO", "ui": "refresh"},
        ),
        AnalogAction(
            action_id="move-lane",
            symbol="M",
            command_shape="cd <target> | lane-change:<from>-><to>:<reason>",
            intent="move between rooms, providers, phases, or permission lanes",
            precondition="target is advertised by observe-room and lane signal is present when crossing providers",
            expected_effect="active frame changes; route cost is recorded",
            evidence="new room/provider/phase is acknowledged",
            reset_scope="session",
            multi_encoding={"terminal": "cd", "training": "route", "tongue": "AV", "ui": "select"},
        ),
        AnalogAction(
            action_id="inspect-object",
            symbol="I",
            command_shape="less <item>",
            intent="read object contract, enemy givens, packet fields, or model adapter notes",
            precondition="object was visible in observe-room output",
            expected_effect="details are exposed without mutation",
            evidence="problem, contract, schema, or adapter note appears",
            reset_scope="read_only",
            multi_encoding={"terminal": "less", "training": "inspect", "tongue": "UM", "ui": "details"},
        ),
        AnalogAction(
            action_id="solve-checkpoint",
            symbol="S",
            command_shape="solve <target> <answer> | packet-graph-run --intent <goal>",
            intent="commit a candidate answer or packet path at a checkpoint",
            precondition="givens inspected and expected output is known",
            expected_effect="verdict/checkpoint is produced; score or merge report updates",
            evidence="defeated/pass/promote/hold verdict is emitted",
            reset_scope="run",
            multi_encoding={"terminal": "solve", "training": "commit", "tongue": "CA", "ui": "run"},
        ),
        AnalogAction(
            action_id="verify-evidence",
            symbol="V",
            command_shape="verify <seal> | score_packet_trace_sft.py --json",
            intent="validate that the recorded path matches expected state and integrity constraints",
            precondition="a checkpoint, seal, trace, or merge report exists",
            expected_effect="pass/fail evidence is generated",
            evidence="hash, seal, test, or score gate passes",
            reset_scope="read_only",
            multi_encoding={"terminal": "verify", "training": "validate", "tongue": "RU", "ui": "check"},
        ),
        AnalogAction(
            action_id="reset-run",
            symbol="R",
            command_shape="reset | new-session | rerun scripted path",
            intent="clear transient state and replay the action domino chain",
            precondition="workflow has terminal state or operator requests a clean slate",
            expected_effect="same initial state is restored for deterministic replay",
            evidence="new session id or clean benchmark artifact appears",
            reset_scope="global",
            multi_encoding={"terminal": "reset", "training": "replay", "tongue": "DR", "ui": "restart"},
        ),
    ]


def build_domino_workflow(*, goal: str, provider_pair: list[str] | None = None) -> dict[str, Any]:
    pair = provider_pair or []
    lane_signal = ""
    if len(pair) >= 2:
        left = pair[0].split(":", 1)[0]
        right = pair[1].split(":", 1)[0]
        if left != right:
            lane_signal = f"provider-pair:{left}->{right}:workflow"
    deck = build_default_action_deck()
    steps = [
        {"step": 1, "action_id": "observe-room", "command": "harness-terminal --no-health"},
        {"step": 2, "action_id": "inspect-object", "command": "inspect selected provider lanes"},
        {
            "step": 3,
            "action_id": "move-lane",
            "command": lane_signal or "same-lane",
        },
        {"step": 4, "action_id": "solve-checkpoint", "command": f"packet-graph-run --intent {json.dumps(goal)}"},
        {"step": 5, "action_id": "verify-evidence", "command": "score_packet_trace_sft.py --json"},
        {"step": 6, "action_id": "reset-run", "command": "rerun from clean checkpoint if verification fails"},
    ]
    return {
        "schema_version": "scbe_analog_domino_workflow_v1",
        "goal": goal,
        "provider_pair": pair,
        "lane_signal": lane_signal,
        "deck": [action.to_dict() for action in deck],
        "steps": steps,
        "rule": "Each domino must expose evidence before the next domino is allowed to fall.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", default="Run a governed AI-to-AI coding workflow")
    parser.add_argument("--provider-pair", default="", help="Comma-separated provider:model pair")
    parser.add_argument("--deck-only", action="store_true")
    args = parser.parse_args(argv)
    pair = [item.strip() for item in args.provider_pair.split(",") if item.strip()]
    payload: Any
    if args.deck_only:
        payload = {"schema_version": "scbe_analog_action_deck_v1", "deck": [a.to_dict() for a in build_default_action_deck()]}
    else:
        payload = build_domino_workflow(goal=args.goal, provider_pair=pair)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
