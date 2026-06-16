"""Smoke tests for the Rust AST cube hot loop."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest

from python.scbe.ast_cube_rust import (
    encode_files,
    encode_files_binary,
    encode_files_binary_raw,
    parse_binary_payload,
    rust_encoder_available,
)


@pytest.mark.skipif(not rust_encoder_available(), reason="Rust ast_cube binary is not built")
def test_rust_ast_cube_emits_matrix_and_bijective_source_lane() -> None:
    path = Path(__file__).with_name("test_ast_cube_encoder.py")
    payload = encode_files([path])

    assert payload["schema"] == "scbe_ast_cube_rust_v1"
    assert payload["shape"][1] == 14
    assert payload["matrix"]
    assert all(len(row) == 14 for row in payload["matrix"])

    raw = base64.b64decode(payload["bijective"]["source_utf8_b64"])
    assert hashlib.sha256(raw).hexdigest() == payload["bijective"]["source_sha256"]


@pytest.mark.skipif(not rust_encoder_available(), reason="Rust ast_cube binary is not built")
def test_rust_ast_cube_batch_summary() -> None:
    paths = [
        Path(__file__).with_name("test_ast_cube_encoder.py"),
        Path(__file__).parents[1] / "python" / "scbe" / "ast_cube_encoder.py",
    ]
    payload = encode_files(paths, summary=True)

    assert payload["schema"] == "scbe_ast_cube_rust_batch_v1"
    assert payload["file_count"] == 2
    assert payload["node_count"] > 0
    assert "matrix" not in payload["files"][0]


@pytest.mark.skipif(not rust_encoder_available(), reason="Rust ast_cube binary is not built")
def test_rust_ast_cube_binary_transport_matches_json_matrix() -> None:
    path = Path(__file__).with_name("test_ast_cube_encoder.py")
    json_payload = encode_files([path])
    binary_payload = encode_files_binary([path])

    assert binary_payload["schema"] == "scbe_ast_cube_rust_binary_v1"
    assert binary_payload["shape"] == json_payload["shape"]
    assert binary_payload["matrix"] == json_payload["matrix"]
    assert binary_payload["source"] == path.read_text(encoding="utf-8")
    assert binary_payload["bijective"]["source_sha256"] == json_payload["bijective"]["source_sha256"]


@pytest.mark.skipif(not rust_encoder_available(), reason="Rust ast_cube binary is not built")
def test_rust_ast_cube_binary_batch() -> None:
    paths = [
        Path(__file__).with_name("test_ast_cube_encoder.py"),
        Path(__file__).parents[1] / "python" / "scbe" / "ast_cube_encoder.py",
    ]
    payload = encode_files_binary(paths)

    assert payload["schema"] == "scbe_ast_cube_rust_binary_batch_v1"
    assert payload["file_count"] == 2
    assert payload["node_count"] == sum(file["shape"][0] for file in payload["files"])
    assert all(file["matrix"] for file in payload["files"])


@pytest.mark.skipif(not rust_encoder_available(), reason="Rust ast_cube binary is not built")
def test_rust_ast_cube_binary_raw_stays_compact_and_parseable() -> None:
    path = Path(__file__).with_name("test_ast_cube_encoder.py")
    raw = encode_files_binary_raw([path])

    assert raw.startswith(b"SCBEAST2")
    parsed = parse_binary_payload(raw)
    assert parsed["shape"][1] == 14
    assert parsed["source"] == path.read_text(encoding="utf-8")


def test_binary_parser_rejects_bad_magic() -> None:
    with pytest.raises(ValueError, match="not an SCBEAST2"):
        parse_binary_payload(b"BADMAGIC")
