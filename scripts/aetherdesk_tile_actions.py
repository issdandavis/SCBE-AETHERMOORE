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


ACTIONS = {
    "chemistry": chemistry_lookup,
    "forge": forge_demo,
    "instrument": instrument_play,
    "rosetta": rosetta_demo,
    "token": token_lookup,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fixed AetherDesk tile action")
    parser.add_argument("action", choices=sorted(ACTIONS))
    args = parser.parse_args()
    ACTIONS[args.action]()


if __name__ == "__main__":
    main()
