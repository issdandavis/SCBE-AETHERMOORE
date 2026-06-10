from __future__ import annotations

from src.tokenizer.semantic_code_bridge import (
    build_lexicon_cross_compile_bridge,
    build_semantic_code_bridge,
    semantic_atom_for_lattice_band,
    semantic_atom_for_operation,
)


def test_semantic_code_bridge_aligns_add_function_across_languages() -> None:
    bridge = build_semantic_code_bridge(
        {
            "python": "def add(a, b):\n    return a + b\n",
            "typescript": "function add(a, b) { return a + b; }\n",
            "rust": "fn add(a: i32, b: i32) -> i32 { return a + b }\n",
            "c": "int add(int a, int b) { return a + b; }\n",
        }
    )

    assert bridge["schema_version"] == "scbe-semantic-code-bridge-v1"
    assert bridge["aligned"] is True
    assert bridge["operation_paths"] == [["function_definition/2", "return_flow", "arithmetic:add/2"]]
    assert bridge["semantic_atoms"] == ["FLOW", "FLOW", "TRANSFORM"]
    assert bridge["workflow_edges"] == [
        {
            "from": "FLOW",
            "to": "FLOW",
            "channel": "dot_to_dot",
            "operation_from": "function_definition/2",
            "operation_to": "return_flow",
        },
        {
            "from": "FLOW",
            "to": "TRANSFORM",
            "channel": "pipe",
            "operation_from": "return_flow",
            "operation_to": "arithmetic:add/2",
        },
    ]
    assert len(set(bridge["interchange_keys"])) == 1
    for preservation in bridge["bijective_packet_preservation"].values():
        assert preservation["lexical_tokens_preserved"] is True
        assert preservation["identifier_names_preserved_in_atoms"] is True
        assert len(preservation["source_sha256"]) == 64
        assert len(preservation["transport_token_sha256"]) == 64


def test_semantic_code_bridge_surfaces_control_guard_as_block_and_merge_flow() -> None:
    bridge = build_semantic_code_bridge(
        {
            "python": "def guarded(x):\n    if x >= 0:\n        return x\n",
        }
    )

    assert bridge["aligned"] is True
    assert bridge["semantic_atoms"] == ["FLOW", "FLOW", "BLOCK", "BLOCK"]
    assert {edge["channel"] for edge in bridge["workflow_edges"]} >= {"bifurcation"}


def test_semantic_atom_for_operation_defaults_unknown_operations_to_transform() -> None:
    assert semantic_atom_for_operation("function_definition/2") == "FLOW"
    assert semantic_atom_for_operation("comparison:gte/2") == "BLOCK"
    assert semantic_atom_for_operation("custom_rewrite") == "TRANSFORM"


def test_lexicon_cross_compile_bridge_proves_bijective_ir_path() -> None:
    bridge = build_lexicon_cross_compile_bridge("(x + y)", "KO", "RU")

    assert bridge["schema_version"] == "scbe-semantic-lexicon-cross-compile-v1"
    assert bridge["aligned"] is True
    assert bridge["quarantined"] is False
    assert bridge["dst_code"] == "x.wrapping_add(y)"
    assert bridge["ir"]["op_name"] == "add"
    assert bridge["semantic_atoms"] == ["TRANSFORM"]
    assert [edge["channel"] for edge in bridge["workflow_edges"]] == ["bifurcation", "merge"]
    assert len(bridge["bridge_hash"]) == 64


def test_lexicon_cross_compile_bridge_quarantines_non_lexicon_source() -> None:
    bridge = build_lexicon_cross_compile_bridge("console.log(secret)", "AV", "KO")

    assert bridge["aligned"] is False
    assert bridge["quarantined"] is True
    assert bridge["error"] == "LiftFailure"
    assert "no lexicon op template matched" in bridge["message"]


def test_semantic_atom_for_lattice_band_maps_operation_bands() -> None:
    assert semantic_atom_for_lattice_band("ARITHMETIC") == "TRANSFORM"
    assert semantic_atom_for_lattice_band("COMPARISON") == "BLOCK"
    assert semantic_atom_for_lattice_band("LOGIC") == "BLOCK"
