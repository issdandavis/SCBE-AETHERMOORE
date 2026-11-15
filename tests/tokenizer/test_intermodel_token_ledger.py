"""Exact byte/token seams and cross-language code-operation joins."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

import pytest

from python.scbe.intermodel_token_ledger import (
    CodeModelInput,
    IntermodelTokenError,
    build_binary_token_atlas,
    build_code_intermodel_ledger,
    build_intermodel_seam_ledger,
    trace_byte_tokenizer,
    trace_code_lexical,
    trace_from_offsets,
    trace_sacred_tongue,
    verify_model_token_trace,
    verify_binary_token_atlas,
    verify_code_intermodel_ledger,
    verify_intermodel_seam_ledger,
    _stable_id,
)


def _fingerprint(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def test_stable_identity_preserves_component_types_and_boundaries() -> None:
    assert _stable_id("x", 1) != _stable_id("x", "1")
    assert _stable_id("x", "a", "b") != _stable_id("x", "a\x1fb")


def test_binary_atlas_reuses_all_existing_exact_byte_views() -> None:
    data = bytes(range(256))
    atlas = build_binary_token_atlas(data)

    assert atlas["source_byte_count"] == 256
    assert atlas["byte_type_count"] == 256
    assert len(atlas["occurrences"]) == 256
    assert verify_binary_token_atlas(data, atlas)

    for row in atlas["byte_types"]:
        value = row["byte_value"]
        assert int(row["bits_msb_first"], 2) == value
        assert set(row["balanced_trits"]) <= {-1, 0, 1}
        assert set(row["six_tongues"]) == {"ko", "av", "ru", "ca", "um", "dr"}
        cube = row["wafer_profiles"]["cube-face-byte-v1"]
        region = row["wafer_profiles"]["ca-opcode-region-v1"]
        assert (cube["cell"] << 2) | cube["orientation"] == value
        assert (region["orientation"] << 6) | region["opcode"] == value


def test_unicode_offsets_join_byte_tongue_and_sparse_code_tokens() -> None:
    source = "café = a + b\n"
    byte_trace = trace_byte_tokenizer(source, model_id="byte-model")
    tongue_trace = trace_sacred_tongue(source, tongue="ca", model_id="tongue-model")
    code_trace = trace_code_lexical(source, model_id="code-model", language="python")

    ledger = build_intermodel_seam_ledger(source, (byte_trace, tongue_trace, code_trace))

    assert ledger["source_byte_count"] == len(source.encode("utf-8"))
    assert ledger["model_count"] == 3
    assert ledger["metrics"]["maximum_models_on_one_seam"] == 3
    assert ledger["metrics"]["unobserved_seam_count"] == 0
    assert ledger["metrics"]["nested_address_collision_count"] == 0
    assert ledger["token_nest"]["carrier_dimensions"] == 18
    assert verify_intermodel_seam_ledger(source, (byte_trace, tongue_trace, code_trace), ledger)
    code_cafe = next(row for row in code_trace["tokens"] if row["surface"] == "caf")
    assert bytes.fromhex(code_cafe["byte_hex"]) == b"caf"
    # The ASCII-oriented code lexer leaves the non-ASCII character explicit as
    # a separate source-bound token instead of losing its second UTF-8 byte.
    accented = next(row for row in code_trace["tokens"] if row["surface"] == "é")
    assert bytes.fromhex(accented["byte_hex"]).decode("utf-8") == "é"


def test_external_tokenizer_offsets_are_converted_to_exact_utf8_bytes() -> None:
    source = "AéZ"
    trace = trace_from_offsets(
        source,
        model_id="external",
        tokenizer_id="test-char-tokenizer",
        tokenizer_fingerprint=_fingerprint("test-char-tokenizer-v1"),
        token_ids=(10, 11, 12),
        offsets=((0, 1), (1, 2), (2, 3)),
        offset_unit="char",
        surfaces=("A", "é", "Z"),
    )

    assert [(row["byte_start"], row["byte_end"]) for row in trace["tokens"]] == [
        (0, 1),
        (1, 3),
        (3, 4),
    ]
    assert trace["tokens"][1]["byte_hex"] == "c3a9"
    assert trace["receipt_security"] == "unkeyed-corruption-detection-only"
    assert verify_model_token_trace(
        source,
        trace,
        expected_model_id="external",
        expected_tokenizer_id="test-char-tokenizer",
        expected_tokenizer_fingerprint=_fingerprint("test-char-tokenizer-v1"),
    )
    assert not verify_model_token_trace(source, trace, expected_tokenizer_id="different-tokenizer")


def test_trace_verifier_rejects_reordered_positive_spans_even_with_valid_hash() -> None:
    source = "abc"
    trace = trace_byte_tokenizer(source, model_id="bytes")
    changed = deepcopy(trace)
    changed["tokens"] = list(reversed(changed["tokens"]))
    for index, row in enumerate(changed["tokens"]):
        row["token_index"] = index
    body = dict(changed)
    body.pop("trace_sha256")
    changed["trace_sha256"] = sha256(
        json.dumps(
            body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert not verify_model_token_trace(source, changed)


def test_full_trace_rejects_gaps_but_sparse_trace_records_them() -> None:
    kwargs = {
        "source": "a b",
        "model_id": "words",
        "tokenizer_id": "word-only",
        "tokenizer_fingerprint": _fingerprint("word-only"),
        "token_ids": ("a", "b"),
        "offsets": ((0, 1), (2, 3)),
        "offset_unit": "char",
    }
    with pytest.raises(IntermodelTokenError, match="full-coverage"):
        trace_from_offsets(**kwargs)
    sparse = trace_from_offsets(**kwargs, coverage_mode="sparse")
    assert sparse["coverage"]["gaps"] == [[1, 2]]


def test_tampered_trace_or_ledger_fails_closed() -> None:
    source = "x + y"
    byte_trace = trace_byte_tokenizer(source, model_id="bytes")
    tongue_trace = trace_sacred_tongue(source, tongue="ko", model_id="ko")
    ledger = build_intermodel_seam_ledger(source, (byte_trace, tongue_trace))

    changed_trace = deepcopy(byte_trace)
    changed_trace["tokens"][0]["byte_hex"] = "00"
    with pytest.raises(IntermodelTokenError, match="receipt hash"):
        build_intermodel_seam_ledger(source, (changed_trace, tongue_trace))

    changed_ledger = deepcopy(ledger)
    changed_ledger["seams"][0]["byte_hex"] = "00"
    assert not verify_intermodel_seam_ledger(source, (byte_trace, tongue_trace), changed_ledger)


def _add_inputs() -> tuple[CodeModelInput, ...]:
    return (
        CodeModelInput("py", "python", "def add(a, b):\n    return a + b\n", "add.py"),
        CodeModelInput("ts", "typescript", "function add(a, b) { return a + b; }\n", "add.ts"),
        CodeModelInput("rs", "rust", "fn add(a: i32, b: i32) -> i32 { return a + b }\n", "add.rs"),
        CodeModelInput("c", "c", "int add(int a, int b) { return a + b; }\n", "add.c"),
    )


def test_code_tokens_join_across_languages_on_operation_cells() -> None:
    inputs = _add_inputs()
    ledger = build_code_intermodel_ledger(inputs)

    assert ledger["aligned"] is True
    assert ledger["operation_paths"] == [["function_definition/2", "return_flow", "arithmetic:add/2"]]
    assert len(ledger["action_cells"]) == 3
    assert [row["semantic_atom"] for row in ledger["action_cells"]] == [
        "FLOW",
        "FLOW",
        "TRANSFORM",
    ]
    assert all(len(row["bindings"]) == 4 for row in ledger["action_cells"])
    assert ledger["metrics"]["binding_count"] == 12
    assert ledger["metrics"]["all_bindings_byte_exact"] is True
    assert ledger["metrics"]["cross_code_nested_address_collision_count"] == 0
    assert ledger["code_face_axis"] == [
        "c",
        "cpp",
        "csharp",
        "go",
        "haskell",
        "java",
        "javascript",
        "julia",
        "kotlin",
        "lua",
        "php",
        "python",
        "ruby",
        "rust",
        "scala",
        "swift",
        "typescript",
        "zig",
    ]
    assert all(source["code_face"]["face_index"] is not None for source in ledger["sources"])
    assert verify_code_intermodel_ledger(inputs, ledger)

    expected_surfaces = [
        {"add"},
        {"return"},
        {"+"},
    ]
    for cell, expected in zip(ledger["action_cells"], expected_surfaces, strict=True):
        assert {binding["surface"] for binding in cell["bindings"]} == expected
        assert all(bytes.fromhex(binding["byte_hex"]) for binding in cell["bindings"])
        assert all(binding["token_nest_id"] for binding in cell["bindings"])


def test_different_operation_paths_are_preserved_without_false_join() -> None:
    inputs = (
        CodeModelInput("add", "python", "def calc(a, b):\n    return a + b\n"),
        CodeModelInput("sub", "python", "def calc(a, b):\n    return a - b\n"),
    )
    ledger = build_code_intermodel_ledger(inputs)

    assert ledger["aligned"] is False
    assert len(ledger["interchange_keys"]) == 2
    assert ledger["action_cells"] == []
    assert ledger["metrics"]["binding_count"] == 0
    assert ledger["metrics"]["all_bindings_byte_exact"] is False
    assert ledger["claim_boundary"]["operation_signature_is_not_program_equivalence_proof"]


def test_code_ledger_tamper_breaks_reconstruction() -> None:
    inputs = _add_inputs()[:2]
    ledger = build_code_intermodel_ledger(inputs)
    changed = deepcopy(ledger)
    changed["action_cells"][0]["bindings"][0]["byte_hex"] = "00"
    assert not verify_code_intermodel_ledger(inputs, changed)


def test_code_ledger_rejects_whitespace_only_sources_explicitly() -> None:
    inputs = (
        CodeModelInput("spaces", "python", "   "),
        CodeModelInput("linebreak", "python", "\n\t"),
    )
    with pytest.raises(IntermodelTokenError, match="contains no lexical tokens"):
        build_code_intermodel_ledger(inputs)


def test_function_definition_binds_declaration_not_earlier_name_occurrence() -> None:
    inputs = (
        CodeModelInput(
            "left",
            "python",
            "add = 0\ndef add(first, second):\n    return first + second\n",
        ),
        CodeModelInput(
            "right",
            "python",
            "add = 1\ndef add(first, second):\n    return first + second\n",
        ),
    )
    ledger = build_code_intermodel_ledger(inputs)
    assert ledger["operation_paths"] == [
        [
            "function_definition/2",
            "return_flow",
            "assignment:assign/2",
            "arithmetic:add/2",
        ]
    ]
    definition = next(cell for cell in ledger["action_cells"] if cell["operation"] == "function_definition/2")
    assert {binding["surface"] for binding in definition["bindings"]} == {"add"}
    assert all(binding["byte_hex"] == b"add".hex() for binding in definition["bindings"])
