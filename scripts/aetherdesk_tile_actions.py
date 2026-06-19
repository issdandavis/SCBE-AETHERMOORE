"""Allowlisted AetherDesk tile actions.

These fixed, no-argument actions let the local browser shell launch useful SCBE
surfaces without accepting arbitrary shell strings from the UI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def chemistry_lookup() -> None:
    from python.scbe.chemistry_dimensions import analyze_formula

    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "chemistry_lookup",
            "label": "Chemistry Lookup",
            "result": analyze_formula("C6H12O6"),
        }
    )


def token_lookup() -> None:
    from python.scbe.token_lookup import lookup_tokens

    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "token_lookup",
            "label": "Token Lookup",
            "result": lookup_tokens(["build", "H2O", "verify"]),
        }
    )


def instrument_play() -> None:
    from python.scbe.instrument import play

    result = play("C E", face="python", args=(10, 3, 2))
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "instrument_play",
            "label": "Instrument",
            "song": result["song"],
            "ops": result["ops"],
            "value": result["value"],
            "song_back": result["song_back"],
            "bijective": result["bijective"],
            "melody": result.get("melody", []),
        }
    )


def forge_demo() -> None:
    from python.helm.tool_forge_demo import render_tool_forge_demo, run_tool_forge_demo

    result = run_tool_forge_demo()
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "forge_demo",
            "label": "Forge Demo",
            "summary": render_tool_forge_demo(result),
            "result": result,
        }
    )


def rosetta_demo() -> None:
    from python.scbe.rosetta import rosetta

    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "rosetta_demo",
            "label": "Rosetta",
            "result": rosetta("C E", cases=[(10, 3, 2)]),
        }
    )


def curriculum_demo() -> None:
    from python.helm.curriculum import run_curriculum

    s = run_curriculum()  # answer-key climber: validates the ladder is solvable
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "curriculum",
            "label": "Coding Ladder",
            "highest_tier_cleared": s["highest_tier_cleared"],
            "highest_grade": s["highest_grade_cleared"],
            "total_verified": s["total_verified"],
            "total": s["total_problems"],
        }
    )


def reasoning_demo() -> None:
    from python.helm.reasoning_ladder import run_reasoning

    s = run_reasoning()  # answer-key climber: validates the grader
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "reasoning",
            "label": "Reasoning Ladder",
            "highest_tier_cleared": s["highest_tier_cleared"],
            "highest_grade": s["highest_grade_cleared"],
            "total_passed": s["total_passed"],
            "total": s["total"],
        }
    )


def stepwise_demo() -> None:
    from python.scbe.stepwise import number_label_task, run_stepwise, scripted_proposer

    r = run_stepwise(number_label_task(6), scripted_proposer(["Buzz", "Fizz"]))  # missteps then rewinds to ok
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "stepwise",
            "label": "Stepwise (rewind on misstep)",
            "completed": r["completed"],
            "answer": r.get("answer"),
            "rewinds": r["rewinds"],
            "model_calls": r["model_calls"],
        }
    )


def failuremap_demo() -> None:
    from python.scbe.failure_map import clears_through, render_map, run_map, seq_task

    tasks = [seq_task("alpha", ["a1", "a2", "a3"]), seq_task("beta", ["b1", "b2"])]
    m = run_map(tasks, {"strong": clears_through(9), "mid": clears_through(2), "weak": clears_through(0)})
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "failuremap",
            "label": "Failure Map",
            "universal_fail": m["universal_fail"],
            "walls": {t: m["per_task"][t]["wall"] for t in m["tasks"]},
            "report": render_map(m),  # cells use tuple keys; the rendered text is the serializable view
        }
    )


def host_check() -> None:
    from python.helm.host_capability import certify, render

    c = certify(probe_network=True)
    emit(
        {
            "schema": "aetherdesk_tile_action_v1",
            "tile": "hostcheck",
            "label": "Host Capability",
            "verdict": c["verdict"],
            "runnable": c["runnable"],
            "report": render(c),
        }
    )


ACTIONS = {
    "chemistry": chemistry_lookup,
    "curriculum": curriculum_demo,
    "failuremap": failuremap_demo,
    "forge": forge_demo,
    "hostcheck": host_check,
    "instrument": instrument_play,
    "reasoning": reasoning_demo,
    "rosetta": rosetta_demo,
    "stepwise": stepwise_demo,
    "token": token_lookup,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fixed AetherDesk tile action")
    parser.add_argument("action", choices=sorted(ACTIONS))
    args = parser.parse_args()
    ACTIONS[args.action]()


if __name__ == "__main__":
    main()
