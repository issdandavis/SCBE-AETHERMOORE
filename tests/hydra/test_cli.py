from __future__ import annotations

from hydra.cli import (
    _load_json_object,
    _parse_lattice25d_options,
    _normalize_command,
    _parse_branch_options,
    _resolve_command_and_args,
)


def test_normalize_command_aliases():
    assert _normalize_command("st") == "status"
    assert _normalize_command("WF") == "workflow"
    assert _normalize_command("br") == "branch"
    assert _normalize_command("switchboard") == "switchboard"


def test_resolve_command_defaults_to_execute_with_stdin_payload():
    command, args, raw = _resolve_command_and_args(None, [], '{"action":"status"}')
    assert command == "execute"
    assert args == ['{"action":"status"}']
    assert raw == "execute"


def test_resolve_command_prefers_explicit_command():
    command, args, raw = _resolve_command_and_args("status", ["x"], '{"action":"status"}')
    assert command == "status"
    assert args == ["x"]
    assert raw == "status"


def test_resolve_execute_uses_stdin_when_missing_payload():
    command, args, raw = _resolve_command_and_args("execute", [], '{"action":"status"}')
    assert command == "execute"
    assert args == ['{"action":"status"}']
    assert raw == "execute"


def test_load_json_object_accepts_object():
    payload = _load_json_object('{"action":"status"}', "execute command")
    assert payload == {"action": "status"}


def test_load_json_object_rejects_invalid_json():
    payload = _load_json_object("{not-json", "execute command")
    assert payload is None


def test_load_json_object_rejects_non_object():
    payload = _load_json_object('["a", "b"]', "execute command")
    assert payload is None


def test_parse_branch_options_accepts_context_and_exports():
    options = _parse_branch_options(
        [
            "--topic",
            "swarm nav",
            "--strategy",
            "scored",
            "--max-paths",
            "7",
            "--max-depth",
            "11",
            "--providers",
            "claude,gpt",
            "--context",
            '{"domain":"uav"}',
            "--export-n8n",
            "out/workflow.json",
            "--export-choicescript",
            "out/workflow.txt",
        ],
        "claude,gpt,gemini",
    )
    assert options is not None
    assert options["topic"] == "swarm nav"
    assert options["strategy"] == "scored"
    assert options["max_paths"] == 7
    assert options["max_depth"] == 11
    assert options["providers"] == ["claude", "gpt"]
    assert options["context"] == {"domain": "uav"}
    assert options["export_n8n_path"] == "out/workflow.json"
    assert options["export_choicescript_path"] == "out/workflow.txt"


def test_parse_lattice25d_options_accepts_query_and_glob():
    options = _parse_lattice25d_options(
        [
            "--glob",
            "docs/**/*.md",
            "--max-notes",
            "25",
            "--cell-size",
            "0.5",
            "--query-intent",
            "0.7,0.2,0.1",
            "--query-top-k",
            "3",
        ]
    )
    assert options is not None
    assert options["glob"] == "docs/**/*.md"
    assert options["max_notes"] == 25
    assert options["cell_size"] == 0.5
    assert options["query_intent"] == [0.7, 0.2, 0.1]
    assert options["query_top_k"] == 3


def test_parse_lattice25d_options_accepts_quadtree_params():
    options = _parse_lattice25d_options(
        [
            "--index",
            "quadtree",
            "--qt-capacity",
            "12",
            "--qt-z-var",
            "0.04",
            "--qt-extent",
            "0.5",
        ]
    )
    assert options is not None
    assert options["index_mode"] == "quadtree"
    assert options["qt_capacity"] == 12
    assert options["qt_z_variance"] == 0.04
    assert options["qt_extent"] == 0.5
