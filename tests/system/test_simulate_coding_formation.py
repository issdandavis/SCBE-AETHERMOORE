import json
from pathlib import Path

import pytest

from scripts.system.simulate_coding_formation import (
    FORMATIONS,
    choose_formation,
    infer_task_vector,
    packet_hash,
    simulate_formation,
)


def _task(**overrides):
    payload = {
        "schema_version": "scbe_bijective_coding_task_v1",
        "task_id": "test-geoseal-cli",
        "goal": "Add a GeoSeal CLI command and focused tests.",
        "formation": "scout-coder-verifier",
        "owned_paths": ["src/geoseal_cli.py", "tests/terminal/test_geoseal_layer_runner_cli.py"],
        "blocked_paths": ["training-data/", "artifacts/"],
        "required_signal": "formation-hop:scout->coder:bounded-edit",
        "success_gate": "python -m pytest tests/terminal/test_geoseal_layer_runner_cli.py -q",
        "receipt_required": True,
    }
    payload.update(overrides)
    return payload


def test_packet_hash_is_order_stable():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert packet_hash(left) == packet_hash(right)


def test_infer_task_vector_weights_code_and_tests():
    vector = infer_task_vector(_task())
    research, coding, verification, context = vector
    assert coding > research
    assert verification > research
    assert context > 0


def test_requested_formation_is_respected():
    task = _task(formation="firefighter-loop")
    vector = infer_task_vector(task)
    assert choose_formation(task, vector) == "firefighter-loop"


def test_bug_goal_selects_firefighter_when_no_requested_formation():
    task = _task(goal="Fix a crashing test in the GeoSeal CLI", formation="")
    vector = infer_task_vector(task)
    assert choose_formation(task, vector) == "firefighter-loop"


def test_simulation_emits_receipts_for_every_role():
    result = simulate_formation(_task())
    assert result["schema_version"] == "scbe_coding_formation_simulation_v1"
    assert result["formation_id"] == "scout-coder-verifier"
    assert result["roles"] == FORMATIONS["scout-coder-verifier"]
    assert len(result["receipts"]) == len(result["roles"])
    assert all(receipt["schema_version"] == "scbe_formation_role_receipt_v1" for receipt in result["receipts"])
    assert all(receipt["input_packet_sha256"] for receipt in result["receipts"])
    assert all(receipt["output_packet_sha256"] for receipt in result["receipts"])


def test_table_game_records_legal_shared_board_without_private_hands():
    result = simulate_formation(_task())
    table = result["table_game"]
    assert table["schema_version"] == "scbe_formation_table_game_v1"
    assert table["game_mode"] == "deterministic_non_greedy_cooperative"
    assert "shared task board" in table["objective"]
    assert table["deck_schema_version"] == "scbe_coding_deck_manifest_v1"
    assert table["deck_grounded_minimum_cards"] == 899
    assert "private" in table["rules"].lower()
    assert table["final_total"] <= table["target_total"]
    assert table["board_verdict"] == "pass"
    assert len(table["plays"]) == len(result["roles"])
    assert all(play["legal"] for play in table["plays"])
    assert all("card" in play for play in table["plays"])
    assert all(play["deck_card_id"] for play in table["plays"])
    assert all(play["deck_card_type"] for play in table["plays"])
    assert all("hand" not in play for play in table["plays"])


def test_receipts_include_board_state():
    result = simulate_formation(_task())
    for receipt in result["receipts"]:
        assert isinstance(receipt["board_total_after"], int)
        assert receipt["board_lane"]
        assert receipt["card_played"]
        assert receipt["deck_card_id"]
        assert receipt["deck_card_type"]
        assert 0.0 <= receipt["cooperative_score"] <= 1.0


def test_role_deck_draws_match_expected_groups():
    result = simulate_formation(_task())
    plays = result["table_game"]["plays"]
    assert [play["deck_group"] for play in plays] == [
        "pairings",
        "language_views",
        "stib",
        "operations",
    ]


def test_table_game_is_non_greedy_cooperative():
    result = simulate_formation(_task())
    table = result["table_game"]
    assert table["game_mode"] == "deterministic_non_greedy_cooperative"
    assert "do not maximize isolated role score" in table["objective"]
    assert all(receipt["cooperative_score"] > 0 for receipt in result["receipts"])


def test_missing_task_id_fails():
    with pytest.raises(ValueError, match="task_id"):
        simulate_formation(_task(task_id=""))


def test_cli_writes_output(tmp_path):
    task_path = tmp_path / "task.json"
    out_path = tmp_path / "result.json"
    task_path.write_text(json.dumps(_task()), encoding="utf-8")

    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/simulate_coding_formation.py",
            "--task",
            str(task_path),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["formation_id"] == "scout-coder-verifier"
