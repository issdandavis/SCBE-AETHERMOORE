import json
from pathlib import Path

from scripts.training_data.build_sacred_tongue_syntax_alignment_sft import (
    SCHEMA_VERSION,
    SYNTAX_BLOCKS,
    TONGUES,
    build_records,
    validate_blocks,
    write_outputs,
)


FULL_NAMES = {"Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"}


def test_tongue_map_uses_full_names_and_canonical_coding_primaries():
    assert {tongue["full_name"] for tongue in TONGUES} == FULL_NAMES
    primaries = {tongue["full_name"]: tongue["coding_primary"] for tongue in TONGUES}
    assert primaries == {
        "Kor'aelin": "Python",
        "Avali": "TypeScript",
        "Runethic": "Rust",
        "Cassisivadan": "Mathematica",
        "Umbroth": "Haskell",
        "Draumric": "Markdown",
    }


def test_every_syntax_block_has_all_six_tongue_surfaces():
    validate_blocks(SYNTAX_BLOCKS)
    for block in SYNTAX_BLOCKS:
        assert set(block["surfaces"]) == FULL_NAMES


def test_matrix_literal_is_first_class_and_shape_guarded():
    matrix = next(block for block in SYNTAX_BLOCKS if block["concept_id"] == "matrix_literal")
    assert matrix["semantic_ast"]["node"] == "MatrixLiteral"
    assert matrix["semantic_ast"]["shape"] == [2, 2]
    assert "rectangular" in matrix["invariants"]
    assert "NumPy" in matrix["surfaces"]["Kor'aelin"]["lowering"]
    assert "Dimensions" in matrix["surfaces"]["Cassisivadan"]["lowering"]


def test_lsp_vim_and_binary_wave_blocks_are_present():
    concept_ids = {block["concept_id"] for block in SYNTAX_BLOCKS}
    assert "lsp_diagnostic" in concept_ids
    assert "vim_operator_motion" in concept_ids
    assert "binary_wave_tool_packet" in concept_ids

    lsp = next(block for block in SYNTAX_BLOCKS if block["concept_id"] == "lsp_diagnostic")
    assert lsp["semantic_ast"]["node"] == "LanguageServerProtocolDiagnostic"
    assert "no_apply_without_diagnostic_gate" in lsp["invariants"]

    vim = next(block for block in SYNTAX_BLOCKS if block["concept_id"] == "vim_operator_motion")
    assert vim["semantic_ast"]["operator"] == "change"
    assert vim["semantic_ast"]["motion"] == "inside_function"

    wave = next(block for block in SYNTAX_BLOCKS if block["concept_id"] == "binary_wave_tool_packet")
    assert "semantic_intent_precedes_transport" in wave["invariants"]
    assert "binary-wave" in wave["surfaces"]["Draumric"]["syntax"]


def test_records_are_jsonl_ready_and_include_source_inspiration():
    records = build_records()
    assert len(records) == len(SYNTAX_BLOCKS)
    for record in records:
        assert record["messages"][0]["role"] == "system"
        assistant = json.loads(record["messages"][2]["content"])
        assert assistant["schema_version"] == SCHEMA_VERSION
        assert assistant["source_inspiration"]["video_title"] == "I Built My Own Programming Language"
        assert set(assistant["surfaces"]) == FULL_NAMES


def test_records_keep_full_names_visible():
    records = build_records()
    joined = "\n".join(record["messages"][2]["content"] for record in records)
    for full_name in FULL_NAMES:
        assert full_name in joined


def test_write_outputs(tmp_path: Path):
    records = build_records()
    paths = write_outputs(
        records,
        output_dir=tmp_path / "sft",
        config_path=tmp_path / "config" / "syntax_alignment.json",
    )
    for path in paths.values():
        assert Path(path).exists()

    train_rows = [
        json.loads(line)
        for line in Path(paths["train"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    holdout_rows = [
        json.loads(line)
        for line in Path(paths["holdout"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(train_rows) == len(SYNTAX_BLOCKS) - 1
    assert len(holdout_rows) == 1
    assert holdout_rows[0]["meta"]["concept_id"] == "matrix_multiply"
