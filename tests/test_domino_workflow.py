from __future__ import annotations

import json
import subprocess
import sys

from src.coding_spine.domino_workflow import build_domino_workflow_from_specs, parse_tile

import pytest

pytestmark = pytest.mark.slow


def test_parse_tile_supports_named_contract_and_dots():
    tile = parse_tile("gather:intent|evidence:1/5")

    assert tile.tile_id == "gather"
    assert tile.left == "intent"
    assert tile.right == "evidence"
    assert tile.left_dots == 1
    assert tile.right_dots == 5


def test_domino_workflow_auto_arranges_and_transfers_contact_dots():
    payload = build_domino_workflow_from_specs(
        [
            "build:patch|test:4/6",
            "gather:intent|evidence:1/5",
            "plan:evidence|patch:1/4",
            "ship:test|verified:0/6",
        ],
        start="intent",
    )

    assert payload["schema"] == "scbe_domino_workflow_v1"
    assert [tile["tile_id"] for tile in payload["chain"]] == ["gather", "plan", "build", "ship"]
    assert payload["summary"]["complete"] is True
    assert payload["contacts"][0]["contract"] == "evidence"
    assert payload["contacts"][0]["transfer_amount"] == 2
    assert payload["mechanics"]["dot_transfer"] == "balanced_contact_faces"


def test_domino_workflow_rotates_tiles_when_contact_requires_it():
    payload = build_domino_workflow_from_specs(
        [
            "a:intent|evidence",
            "b:patch|evidence",
        ],
        start="intent",
    )

    assert [tile["tile_id"] for tile in payload["chain"]] == ["a", "b"]
    assert payload["chain"][1]["rotated"] is True
    assert payload["chain"][1]["left"] == "evidence"


def test_geoseal_domino_cli_outputs_json():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "domino",
            "gather:intent|evidence:1/5",
            "plan:evidence|patch:1/4",
            "--start",
            "intent",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout)

    assert proc.returncode == 0, proc.stderr
    assert payload["summary"]["complete"] is True
    assert payload["contacts"][0]["contract"] == "evidence"
