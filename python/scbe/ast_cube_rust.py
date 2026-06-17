"""Rust-backed AST cube encoder launcher.

The Rust hot loop lives in ``rust/ast_cube`` and emits the same source
bijection metadata plus 14-wide cube-vector matrices. This module keeps Python
callers from hard-coding the binary path and makes fallback decisions explicit.
"""

from __future__ import annotations

import json
import base64
import hashlib
import struct
import subprocess
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXE = ROOT / "rust" / "ast_cube" / "target" / "release" / "ast_cube.exe"


def rust_encoder_available(exe: Path = DEFAULT_EXE) -> bool:
    return exe.exists() and exe.is_file()


def encode_files(paths: Sequence[str | Path], *, summary: bool = False, exe: Path = DEFAULT_EXE) -> dict[str, Any]:
    """Run the Rust AST-cube encoder for one or more Python source files."""

    if not rust_encoder_available(exe):
        raise FileNotFoundError(
            f"Rust AST cube encoder not built: {exe}. "
            "Build with: cargo build --release --manifest-path rust/ast_cube/Cargo.toml"
        )
    args = [str(exe)]
    if summary:
        args.append("--summary")
    args.extend(str(Path(path)) for path in paths)
    if len(args) == (2 if summary else 1):
        raise ValueError("encode_files requires at least one path")
    proc = subprocess.run(args, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def _read_exact(data: bytes, offset: int, size: int) -> tuple[bytes, int]:
    end = offset + size
    if end > len(data):
        raise ValueError("truncated SCBEAST2 payload")
    return data[offset:end], end


def _read_u8(data: bytes, offset: int) -> tuple[int, int]:
    raw, offset = _read_exact(data, offset, 1)
    return raw[0], offset


def _read_u32(data: bytes, offset: int) -> tuple[int, int]:
    raw, offset = _read_exact(data, offset, 4)
    return struct.unpack_from("<I", raw)[0], offset


def _read_u64(data: bytes, offset: int) -> tuple[int, int]:
    raw, offset = _read_exact(data, offset, 8)
    return struct.unpack_from("<Q", raw)[0], offset


def _read_i64_row(data: bytes, offset: int, width: int) -> tuple[list[int], int]:
    raw, offset = _read_exact(data, offset, 8 * width)
    return list(struct.unpack_from("<" + "q" * width, raw)), offset


def _newline_style(code: int) -> str:
    return {0: "none", 1: "lf", 2: "cr", 3: "crlf"}.get(code, "unknown")


def parse_binary_payload(data: bytes) -> dict[str, Any]:
    """Parse the compact Rust ``SCBEAST2`` binary matrix format."""

    offset = 0
    magic, offset = _read_exact(data, offset, 8)
    if magic != b"SCBEAST2":
        raise ValueError("not an SCBEAST2 payload")
    file_count, offset = _read_u32(data, offset)
    width, offset = _read_u32(data, offset)
    files = []
    node_count = 0

    for _ in range(file_count):
        path_len, offset = _read_u32(data, offset)
        path_raw, offset = _read_exact(data, offset, path_len)
        byte_count, offset = _read_u64(data, offset)
        char_count, offset = _read_u64(data, offset)
        newline_code, offset = _read_u8(data, offset)
        trailing, offset = _read_u8(data, offset)
        digest, offset = _read_exact(data, offset, 32)
        source_len, offset = _read_u64(data, offset)
        source_raw, offset = _read_exact(data, offset, source_len)
        rows, offset = _read_u64(data, offset)

        if byte_count != len(source_raw):
            raise ValueError("SCBEAST2 byte_count does not match source length")
        digest_hex = digest.hex()
        if hashlib.sha256(source_raw).hexdigest() != digest_hex:
            raise ValueError("SCBEAST2 source hash mismatch")
        matrix = []
        for _row in range(rows):
            row, offset = _read_i64_row(data, offset, width)
            matrix.append(row)
        node_count += rows
        files.append(
            {
                "schema": "scbe_ast_cube_rust_binary_file_v1",
                "source_path": path_raw.decode("utf-8"),
                "shape": [rows, width],
                "matrix": matrix,
                "source": source_raw.decode("utf-8", errors="surrogatepass"),
                "bijective": {
                    "schema": "scbe_ast_source_bijection_v1",
                    "encoding": "utf-8",
                    "source_utf8_b64": base64.b64encode(source_raw).decode("ascii"),
                    "source_sha256": digest_hex,
                    "char_count": char_count,
                    "byte_count": byte_count,
                    "newline_style": _newline_style(newline_code),
                    "has_trailing_newline": bool(trailing),
                },
            }
        )

    if offset != len(data):
        raise ValueError("SCBEAST2 payload has trailing bytes")
    if file_count == 1:
        one = dict(files[0])
        one["schema"] = "scbe_ast_cube_rust_binary_v1"
        return one
    return {
        "schema": "scbe_ast_cube_rust_binary_batch_v1",
        "file_count": file_count,
        "node_count": node_count,
        "files": files,
    }


def encode_files_binary(paths: Sequence[str | Path], *, exe: Path = DEFAULT_EXE) -> dict[str, Any]:
    """Run the Rust AST-cube encoder using compact binary matrix transport."""

    if not rust_encoder_available(exe):
        raise FileNotFoundError(
            f"Rust AST cube encoder not built: {exe}. "
            "Build with: cargo build --release --manifest-path rust/ast_cube/Cargo.toml"
        )
    path_args = [str(Path(path)) for path in paths]
    if not path_args:
        raise ValueError("encode_files_binary requires at least one path")
    proc = subprocess.run(
        [str(exe), "--binary", *path_args],
        check=True,
        capture_output=True,
    )
    return parse_binary_payload(proc.stdout)


def encode_files_binary_raw(paths: Sequence[str | Path], *, exe: Path = DEFAULT_EXE) -> bytes:
    """Return raw ``SCBEAST2`` bytes without expanding matrices into Python lists."""

    if not rust_encoder_available(exe):
        raise FileNotFoundError(
            f"Rust AST cube encoder not built: {exe}. "
            "Build with: cargo build --release --manifest-path rust/ast_cube/Cargo.toml"
        )
    path_args = [str(Path(path)) for path in paths]
    if not path_args:
        raise ValueError("encode_files_binary_raw requires at least one path")
    proc = subprocess.run(
        [str(exe), "--binary", *path_args],
        check=True,
        capture_output=True,
    )
    return proc.stdout


__all__ = [
    "DEFAULT_EXE",
    "encode_files",
    "encode_files_binary",
    "encode_files_binary_raw",
    "parse_binary_payload",
    "rust_encoder_available",
]
