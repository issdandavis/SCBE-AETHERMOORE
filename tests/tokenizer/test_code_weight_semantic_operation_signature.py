from __future__ import annotations

from src.tokenizer.code_weight_packets import build_code_weight_packet


def _signature(source: str, language: str) -> dict:
    packet = build_code_weight_packet(source, language=language, source_name=f"sample.{language}")
    return packet["semantic_operation_signature"]


def test_semantic_operation_signature_matches_add_function_across_languages() -> None:
    samples = {
        "python": "def add(a, b):\n    return a + b\n",
        "typescript": "function add(a, b) { return a + b; }\n",
        "rust": "fn add(a: i32, b: i32) -> i32 { return a + b }\n",
        "c": "int add(int a, int b) { return a + b; }\n",
    }

    signatures = {language: _signature(source, language) for language, source in samples.items()}
    keys = {signature["interchange_key"] for signature in signatures.values()}
    paths = {tuple(signature["operation_path"]) for signature in signatures.values()}

    assert len(keys) == 1
    assert paths == {("function_definition/2", "return_flow", "arithmetic:add/2")}
    for language, signature in signatures.items():
        assert signature["source_language"] == language
        assert signature["preservation"]["language_specific_syntax_excluded_from_interchange_key"] is True
        assert signature["preservation"]["identifier_names_preserved_in_atoms"] is True


def test_semantic_operation_signature_preserves_identifiers_without_polluting_interchange_key() -> None:
    first = _signature("def add(left, right):\n    return left + right\n", "python")
    second = _signature("def sum_values(a, b):\n    return a + b\n", "python")

    assert first["interchange_key"] == second["interchange_key"]
    assert first["operation_atoms"][0]["name"] == "add"
    assert first["operation_atoms"][0]["params"] == ["left", "right"]
    assert second["operation_atoms"][0]["name"] == "sum_values"
    assert second["operation_atoms"][0]["params"] == ["a", "b"]


def test_packet_surfaces_operation_signature_in_semantic_expression() -> None:
    packet = build_code_weight_packet("def guarded(x):\n    if x >= 0:\n        return x\n", language="python")
    semantic = packet["semantic_expression"]

    assert semantic["interchange_key"] == packet["semantic_operation_signature"]["interchange_key"]
    assert semantic["operation_signature"]["schema_version"] == "scbe-semantic-operation-signature-v1"
    assert "control_guard" in semantic["operation_path"]
    assert "comparison:gte/2" in semantic["operation_path"]
