"""Hash-bound source authority for packet-free ordinary and retention lanes.

Packet-free prompts are controls, not unlabeled free text.  A family label alone
cannot establish source separation because the same artifact can be relabeled.
This module binds every row to an admitted authority file, an exact source
artifact, and an exact UTF-8 byte span.  A small, named deterministic transform
may derive the final prompt from that span.  The source-family identity is
derived from the authority hash instead of being supplied by a caller.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .prime_token_training import sha256_file

PACKET_FREE_AUTHORITY_SCHEMA = "scbe.prime-token-packet-free-source-authority.v1"
PACKET_FREE_REVIEW_STATUS = "ADMITTED"
PACKET_FREE_FAMILY_PREFIX = "packet-free-authority:"
IDENTITY_TRANSFORM = "identity_utf8_v1"
LINE_STRIP_JOIN_TRANSFORM = "line_strip_join_space_v1"
ALLOWED_TEXT_TRANSFORMS = (IDENTITY_TRANSFORM, LINE_STRIP_JOIN_TRANSFORM)
NO_AUTHORITY = "NOT_AUTHORIZED"
REQUIRED_AUTHORITY_FIELDS = (
    "training_intake",
    "optimization",
    "promotion",
    "partial_unfreeze",
    "tool_dispatch",
)


def _required_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _required_content_text(value: object, *, label: str) -> str:
    """Return non-empty content without silently changing its whitespace."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _required_sha256(value: object, *, label: str) -> str:
    digest = _required_text(value, label=label).casefold()
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return digest


def _required_nonnegative_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _path_key(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").casefold()


def transform_packet_free_text(value: str, transform: str) -> str:
    """Apply one allow-listed, deterministic packet-free text transform."""

    if transform == IDENTITY_TRANSFORM:
        return value
    if transform == LINE_STRIP_JOIN_TRANSFORM:
        return " ".join(part.strip() for part in value.splitlines() if part.strip())
    raise ValueError(f"unsupported packet-free text transform: {transform}")


def packet_free_family_id(authority_path: str | Path) -> str:
    """Return the only accepted family identity for one authority file."""

    path = Path(authority_path).resolve(strict=True)
    return f"{PACKET_FREE_FAMILY_PREFIX}{sha256_file(path)}"


def _load_authority(path: Path, *, lane: str) -> tuple[dict[str, Any], str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{lane} source authority must contain one JSON object")
    if value.get("schema") != PACKET_FREE_AUTHORITY_SCHEMA:
        raise ValueError(f"{lane} source authority schema changed")
    if value.get("lane") != lane:
        raise ValueError(f"{lane} source authority names another lane")
    if value.get("review_status") != PACKET_FREE_REVIEW_STATUS:
        raise ValueError(f"{lane} source authority is not admitted")
    authority = value.get("authority")
    if not isinstance(authority, dict):
        raise ValueError(f"{lane} source authority omitted its authority boundary")
    for field in REQUIRED_AUTHORITY_FIELDS:
        if authority.get(field) != NO_AUTHORITY:
            raise ValueError(f"{lane} source authority unexpectedly authorizes {field}")
    return value, sha256_file(path)


def validate_packet_free_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    authority_path: str | Path,
    lane: str,
    max_bytes: int = 512,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Validate and canonicalize one packet-free lane.

    The authority records exact source spans.  The input rows may omit
    ``source_family``; if present it must equal the authority-derived identity.
    Returned rows always carry the derived identity and replayable source fields.
    """

    if lane not in {"ordinary", "retention"}:
        raise ValueError("packet-free lane must be ordinary or retention")
    if max_bytes < 1 or max_bytes > 512:
        raise ValueError("packet-free byte bound must be in [1,512]")
    path = Path(authority_path).resolve(strict=True)
    authority, authority_sha256 = _load_authority(path, lane=lane)
    family_id = f"{PACKET_FREE_FAMILY_PREFIX}{authority_sha256}"

    raw_sources = authority.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError(f"{lane} source authority has no source artifacts")

    record_authorities: dict[str, dict[str, object]] = {}
    source_paths: set[str] = set()
    source_sha256s: set[str] = set()
    locator_keys: set[str] = set()
    for source_index, source in enumerate(raw_sources):
        if not isinstance(source, dict):
            raise TypeError(f"{lane} source artifact {source_index} must be an object")
        source_path_text = _required_text(
            source.get("path"), label=f"{lane} source path"
        )
        source_path = Path(source_path_text)
        if not source_path.is_absolute():
            raise ValueError(f"{lane} source path must be absolute")
        source_path = source_path.resolve(strict=True)
        path_key = _path_key(source_path)
        if path_key in source_paths:
            raise ValueError(f"{lane} source authority repeats a source path")
        source_paths.add(path_key)
        expected_sha256 = _required_sha256(
            source.get("sha256"), label=f"{lane} source hash"
        )
        actual_sha256 = sha256_file(source_path)
        if actual_sha256 != expected_sha256:
            raise RuntimeError(f"{lane} source artifact hash differs")
        expected_bytes = _required_nonnegative_int(
            source.get("bytes"), label=f"{lane} source bytes"
        )
        source_bytes = source_path.read_bytes()
        if len(source_bytes) != expected_bytes:
            raise RuntimeError(f"{lane} source artifact byte count differs")
        source_sha256s.add(actual_sha256)
        raw_records = source.get("records")
        if not isinstance(raw_records, list) or not raw_records:
            raise ValueError(f"{lane} source artifact has no record spans")
        for record_index, record in enumerate(raw_records):
            if not isinstance(record, dict):
                raise TypeError(
                    f"{lane} source record {record_index} must be an object"
                )
            identity = _required_text(
                record.get("id"), label=f"{lane} source record id"
            )
            if identity in record_authorities:
                raise ValueError(f"{lane} source authority repeats a record identity")
            locator = _required_text(
                record.get("source_locator"), label=f"{lane} source locator"
            )
            locator_key = locator.casefold()
            if locator_key in locator_keys:
                raise ValueError(f"{lane} source authority repeats a source locator")
            locator_keys.add(locator_key)
            start = _required_nonnegative_int(
                record.get("byte_start"), label=f"{lane} byte_start"
            )
            end = _required_nonnegative_int(
                record.get("byte_end"), label=f"{lane} byte_end"
            )
            if end <= start or end > len(source_bytes):
                raise ValueError(f"{lane} source span is empty or out of bounds")
            span = source_bytes[start:end]
            try:
                text = span.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"{lane} source span is not exact UTF-8 text") from exc
            excerpt_sha256 = _required_sha256(
                record.get("excerpt_sha256"), label=f"{lane} source record excerpt hash"
            )
            if sha256(span).hexdigest() != excerpt_sha256:
                raise RuntimeError(f"{lane} source record excerpt hash differs")
            text_transform = _required_text(
                record.get("text_transform"),
                label=f"{lane} source record text transform",
            )
            if text_transform not in ALLOWED_TEXT_TRANSFORMS:
                raise ValueError(
                    f"unsupported packet-free text transform: {text_transform}"
                )
            transformed_text = transform_packet_free_text(text, text_transform)
            if not transformed_text.strip():
                raise ValueError(f"{lane} source transform produced empty text")
            content_sha256 = _required_sha256(
                record.get("content_sha256"), label=f"{lane} source record content hash"
            )
            if sha256(transformed_text.encode("utf-8")).hexdigest() != content_sha256:
                raise RuntimeError(f"{lane} source record content hash differs")
            record_authorities[identity] = {
                "source_locator": locator,
                "source_path": str(source_path),
                "source_path_key": path_key,
                "source_artifact_sha256": actual_sha256,
                "source_byte_start": start,
                "source_byte_end": end,
                "source_excerpt_sha256": excerpt_sha256,
                "text_transform": text_transform,
                "content_sha256": content_sha256,
                "text": transformed_text,
            }

    canonical: list[dict[str, object]] = []
    seen_rows: set[str] = set()
    for row_index, value in enumerate(rows):
        if not isinstance(value, Mapping):
            raise TypeError(f"{lane} row {row_index} must be an object")
        identity = _required_text(value.get("id"), label=f"{lane} identity")
        if identity in seen_rows:
            raise ValueError(f"{lane} repeats an identity")
        seen_rows.add(identity)
        bound = record_authorities.get(identity)
        if bound is None:
            raise ValueError(f"{lane} row is absent from its source authority")
        text = _required_content_text(value.get("text"), label=f"{lane} text")
        if text != bound["text"]:
            raise ValueError(
                f"{lane} row text differs from its authorized source transform"
            )
        locator = _required_text(
            value.get("source_locator"), label=f"{lane} source locator"
        )
        if locator != bound["source_locator"]:
            raise ValueError(f"{lane} row locator differs from its source authority")
        content_sha256 = _required_sha256(
            value.get("content_sha256"), label=f"{lane} content hash"
        )
        if (
            content_sha256 != bound["content_sha256"]
            or sha256(text.encode("utf-8")).hexdigest() != content_sha256
        ):
            raise ValueError(
                f"{lane} row content hash differs from its text or source transform"
            )
        declared_family = value.get("source_family")
        if (
            declared_family is not None
            and _required_text(declared_family, label=f"{lane} source family")
            != family_id
        ):
            raise ValueError(f"{lane} row source family is not authority-derived")
        token_ids = list(text.encode("utf-8")[:max_bytes])
        if not token_ids:
            raise ValueError(f"{lane} text produced no byte tokens")
        canonical.append(
            {
                "id": identity,
                "split": lane,
                "text": text,
                "source_family": family_id,
                "source_locator": locator,
                "source_authority_sha256": authority_sha256,
                "source_artifact_path": bound["source_path"],
                "source_artifact_sha256": bound["source_artifact_sha256"],
                "source_byte_start": bound["source_byte_start"],
                "source_byte_end": bound["source_byte_end"],
                "source_excerpt_sha256": bound["source_excerpt_sha256"],
                "text_transform": bound["text_transform"],
                "content_sha256": content_sha256,
                "token_ids": token_ids,
            }
        )

    missing = sorted(set(record_authorities) - seen_rows)
    if missing:
        raise ValueError(
            f"{lane} source authority has {len(missing)} unconsumed records"
        )
    if not canonical:
        raise ValueError(f"{lane} source lane is empty")
    receipt: dict[str, object] = {
        "lane": lane,
        "family_id": family_id,
        "authority_path": str(path),
        "authority_sha256": authority_sha256,
        "record_count": len(canonical),
        "source_paths": sorted(source_paths),
        "source_sha256s": sorted(source_sha256s),
        "content_sha256s": sorted(
            str(value["content_sha256"]) for value in record_authorities.values()
        ),
    }
    return canonical, receipt
