"""Strict UTF-8 byte-token bridge for Clay's fixed 276-token parent vocabulary.

Clay's existing parent does not contain ordinary VQCC letters such as ``A``,
``B``, ``T``, newlines, or lowercase prose as literal tokens.  It does contain
one private-use Unicode token for every byte value.  This module maps all VQCC
prompt and label text through those byte tokens, so the frozen parent can read
the new task without changing its embedding table or inventing unknown-token
behavior.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


CODEC_SCHEMA = "clay.vqcc-utf8-pua-byte-codec.v1"
BYTE_TOKEN_BASE = 0xE100
BYTE_TOKEN_COUNT = 256
EXPECTED_PARENT_VOCAB_SIZE = 276
PARENT_VOCAB_SHA256 = "bb0541789d0cfac2e02f7c3321d93ce1b9dc5513e2852499d81122a1e600e5b1"
VOCAB_HASH_ALGORITHM = "sha256-json-utf8-ensure-ascii-sort-keys-compact-v1"
TASK_LABELS = {
    "finding_binding": ("A", "B"),
    "gate_count": ("A", "B", "T"),
}


class ByteCodecError(ValueError):
    """Raised when text, labels, or a parent vocabulary violate the codec."""


def byte_token(value: int) -> str:
    if type(value) is not int or not 0 <= value < BYTE_TOKEN_COUNT:
        raise ByteCodecError("byte token value must be an integer in [0, 255]")
    return chr(BYTE_TOKEN_BASE + value)


def encode_bytes(payload: bytes) -> tuple[str, ...]:
    if not isinstance(payload, bytes):
        raise ByteCodecError("payload must be bytes")
    return tuple(byte_token(value) for value in payload)


def decode_bytes(tokens: Sequence[str]) -> bytes:
    values: list[int] = []
    for index, token in enumerate(tokens):
        if not isinstance(token, str) or len(token) != 1:
            raise ByteCodecError(f"token {index} is not one Unicode scalar")
        value = ord(token) - BYTE_TOKEN_BASE
        if not 0 <= value < BYTE_TOKEN_COUNT:
            raise ByteCodecError(f"token {index} is outside Clay's byte-token block")
        values.append(value)
    return bytes(values)


def encode_text(text: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise ByteCodecError("text must be a string")
    return encode_bytes(text.encode("utf-8", errors="strict"))


def decode_text(tokens: Sequence[str]) -> str:
    try:
        return decode_bytes(tokens).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ByteCodecError("byte-token sequence is not valid UTF-8") from exc


def encode_label(task: str, label: str) -> tuple[str, ...]:
    allowed = TASK_LABELS.get(task)
    if allowed is None:
        raise ByteCodecError(f"unknown VQCC task: {task!r}")
    if label not in allowed:
        raise ByteCodecError(f"label {label!r} is not valid for {task}")
    encoded = encode_text(label)
    if len(encoded) != 1:
        raise AssertionError("VQCC labels must encode to exactly one byte token")
    return encoded


def decode_label(task: str, tokens: Sequence[str]) -> str:
    allowed = TASK_LABELS.get(task)
    if allowed is None:
        raise ByteCodecError(f"unknown VQCC task: {task!r}")
    if len(tokens) != 1:
        raise ByteCodecError("VQCC label output must contain exactly one byte token")
    label = decode_text(tokens)
    if label not in allowed:
        raise ByteCodecError(f"decoded label {label!r} is not valid for {task}")
    return label


def _normalise_vocab(vocab: Sequence[str] | Mapping[str, int]) -> tuple[list[str], dict[str, int]]:
    if isinstance(vocab, Mapping):
        if any(type(index) is not int or index < 0 for index in vocab.values()):
            raise ByteCodecError("vocabulary IDs must be nonnegative integers")
        if len(set(vocab.values())) != len(vocab):
            raise ByteCodecError("vocabulary IDs must be unique")
        if set(vocab.values()) != set(range(len(vocab))):
            raise ByteCodecError("vocabulary IDs must be contiguous from zero")
        ordered = [""] * len(vocab)
        for token, index in vocab.items():
            ordered[index] = token
    else:
        ordered = list(vocab)
    if any(not isinstance(token, str) or len(token) != 1 for token in ordered):
        raise ByteCodecError("every parent token must be one Unicode scalar")
    if len(set(ordered)) != len(ordered):
        raise ByteCodecError("parent vocabulary tokens must be unique")
    return ordered, {token: index for index, token in enumerate(ordered)}


def canonical_vocab_sha256(vocab: Sequence[str] | Mapping[str, int]) -> str:
    ordered, _stoi = _normalise_vocab(vocab)
    payload = json.dumps(
        ordered,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_parent_vocab(
    vocab: Sequence[str] | Mapping[str, int],
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    ordered, stoi = _normalise_vocab(vocab)
    if len(ordered) != EXPECTED_PARENT_VOCAB_SIZE:
        raise ByteCodecError(
            f"parent vocabulary size differs: {len(ordered)} != {EXPECTED_PARENT_VOCAB_SIZE}"
        )
    missing = [value for value in range(BYTE_TOKEN_COUNT) if byte_token(value) not in stoi]
    if missing:
        raise ByteCodecError(f"parent vocabulary lacks byte tokens: {missing[:8]}")
    actual_sha256 = canonical_vocab_sha256(ordered)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ByteCodecError(
            f"parent vocabulary hash differs: expected {expected_sha256}, got {actual_sha256}"
        )
    label_ids = {
        task: {label: stoi[encode_label(task, label)[0]] for label in labels}
        for task, labels in TASK_LABELS.items()
    }
    return {
        "schema": CODEC_SCHEMA,
        "vocab_size": len(ordered),
        "vocab_sha256": actual_sha256,
        "vocab_hash_algorithm": VOCAB_HASH_ALGORITHM,
        "byte_token_base": BYTE_TOKEN_BASE,
        "byte_token_count": BYTE_TOKEN_COUNT,
        "all_byte_tokens_present": True,
        "label_token_ids": label_ids,
        "literal_labels_used": False,
    }
