"""
Sacred Tongue Instruction Binary (STIB) — v1.

Universal canonical form for tongue programs. Every language emitter consumes
this. Every emitter can also produce it from source (bijective). Adding a new
language = writing one emitter that reads STIB.

WIRE FORMAT (v1):

  off   size           field
  ----  -------------  ----------------------------------------------------
  0     4              magic = b"STIB"
  4     1              version major (0x01)
  5     1              version minor (0x00)
  6     1              tongue id (0=KO 1=AV 2=RU 3=CA 4=UM 5=DR)
  7     1              flags (reserved, 0x00)
  8     1              fn_name length n
  9     n              fn_name (UTF-8, no null terminator)
  9+n   1              arg count m
  ...   per-arg:       1 byte arg_name_length + arg_name (UTF-8)
  ...   2              op_count (uint16, big-endian)
  ...   op_count       opcode bytes (no operands in v1; CA arithmetic only)
  ...   32             SHA-256 over everything before this field

All multi-byte integers are big-endian. Strings are length-prefixed UTF-8,
length is one unsigned byte (0-255). Future versions reserve a 4-bit prefix
on each opcode for immediate-operand encoding; v1 ops always use 0 prefix.

The hash is computed over the entire blob excluding the hash itself, so any
tampering of headers, opcodes, or names is detected at parse time.

DESIGN INTENT: this is the substrate the user asked for — "a same basis file
for all our commands that any language can fall back to." Token sequences,
opcode names, and emitted source are all derivable from STIB; STIB is
derivable from any of them.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import List, Sequence

MAGIC = b"STIB"
VERSION_MAJOR = 0x01
VERSION_MINOR = 0x00
HASH_LEN = 32  # SHA-256

TONGUE_NAMES = {0: "KO", 1: "AV", 2: "RU", 3: "CA", 4: "UM", 5: "DR"}
TONGUE_IDS = {v: k for k, v in TONGUE_NAMES.items()}


class STIBError(ValueError):
    """Any STIB encode/decode/integrity failure."""


@dataclass
class STIBBlock:
    """In-memory representation of a parsed STIB blob."""

    tongue: str  # "CA" etc.
    fn_name: str
    arg_names: List[str]
    opcodes: List[int]
    flags: int = 0
    version: tuple = (VERSION_MAJOR, VERSION_MINOR)


def _check_str(s: str, label: str) -> bytes:
    raw = s.encode("utf-8")
    if len(raw) > 255:
        raise STIBError(f"{label} too long ({len(raw)} bytes; max 255)")
    return raw


def encode(block: STIBBlock) -> bytes:
    """Serialize a STIBBlock to a STIB v1 blob."""
    if block.tongue not in TONGUE_IDS:
        raise STIBError(f"unknown tongue {block.tongue!r}")
    if len(block.opcodes) > 0xFFFF:
        raise STIBError(f"too many opcodes ({len(block.opcodes)}; max 65535)")
    for op in block.opcodes:
        if not (0 <= int(op) <= 0xFF):
            raise STIBError(f"opcode out of range: {op}")
    if len(block.arg_names) > 255:
        raise STIBError(f"too many args ({len(block.arg_names)}; max 255)")

    fn_bytes = _check_str(block.fn_name, "fn_name")
    arg_bytes = [_check_str(a, "arg_name") for a in block.arg_names]

    parts: List[bytes] = []
    parts.append(MAGIC)
    parts.append(bytes([VERSION_MAJOR, VERSION_MINOR]))
    parts.append(bytes([TONGUE_IDS[block.tongue]]))
    parts.append(bytes([block.flags & 0xFF]))
    parts.append(bytes([len(fn_bytes)]))
    parts.append(fn_bytes)
    parts.append(bytes([len(arg_bytes)]))
    for a in arg_bytes:
        parts.append(bytes([len(a)]))
        parts.append(a)
    parts.append(struct.pack(">H", len(block.opcodes)))
    parts.append(bytes(int(op) & 0xFF for op in block.opcodes))

    body = b"".join(parts)
    digest = hashlib.sha256(body).digest()
    return body + digest


def decode(blob: bytes) -> STIBBlock:
    """Parse a STIB v1 blob. Verifies magic, version, integrity hash."""
    if len(blob) < len(MAGIC) + 2 + 4 + HASH_LEN:
        raise STIBError("blob too small")
    if not blob.startswith(MAGIC):
        raise STIBError("bad magic")
    body, digest = blob[:-HASH_LEN], blob[-HASH_LEN:]
    if hashlib.sha256(body).digest() != digest:
        raise STIBError("integrity hash mismatch")

    pos = len(MAGIC)
    major, minor = body[pos], body[pos + 1]
    pos += 2
    if major != VERSION_MAJOR:
        raise STIBError(f"unsupported version {major}.{minor}")
    tongue_id = body[pos]
    pos += 1
    flags = body[pos]
    pos += 1
    if tongue_id not in TONGUE_NAMES:
        raise STIBError(f"unknown tongue id {tongue_id}")

    fn_len = body[pos]
    pos += 1
    fn_name = body[pos : pos + fn_len].decode("utf-8")
    pos += fn_len

    arg_count = body[pos]
    pos += 1
    arg_names: List[str] = []
    for _ in range(arg_count):
        n = body[pos]
        pos += 1
        arg_names.append(body[pos : pos + n].decode("utf-8"))
        pos += n

    op_count = struct.unpack(">H", body[pos : pos + 2])[0]
    pos += 2
    opcodes = list(body[pos : pos + op_count])
    pos += op_count
    if pos != len(body):
        raise STIBError(f"trailing bytes after opcodes ({len(body) - pos})")

    return STIBBlock(
        tongue=TONGUE_NAMES[tongue_id],
        fn_name=fn_name,
        arg_names=arg_names,
        opcodes=opcodes,
        flags=flags,
        version=(major, minor),
    )


def from_compiled(prog) -> STIBBlock:
    """Build a STIBBlock from a CompiledProgram (CA-only first slice)."""
    return STIBBlock(
        tongue="CA",
        fn_name=prog.fn_name,
        arg_names=list(prog.arg_names),
        opcodes=[op_id for op_id, _ in prog.op_trace],
    )


def to_token_sequence(block: STIBBlock) -> Sequence[int]:
    """Recover the raw token sequence (just the opcode bytes)."""
    return list(block.opcodes)
