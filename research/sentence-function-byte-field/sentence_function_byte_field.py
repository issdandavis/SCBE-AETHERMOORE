"""Sentence-function bytes beside a conserved identity.

The Essay 1 guide supplies the codes. This module copies them into a side
channel. It does not rewrite the identity bytes, and it does not call the
14-layer pipeline or the nested-patch attention path.

Essay prose is not in the catalog. Callers pass the bytes they want to test.
"""

from __future__ import annotations

import json
from pathlib import Path

MAGIC = b"SFB1"
VERSION = 1
CHANNELS = ("paragraph", "sort", "slot", "job", "phrase")

_CATALOG = json.loads(Path(__file__).with_name("sentenceFunctionCatalog.json").read_text(encoding="utf-8"))
_SENTENCES = {row["id"]: row for row in _CATALOG["sentences"]}
_VOCAB = {
    "paragraph": max(row["paragraph"] for row in _CATALOG["sentences"]),
    "sort": max(row["code"] for row in _CATALOG["sorts"]),
    "slot": max(row["code"] for row in _CATALOG["slots"]),
    "job": max(row["code"] for row in _CATALOG["jobs"]),
    "phrase": max(row["code"] for row in _CATALOG["phrases"]),
}


def _u32(value: int) -> bytes:
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError("integer does not fit in uint32")
    return value.to_bytes(4, "little")


def _read_u32(blob: bytes, cursor: int) -> tuple[int, int]:
    if cursor + 4 > len(blob):
        raise ValueError("byte field ended early")
    return int.from_bytes(blob[cursor : cursor + 4], "little"), cursor + 4


def _paint(identity_len: int, phrase_codes: list[int], spans: list[tuple[int, int]]) -> bytes:
    channel = bytearray(identity_len)
    seen = bytearray(identity_len)
    for code, (start, end) in zip(phrase_codes, spans):
        if start < 0 or end > identity_len or end <= start:
            raise ValueError("phrase span is outside the identity")
        for index in range(start, end):
            if seen[index]:
                raise ValueError("phrase spans overlap")
            seen[index] = 1
            channel[index] = code
    return bytes(channel)


def encode_sentence_byte_field(
    identity: bytes, sentence_id: int, phrase_spans: list[tuple[int, int]] | None = None
) -> bytes:
    """Place one guide row beside identity. Identity is copied, not altered."""

    if not isinstance(identity, (bytes, bytearray)):
        raise TypeError("identity must be bytes")
    identity = bytes(identity)
    row = _SENTENCES.get(sentence_id)
    if row is None:
        raise ValueError(f"sentence {sentence_id} is not in the guide")
    phrase_codes = [int(code) for code in row["phrases"]]
    if len(phrase_codes) > 255:
        raise ValueError("phrase list does not fit in one byte")
    spans = [] if phrase_spans is None else [(int(start), int(end)) for start, end in phrase_spans]
    if phrase_spans is not None and len(spans) != len(phrase_codes):
        raise ValueError("phrase spans must cover every phrase function on the sentence")
    phrase_channel = _paint(len(identity), phrase_codes, spans)
    width = len(identity)
    repeated = {
        "paragraph": bytes([row["paragraph"]]) * width,
        "sort": bytes([row["sort"]]) * width,
        "slot": bytes([row["slot"]]) * width,
        "job": bytes([row["job"]]) * width,
        "phrase": phrase_channel,
    }
    header = bytearray(MAGIC)
    header.append(VERSION)
    header.extend(
        [
            row["id"],
            row["paragraph"],
            row["slot"],
            row["sort"],
            row["job"],
            len(phrase_codes),
        ]
    )
    header.extend(phrase_codes)
    header.append(len(spans))
    for start, end in spans:
        header.extend(_u32(start))
        header.extend(_u32(end))
    header.extend(_u32(width))
    header.extend(identity)
    for name in CHANNELS:
        header.extend(repeated[name])
    return bytes(header)


def decode_sentence_byte_field(blob: bytes) -> dict[str, object]:
    """Read a byte field. Structural checks only; guide matching is separate."""

    if not isinstance(blob, (bytes, bytearray)):
        raise TypeError("byte field must be bytes")
    blob = bytes(blob)
    if len(blob) < 4 or blob[:4] != MAGIC:
        raise ValueError("byte field magic is not SFB1")
    cursor = 4
    if cursor >= len(blob) or blob[cursor] != VERSION:
        raise ValueError("unsupported byte field version")
    cursor += 1
    needed = cursor + 6
    if needed > len(blob):
        raise ValueError("byte field ended early")
    sentence_id, paragraph, slot, sort, job, phrase_count = blob[cursor:needed]
    cursor = needed
    if cursor + phrase_count > len(blob):
        raise ValueError("byte field ended early")
    phrase_codes = list(blob[cursor : cursor + phrase_count])
    cursor += phrase_count
    if cursor >= len(blob):
        raise ValueError("byte field ended early")
    span_count = blob[cursor]
    cursor += 1
    spans: list[tuple[int, int]] = []
    for _ in range(span_count):
        start, cursor = _read_u32(blob, cursor)
        end, cursor = _read_u32(blob, cursor)
        spans.append((start, end))
    identity_len, cursor = _read_u32(blob, cursor)
    identity_end = cursor + identity_len
    channel_end = identity_end + identity_len * len(CHANNELS)
    if identity_len < 0 or channel_end != len(blob) or identity_end > len(blob):
        raise ValueError("byte field length does not match its channels")
    identity = blob[cursor:identity_end]
    cursor = identity_end
    channels: dict[str, bytes] = {}
    for name in CHANNELS:
        channels[name] = blob[cursor : cursor + identity_len]
        cursor += identity_len
    expected = {
        "paragraph": bytes([paragraph]) * identity_len,
        "sort": bytes([sort]) * identity_len,
        "slot": bytes([slot]) * identity_len,
        "job": bytes([job]) * identity_len,
        "phrase": _paint(identity_len, phrase_codes, spans),
    }
    for name in CHANNELS:
        if channels[name] != expected[name]:
            raise ValueError(f"{name} channel does not match the header")
    return {
        "sentence_id": sentence_id,
        "paragraph": paragraph,
        "slot": slot,
        "sort": sort,
        "job": job,
        "phrases": phrase_codes,
        "spans": spans,
        "identity": identity,
        "channels": channels,
    }


def matches_guide(decoded: dict[str, object]) -> bool:
    row = _SENTENCES.get(decoded["sentence_id"])
    if row is None:
        return False
    return (
        decoded["paragraph"] == row["paragraph"]
        and decoded["slot"] == row["slot"]
        and decoded["sort"] == row["sort"]
        and decoded["job"] == row["job"]
        and list(decoded["phrases"]) == list(row["phrases"])
    )


def identity_bytes(blob: bytes) -> bytes:
    return bytes(decode_sentence_byte_field(blob)["identity"])  # type: ignore[arg-type]


def _permutation(size: int, seed: int) -> dict[int, int]:
    items = list(range(1, size + 1))
    state = seed & 0xFFFFFFFF
    for index in range(size - 1, 0, -1):
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        swap = state % (index + 1)
        items[index], items[swap] = items[swap], items[index]
    return {code: items[code - 1] for code in range(1, size + 1)}


def permute_byte_field(blob: bytes, channel: str, seed: int) -> bytes:
    """Bijection over one code channel. Identity bytes and spans stay put."""

    if channel not in _VOCAB:
        raise ValueError(f"unknown channel {channel}")
    decoded = decode_sentence_byte_field(blob)
    mapping = _permutation(_VOCAB[channel], seed)
    remapped = dict(decoded)
    phrases = list(decoded["phrases"])  # type: ignore[arg-type]
    if channel == "phrase":
        phrases = [mapping.get(code, code) for code in phrases]
    elif channel == "paragraph":
        remapped["paragraph"] = mapping[int(decoded["paragraph"])]
    else:
        remapped[channel] = mapping[int(decoded[channel])]
    identity = bytes(decoded["identity"])  # type: ignore[arg-type]
    spans = list(decoded["spans"])  # type: ignore[arg-type]
    phrase_channel = _paint(len(identity), phrases, spans)
    width = len(identity)
    channels = {
        "paragraph": bytes([int(remapped["paragraph"])]) * width,
        "sort": bytes([int(remapped["sort"])]) * width,
        "slot": bytes([int(remapped["slot"])]) * width,
        "job": bytes([int(remapped["job"])]) * width,
        "phrase": phrase_channel,
    }
    header = bytearray(MAGIC)
    header.append(VERSION)
    header.extend(
        [
            int(decoded["sentence_id"]),
            int(remapped["paragraph"]),
            int(remapped["slot"]),
            int(remapped["sort"]),
            int(remapped["job"]),
            len(phrases),
        ]
    )
    header.extend(phrases)
    header.append(len(spans))
    for start, end in spans:
        header.extend(_u32(start))
        header.extend(_u32(end))
    header.extend(_u32(width))
    header.extend(identity)
    for name in CHANNELS:
        header.extend(channels[name])
    return bytes(header)
