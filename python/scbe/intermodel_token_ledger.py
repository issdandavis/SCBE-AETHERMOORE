"""Byte-rooted token seams for exact intermodel and code/action matching.

The byte stream is the authority.  Bit, balanced-trit, Sacred Tongue, opcode,
lexical, BPE, and model-token rows are typed views attached to exact source
spans.  Different tokenizers meet by subdividing their spans into a common
minimal seam partition; they are never declared equivalent merely because
their display strings or embedding vectors are close.

The code bridge adds a second, explicitly weaker join.  Language-specific code
tokens remain bound to their source bytes while already-existing semantic
operation signatures may join equivalent operations across languages.  Those
joins are training/planning evidence only and carry no execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any, Literal, Mapping, Sequence

from python.scbe.bit_spine import BitSpine, trits_to_bytes
from python.scbe.ca_opcode_table import get_ca_opcode
from python.scbe.hex_trit_cross_router import hex_trit_cross_cell
from python.scbe.semantic_opcode_vm import OPCODE_TO_CONTRACT
from src.crypto.sacred_tongues import (
    SACRED_TONGUE_TOKENIZER,
    TOKENIZER_PROFILE_ID,
)
from src.tokenizer.code_weight_packets import (
    LANGUAGE_TONGUES,
    LEXICAL_TOKEN_RE,
    build_code_weight_packet,
    lexical_token_spans,
)
from src.tokenizer.semantic_code_bridge import semantic_atom_for_operation
from python.scbe.token_honeycomb_nest import (
    TokenNestInput,
    build_typed_token_honeycomb,
)

BINARY_ATLAS_SCHEMA = "scbe.binary-token-atlas.v2"
TOKEN_TRACE_SCHEMA = "scbe.model-token-span-trace.v1"
SEAM_LEDGER_SCHEMA = "scbe.intermodel-token-seam-ledger.v1"
CODE_LEDGER_SCHEMA = "scbe.code-token-intermodel-ledger.v1"
BYTE_TOKENIZER_PROFILE = "scbe.byte-tokenizer.v1"
CODE_TOKENIZER_PROFILE = "scbe.code-weight-lexical-tokenizer.v1"
TONGUE_ORDER = ("ko", "av", "ru", "ca", "um", "dr")
CODE_LANGUAGE_FACES_18 = (
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
)
CODE_LANGUAGE_ALIASES = {
    "c++": "cpp",
    "c#": "csharp",
    "js": "javascript",
    "ts": "typescript",
}
MAX_SOURCE_BYTES = 1_048_576
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class IntermodelTokenError(ValueError):
    """A token trace, binary projection, or join violated its exact contract."""


OffsetUnit = Literal["char", "byte"]
CoverageMode = Literal["full", "sparse"]


@dataclass(frozen=True, slots=True)
class CodeModelInput:
    """One model/language source surface for a cross-code operation join."""

    model_id: str
    language: str
    source: str
    source_name: str = ""

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id cannot be empty")
        if not self.language.strip():
            raise ValueError("language cannot be empty")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source must be nonempty text")


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _json_sha256(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def _typed_id_part(value: object) -> object:
    """Return a type-preserving JSON value for stable identity hashing."""

    if value is None:
        return {"type": "none", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IntermodelTokenError("stable IDs cannot contain non-finite floats")
        return {"type": "float", "value": value.hex()}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, bytes):
        return {"type": "bytes", "value": value.hex()}
    if isinstance(value, Mapping):
        entries = [
            (_typed_id_part(key), _typed_id_part(item)) for key, item in value.items()
        ]
        entries.sort(key=lambda pair: canonical_json(pair[0]))
        return {"type": "mapping", "value": entries}
    if isinstance(value, tuple):
        return {"type": "tuple", "value": [_typed_id_part(item) for item in value]}
    if isinstance(value, list):
        return {"type": "list", "value": [_typed_id_part(item) for item in value]}
    raise IntermodelTokenError(
        f"unsupported stable-ID component type: {type(value).__name__}"
    )


def _stable_id(namespace: str, *parts: object) -> str:
    payload = {
        "namespace": namespace,
        "parts": [_typed_id_part(part) for part in parts],
    }
    return sha256(canonical_json(payload)).hexdigest()


def _require_source(source: str) -> bytes:
    if not isinstance(source, str):
        raise TypeError("source must be text")
    raw = source.encode("utf-8")
    if len(raw) > MAX_SOURCE_BYTES:
        raise IntermodelTokenError(
            f"source exceeds bounded ledger limit of {MAX_SOURCE_BYTES} bytes"
        )
    return raw


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise IntermodelTokenError(f"{name} must be lowercase SHA-256")


def _char_byte_offsets(source: str) -> tuple[int, ...]:
    offsets = [0]
    for character in source:
        offsets.append(offsets[-1] + len(character.encode("utf-8")))
    return tuple(offsets)


def _coverage_summary(
    byte_count: int, token_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    spans = sorted(
        (
            (int(row["byte_start"]), int(row["byte_end"]))
            for row in token_rows
            if not row["special"]
        ),
        key=lambda span: (span[0], span[1]),
    )
    gaps: list[list[int]] = []
    cursor = 0
    covered = 0
    for start, end in spans:
        if start < cursor:
            raise IntermodelTokenError("positive token spans may not overlap")
        if start > cursor:
            gaps.append([cursor, start])
        covered += end - start
        cursor = end
    if cursor < byte_count:
        gaps.append([cursor, byte_count])
    return {
        "covered_bytes": covered,
        "source_bytes": byte_count,
        "coverage_ratio": 1.0 if byte_count == 0 else covered / byte_count,
        "gaps": gaps,
        "positive_span_count": len(spans),
        "special_token_count": sum(bool(row["special"]) for row in token_rows),
    }


def trace_from_offsets(
    source: str,
    *,
    model_id: str,
    tokenizer_id: str,
    tokenizer_fingerprint: str,
    token_ids: Sequence[int | str],
    offsets: Sequence[tuple[int, int]],
    offset_unit: OffsetUnit = "char",
    coverage_mode: CoverageMode = "full",
    surfaces: Sequence[str] | None = None,
    token_kinds: Sequence[str] | None = None,
    token_metadata: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind one tokenizer's IDs to exact source-byte spans.

    ``offsets`` must refer to the original unnormalized source.  Character
    offsets are converted to UTF-8 byte offsets.  Byte offsets may split a
    multi-byte character, which is valid for a byte-level tokenizer because the
    exact hex slice remains authoritative.
    """

    raw = _require_source(source)
    if not model_id.strip() or not tokenizer_id.strip():
        raise IntermodelTokenError("model_id and tokenizer_id cannot be empty")
    _require_sha256("tokenizer_fingerprint", tokenizer_fingerprint)
    if coverage_mode not in ("full", "sparse"):
        raise IntermodelTokenError("coverage_mode must be full or sparse")
    if offset_unit not in ("char", "byte"):
        raise IntermodelTokenError("offset_unit must be char or byte")
    count = len(token_ids)
    for name, values in (
        ("offsets", offsets),
        ("surfaces", surfaces),
        ("token_kinds", token_kinds),
        ("token_metadata", token_metadata),
    ):
        if values is not None and len(values) != count:
            raise IntermodelTokenError(f"{name} length does not match token_ids")

    char_bytes = _char_byte_offsets(source)
    source_sha256 = sha256(raw).hexdigest()
    rows: list[dict[str, Any]] = []
    last_positive_end = 0
    for index, (token_id, offset) in enumerate(zip(token_ids, offsets, strict=True)):
        if isinstance(token_id, bool) or not isinstance(token_id, (int, str)):
            raise IntermodelTokenError("token IDs must be integers or strings")
        if (
            not isinstance(offset, tuple)
            or len(offset) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in offset
            )
        ):
            raise IntermodelTokenError("each offset must be an integer pair")
        start, end = offset
        limit = len(source) if offset_unit == "char" else len(raw)
        if not 0 <= start <= end <= limit:
            raise IntermodelTokenError("token offset is outside the source")
        byte_start, byte_end = (
            (char_bytes[start], char_bytes[end])
            if offset_unit == "char"
            else (start, end)
        )
        special = byte_start == byte_end
        if not special and byte_start < last_positive_end:
            raise IntermodelTokenError("positive token spans must follow source order")
        if not special:
            last_positive_end = byte_end
        token_bytes = raw[byte_start:byte_end]
        surface = (
            str(surfaces[index])
            if surfaces is not None
            else token_bytes.decode("utf-8", errors="replace")
        )
        kind = str(token_kinds[index]) if token_kinds is not None else "model"
        metadata = dict(token_metadata[index]) if token_metadata is not None else {}
        span_id = _stable_id(
            "source-token-span",
            source_sha256,
            byte_start,
            byte_end,
            token_bytes.hex(),
        )
        rows.append(
            {
                "token_index": index,
                "token_id": token_id,
                "surface": surface,
                "kind": kind,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "byte_hex": token_bytes.hex(),
                "span_id": span_id,
                "special": special,
                "metadata": metadata,
            }
        )

    coverage = _coverage_summary(len(raw), rows)
    if coverage_mode == "full" and coverage["gaps"]:
        raise IntermodelTokenError(
            "full-coverage tokenizer left source bytes without a token span"
        )
    body = {
        "schema": TOKEN_TRACE_SCHEMA,
        "receipt_security": "unkeyed-corruption-detection-only",
        "model_id": model_id,
        "tokenizer_id": tokenizer_id,
        "tokenizer_fingerprint": tokenizer_fingerprint,
        "source_sha256": source_sha256,
        "source_byte_count": len(raw),
        "coverage_mode": coverage_mode,
        "coverage": coverage,
        "tokens": rows,
    }
    return {**body, "trace_sha256": _json_sha256(body)}


def _validate_trace(source: str, trace: Mapping[str, Any]) -> None:
    raw = _require_source(source)
    if not isinstance(trace, dict) or trace.get("schema") != TOKEN_TRACE_SCHEMA:
        raise IntermodelTokenError("invalid token trace schema")
    body = dict(trace)
    claimed = body.pop("trace_sha256", None)
    if claimed != _json_sha256(body):
        raise IntermodelTokenError("token trace receipt hash mismatch")
    if trace.get("source_sha256") != sha256(raw).hexdigest():
        raise IntermodelTokenError("token trace belongs to another source")
    if trace.get("source_byte_count") != len(raw):
        raise IntermodelTokenError("token trace byte count is invalid")
    _require_sha256("tokenizer_fingerprint", str(trace.get("tokenizer_fingerprint")))
    rows = trace.get("tokens")
    if not isinstance(rows, list):
        raise IntermodelTokenError("token trace rows must be a list")
    last_positive_end = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("token_index") != index:
            raise IntermodelTokenError("token trace indexes are not canonical")
        start, end = row.get("byte_start"), row.get("byte_end")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start <= end <= len(raw)
        ):
            raise IntermodelTokenError("token trace span is invalid")
        token_bytes = raw[start:end]
        if row.get("byte_hex") != token_bytes.hex():
            raise IntermodelTokenError("token trace byte slice drifted")
        if row.get("special") is not (start == end):
            raise IntermodelTokenError("token special/span state is inconsistent")
        if start != end and start < last_positive_end:
            raise IntermodelTokenError("positive token spans must follow source order")
        if start != end:
            last_positive_end = end
        expected_span_id = _stable_id(
            "source-token-span", trace["source_sha256"], start, end, token_bytes.hex()
        )
        if row.get("span_id") != expected_span_id:
            raise IntermodelTokenError("token span identity drifted")
    coverage = _coverage_summary(len(raw), rows)
    if trace.get("coverage") != coverage:
        raise IntermodelTokenError("token trace coverage summary drifted")
    if trace.get("coverage_mode") == "full" and coverage["gaps"]:
        raise IntermodelTokenError("full trace contains gaps")


def verify_model_token_trace(
    source: str,
    trace: Mapping[str, Any],
    *,
    expected_model_id: str | None = None,
    expected_tokenizer_id: str | None = None,
    expected_tokenizer_fingerprint: str | None = None,
) -> bool:
    """Verify receipt integrity and, when supplied, expected trace authority.

    The embedded SHA-256 is unkeyed corruption detection.  It is not a MAC or
    signature, so callers crossing a trust boundary should also pin the model,
    tokenizer, and tokenizer fingerprint here.
    """

    try:
        _validate_trace(source, trace)
        expected = (
            ("model_id", expected_model_id),
            ("tokenizer_id", expected_tokenizer_id),
            ("tokenizer_fingerprint", expected_tokenizer_fingerprint),
        )
        if expected_tokenizer_fingerprint is not None:
            _require_sha256(
                "expected_tokenizer_fingerprint", expected_tokenizer_fingerprint
            )
        if any(
            value is not None and trace.get(key) != value for key, value in expected
        ):
            raise IntermodelTokenError(
                "token trace authority does not match expectation"
            )
    except (IntermodelTokenError, TypeError, ValueError, KeyError):
        return False
    return True


def _token_nest_id(trace: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    return _stable_id(
        "typed-token-nest-member",
        trace["model_id"],
        trace["tokenizer_fingerprint"],
        row["token_index"],
        row["span_id"],
        row["token_id"],
    )


def _token_nest_inputs(
    traces: Sequence[Mapping[str, Any]],
) -> tuple[list[TokenNestInput], dict[tuple[str, int], str]]:
    rows: list[TokenNestInput] = []
    member_ids: dict[tuple[str, int], str] = {}
    sequence_index = 0
    for trace in traces:
        model_id = str(trace["model_id"])
        for token in trace["tokens"]:
            if token["special"]:
                continue
            canonical_id = _token_nest_id(trace, token)
            member_ids[(model_id, int(token["token_index"]))] = canonical_id
            rows.append(
                TokenNestInput(
                    canonical_id=canonical_id,
                    family=str(token["kind"]),
                    byte_hex=str(token["byte_hex"]),
                    sequence_index=sequence_index,
                    label=str(token["surface"]),
                    source_id=model_id,
                )
            )
            sequence_index += 1
    return rows, member_ids


def _code_face(language: str) -> dict[str, Any]:
    normalized = CODE_LANGUAGE_ALIASES.get(language.casefold(), language.casefold())
    face_index = (
        CODE_LANGUAGE_FACES_18.index(normalized)
        if normalized in CODE_LANGUAGE_FACES_18
        else None
    )
    return {
        "language": normalized,
        "face_index": face_index,
        "face_count": len(CODE_LANGUAGE_FACES_18),
        "support_state": (
            "DECLARED_LEGACY_FACE"
            if face_index is not None
            else "OUTSIDE_LEGACY_FACE_AXIS"
        ),
        "runtime_execution_proven_here": False,
    }


def trace_byte_tokenizer(source: str, *, model_id: str = "byte-root") -> dict[str, Any]:
    """Build the canonical one-token-per-byte model trace."""

    raw = _require_source(source)
    fingerprint = _json_sha256(
        {"profile": BYTE_TOKENIZER_PROFILE, "vocabulary": list(range(256))}
    )
    return trace_from_offsets(
        source,
        model_id=model_id,
        tokenizer_id=BYTE_TOKENIZER_PROFILE,
        tokenizer_fingerprint=fingerprint,
        token_ids=list(raw),
        offsets=[(index, index + 1) for index in range(len(raw))],
        offset_unit="byte",
        coverage_mode="full",
        surfaces=[f"0x{value:02X}" for value in raw],
        token_kinds=["byte"] * len(raw),
    )


def trace_sacred_tongue(
    source: str, *, tongue: str, model_id: str | None = None
) -> dict[str, Any]:
    """Build one exact one-token-per-byte Six Tongues trace."""

    raw = _require_source(source)
    code = tongue.casefold()
    if code not in TONGUE_ORDER:
        raise IntermodelTokenError(f"unknown tongue: {tongue}")
    table = SACRED_TONGUE_TOKENIZER.byte_to_token[code]
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(code, raw)
    fingerprint = _json_sha256(
        {
            "profile": TOKENIZER_PROFILE_ID,
            "tongue": code,
            "byte_to_token": table,
        }
    )
    return trace_from_offsets(
        source,
        model_id=model_id or f"six-tongues:{code}",
        tokenizer_id=f"{TOKENIZER_PROFILE_ID}:{code}",
        tokenizer_fingerprint=fingerprint,
        token_ids=[f"{code}:{token}" for token in tokens],
        offsets=[(index, index + 1) for index in range(len(raw))],
        offset_unit="byte",
        coverage_mode="full",
        surfaces=tokens,
        token_kinds=["six_tongues"] * len(raw),
        token_metadata=[{"tongue": code, "byte_value": value} for value in raw],
    )


def trace_code_lexical(source: str, *, model_id: str, language: str) -> dict[str, Any]:
    """Trace the exact lexical tokens used by the semantic code signature."""

    spans = lexical_token_spans(source)
    fingerprint = _json_sha256(
        {
            "profile": CODE_TOKENIZER_PROFILE,
            "pattern": LEXICAL_TOKEN_RE.pattern,
            "flags": LEXICAL_TOKEN_RE.flags,
        }
    )
    return trace_from_offsets(
        source,
        model_id=model_id,
        tokenizer_id=f"{CODE_TOKENIZER_PROFILE}:{language.casefold()}",
        tokenizer_fingerprint=fingerprint,
        token_ids=[row["token"] for row in spans],
        offsets=[(row["byte_start"], row["byte_end"]) for row in spans],
        offset_unit="byte",
        coverage_mode="sparse",
        surfaces=[row["token"] for row in spans],
        token_kinds=[row["role"] for row in spans],
        token_metadata=[{"deed_id": row["deed_id"]} for row in spans],
    )


def build_binary_token_atlas(data: bytes) -> dict[str, Any]:
    """Attach existing exact binary/token views to unique byte roots.

    Byte types are stored once and source occurrences reference them.  This
    avoids repeating the six tongue strings for every occurrence while keeping
    a source-specific immutable deed for each position.
    """

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if len(data) > MAX_SOURCE_BYTES:
        raise IntermodelTokenError("binary atlas exceeds bounded source limit")
    source_sha256 = sha256(data).hexdigest()
    type_rows: list[dict[str, Any]] = []
    for value in sorted(set(data)):
        one = bytes([value])
        spine = BitSpine(one)
        trits = spine.trits()
        if trits_to_bytes(trits) != one:
            raise AssertionError("balanced-trit byte round trip failed")
        tongue_tokens = {
            code: SACRED_TONGUE_TOKENIZER.encode_bytes(code, one)[0]
            for code in TONGUE_ORDER
        }
        for code, token in tongue_tokens.items():
            if SACRED_TONGUE_TOKENIZER.decode_tokens(code, [token]) != one:
                raise AssertionError("Six Tongues byte round trip failed")

        # Two existing exact factorizations are retained as named profiles.
        # They are transposes of the same 256 states and must not be conflated.
        cube_cell, cube_orientation = value >> 2, value & 0x03
        region_opcode, region_orientation = value & 0x3F, value >> 6
        if (cube_cell << 2) | cube_orientation != value:
            raise AssertionError("cube-face byte factorization failed")
        if (region_orientation << 6) | region_opcode != value:
            raise AssertionError("opcode-region byte factorization failed")
        ca_entry = get_ca_opcode(region_opcode)
        vm_contract = OPCODE_TO_CONTRACT.get(value)
        body: dict[str, Any] = {
            "byte_type_id": f"b256:{value:02x}",
            "byte_value": value,
            "hex": f"{value:02x}",
            "bits_msb_first": spine.bits(),
            "balanced_trits": trits,
            "hex_trit_cross_column": hex_trit_cross_cell(value),
            "six_tongues": tongue_tokens,
            "wafer_profiles": {
                "cube-face-byte-v1": {
                    "cell": cube_cell,
                    "orientation": cube_orientation,
                    "inverse": "(cell << 2) | orientation",
                },
                "ca-opcode-region-v1": {
                    "opcode": region_opcode,
                    "orientation": region_orientation,
                    "opcode_name": ca_entry.name,
                    "inverse": "(orientation << 6) | opcode",
                },
            },
            "semantic_vm_contract": (
                None
                if vm_contract is None
                else {
                    "token": vm_contract.token,
                    "opcode": vm_contract.opcode,
                    "family": vm_contract.family,
                    "verification_rule": vm_contract.verification_rule,
                }
            ),
        }
        type_rows.append({**body, "type_sha256": _json_sha256(body)})

    occurrences = [
        {
            "byte_offset": offset,
            "byte_type_id": f"b256:{value:02x}",
            "deed_id": _stable_id("byte-deed", source_sha256, offset, f"{value:02x}"),
        }
        for offset, value in enumerate(data)
    ]
    body = {
        "schema": BINARY_ATLAS_SCHEMA,
        "source_sha256": source_sha256,
        "source_byte_count": len(data),
        "byte_type_count": len(type_rows),
        "byte_types": type_rows,
        "occurrences": occurrences,
        "view_contract": {
            "canonical_identity": "source_sha256_plus_byte_offset",
            "deterministic_views_are_correlated": True,
            "independent_evidence_count": 1,
            "execution_authority": False,
        },
    }
    return {**body, "atlas_sha256": _json_sha256(body)}


def verify_binary_token_atlas(data: bytes, atlas: Mapping[str, Any]) -> bool:
    try:
        return dict(atlas) == build_binary_token_atlas(data)
    except (IntermodelTokenError, TypeError, ValueError, KeyError):
        return False


def _interval_intersection_length(
    left: Sequence[tuple[int, int]], right: Sequence[tuple[int, int]]
) -> int:
    i = j = total = 0
    while i < len(left) and j < len(right):
        start = max(left[i][0], right[j][0])
        end = min(left[i][1], right[j][1])
        if start < end:
            total += end - start
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return total


def build_intermodel_seam_ledger(
    source: str, traces: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Partition source bytes at every model boundary and join token members."""

    raw = _require_source(source)
    if len(traces) < 2:
        raise IntermodelTokenError("an intermodel ledger needs at least two traces")
    for trace in traces:
        _validate_trace(source, trace)
    model_ids = [str(trace["model_id"]) for trace in traces]
    if len(set(model_ids)) != len(model_ids):
        raise IntermodelTokenError("model_id values must be unique within a ledger")

    boundaries = {0, len(raw)}
    positive: dict[str, list[dict[str, Any]]] = {}
    exact_groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for trace in traces:
        model_id = str(trace["model_id"])
        rows = [dict(row) for row in trace["tokens"] if not row["special"]]
        positive[model_id] = rows
        for row in rows:
            start, end = int(row["byte_start"]), int(row["byte_end"])
            boundaries.update((start, end))
            exact_groups.setdefault((start, end), []).append(
                {
                    "model_id": model_id,
                    "token_index": row["token_index"],
                    "token_id": row["token_id"],
                    "span_id": row["span_id"],
                }
            )

    ordered = sorted(boundaries)
    pointers = {model_id: 0 for model_id in model_ids}
    atlas = build_binary_token_atlas(raw)
    deed_ids = [row["deed_id"] for row in atlas["occurrences"]]
    seams: list[dict[str, Any]] = []
    for seam_index, (start, end) in enumerate(zip(ordered, ordered[1:])):
        if start == end:
            continue
        memberships: list[dict[str, Any]] = []
        for model_id in model_ids:
            rows = positive[model_id]
            pointer = pointers[model_id]
            while pointer < len(rows) and int(rows[pointer]["byte_end"]) <= start:
                pointer += 1
            pointers[model_id] = pointer
            if pointer >= len(rows):
                continue
            row = rows[pointer]
            if int(row["byte_start"]) <= start and int(row["byte_end"]) >= end:
                memberships.append(
                    {
                        "model_id": model_id,
                        "token_index": row["token_index"],
                        "token_id": row["token_id"],
                        "token_span_id": row["span_id"],
                        "token_exactly_equals_seam": (
                            int(row["byte_start"]) == start
                            and int(row["byte_end"]) == end
                        ),
                    }
                )
        seam_bytes = raw[start:end]
        seam_body = {
            "seam_index": seam_index,
            "byte_start": start,
            "byte_end": end,
            "byte_hex": seam_bytes.hex(),
            "byte_deed_ids": deed_ids[start:end],
            "memberships": memberships,
            "membership_state": "PRESENT" if memberships else "UNOBSERVED",
        }
        seams.append(
            {
                **seam_body,
                "seam_id": _stable_id(
                    "intermodel-seam",
                    sha256(raw).hexdigest(),
                    start,
                    end,
                    seam_bytes.hex(),
                ),
            }
        )

    exact_span_matches = [
        {
            "byte_start": start,
            "byte_end": end,
            "byte_hex": raw[start:end].hex(),
            "memberships": members,
        }
        for (start, end), members in sorted(exact_groups.items())
        if len({member["model_id"] for member in members}) > 1
    ]
    pairwise: list[dict[str, Any]] = []
    intervals = {
        model_id: [
            (int(row["byte_start"]), int(row["byte_end"])) for row in positive[model_id]
        ]
        for model_id in model_ids
    }
    for left_index, left in enumerate(model_ids):
        for right in model_ids[left_index + 1 :]:
            shared_bytes = _interval_intersection_length(
                intervals[left], intervals[right]
            )
            exact_count = sum(
                {left, right}.issubset(
                    {member["model_id"] for member in row["memberships"]}
                )
                for row in exact_span_matches
            )
            shared_seams = sum(
                {left, right}.issubset(
                    {member["model_id"] for member in seam["memberships"]}
                )
                for seam in seams
            )
            pairwise.append(
                {
                    "left_model": left,
                    "right_model": right,
                    "shared_byte_count": shared_bytes,
                    "shared_byte_ratio": (1.0 if not raw else shared_bytes / len(raw)),
                    "exact_span_match_count": exact_count,
                    "shared_seam_count": shared_seams,
                    "segmentation_identical": intervals[left] == intervals[right],
                }
            )

    nest_inputs, _nest_member_ids = _token_nest_inputs(traces)
    token_nest = build_typed_token_honeycomb(nest_inputs) if nest_inputs else None

    body = {
        "schema": SEAM_LEDGER_SCHEMA,
        "source_sha256": sha256(raw).hexdigest(),
        "source_byte_count": len(raw),
        "model_count": len(traces),
        "models": [
            {
                "model_id": trace["model_id"],
                "tokenizer_id": trace["tokenizer_id"],
                "tokenizer_fingerprint": trace["tokenizer_fingerprint"],
                "trace_sha256": trace["trace_sha256"],
                "coverage": trace["coverage"],
            }
            for trace in traces
        ],
        "binary_atlas": atlas,
        "token_nest": token_nest,
        "seams": seams,
        "exact_span_matches": exact_span_matches,
        "pairwise": pairwise,
        "metrics": {
            "seam_count": len(seams),
            "unobserved_seam_count": sum(
                seam["membership_state"] == "UNOBSERVED" for seam in seams
            ),
            "fully_shared_seam_count": sum(
                len({member["model_id"] for member in seam["memberships"]})
                == len(traces)
                for seam in seams
            ),
            "maximum_models_on_one_seam": max(
                (
                    len({member["model_id"] for member in seam["memberships"]})
                    for seam in seams
                ),
                default=0,
            ),
            "nested_token_count": (
                0 if token_nest is None else token_nest["metrics"]["token_count"]
            ),
            "nested_address_collision_count": (
                0
                if token_nest is None
                else token_nest["metrics"]["nested_address_collision_count"]
            ),
        },
        "claim_boundary": {
            "exact_shared_bytes_are_proven": True,
            "shared_semantics_are_not_inferred_from_overlap": True,
            "deterministic_views_are_correlated": True,
            "honeycomb_similarity_is_a_routing_hint": True,
            "execution_authority": False,
        },
    }
    return {**body, "ledger_sha256": _json_sha256(body)}


def verify_intermodel_seam_ledger(
    source: str,
    traces: Sequence[Mapping[str, Any]],
    ledger: Mapping[str, Any],
) -> bool:
    try:
        return dict(ledger) == build_intermodel_seam_ledger(source, traces)
    except (IntermodelTokenError, TypeError, ValueError, KeyError):
        return False


def build_code_intermodel_ledger(
    inputs: Sequence[CodeModelInput],
) -> dict[str, Any]:
    """Join code tokens through exact bytes and shared operation signatures."""

    if len(inputs) < 2:
        raise IntermodelTokenError("a code intermodel ledger needs at least two inputs")
    if len({item.model_id for item in inputs}) != len(inputs):
        raise IntermodelTokenError("code model IDs must be unique")

    source_rows: list[dict[str, Any]] = []
    signatures: dict[str, dict[str, Any]] = {}
    lexical_traces: dict[str, dict[str, Any]] = {}
    for item in inputs:
        packet = build_code_weight_packet(
            item.source,
            language=item.language,
            source_name=item.source_name or item.model_id,
        )
        signature = packet["semantic_operation_signature"]
        lexical = trace_code_lexical(
            item.source, model_id=f"{item.model_id}:code", language=item.language
        )
        if not lexical["tokens"]:
            raise IntermodelTokenError(
                f"code input {item.model_id!r} contains no lexical tokens"
            )
        tongue = LANGUAGE_TONGUES.get(item.language.casefold(), "KO").casefold()
        byte_trace = trace_byte_tokenizer(item.source, model_id=f"{item.model_id}:byte")
        tongue_trace = trace_sacred_tongue(
            item.source,
            tongue=tongue,
            model_id=f"{item.model_id}:tongue:{tongue}",
        )
        source_ledger = build_intermodel_seam_ledger(
            item.source, (byte_trace, tongue_trace, lexical)
        )
        signatures[item.model_id] = signature
        lexical_traces[item.model_id] = lexical
        source_rows.append(
            {
                "model_id": item.model_id,
                "language": item.language,
                "source_name": item.source_name or item.model_id,
                "source_sha256": packet["source_sha256"],
                "code_face": _code_face(item.language),
                "transport_tongue": packet["transport"]["tongue"],
                "transport_token_sha256": packet["transport"]["token_sha256"],
                "operation_signature": signature,
                "source_seam_ledger": source_ledger,
            }
        )

    cross_nest_inputs, cross_nest_member_ids = _token_nest_inputs(
        [lexical_traces[item.model_id] for item in inputs]
    )
    cross_code_token_nest = build_typed_token_honeycomb(cross_nest_inputs)

    keys = {signature["interchange_key"] for signature in signatures.values()}
    paths = {tuple(signature["operation_path"]) for signature in signatures.values()}
    aligned = len(keys) == 1 and len(paths) == 1
    action_cells: list[dict[str, Any]] = []
    if aligned:
        interchange_key = next(iter(keys))
        operation_path = next(iter(paths))
        for operation_index, operation in enumerate(operation_path):
            bindings: list[dict[str, Any]] = []
            for item in inputs:
                signature = signatures[item.model_id]
                atoms = signature["operation_atoms"]
                if operation_index >= len(atoms):
                    raise IntermodelTokenError(
                        "operation path and atom ledger diverged"
                    )
                atom = atoms[operation_index]
                token_index = atom.get("token_index")
                if (
                    isinstance(token_index, bool)
                    or not isinstance(token_index, int)
                    or not 0
                    <= token_index
                    < len(lexical_traces[item.model_id]["tokens"])
                ):
                    raise IntermodelTokenError(
                        "operation atom lacks an exact lexical token binding"
                    )
                token = lexical_traces[item.model_id]["tokens"][token_index]
                nest_member_id = cross_nest_member_ids[
                    (str(lexical_traces[item.model_id]["model_id"]), token_index)
                ]
                bindings.append(
                    {
                        "model_id": item.model_id,
                        "language": item.language,
                        "token_index": token_index,
                        "token_id": token["token_id"],
                        "surface": token["surface"],
                        "byte_start": token["byte_start"],
                        "byte_end": token["byte_end"],
                        "byte_hex": token["byte_hex"],
                        "source_span_id": token["span_id"],
                        "token_nest_id": nest_member_id,
                        "binding_id": _stable_id(
                            "code-operation-binding",
                            interchange_key,
                            operation_index,
                            item.model_id,
                            token["span_id"],
                        ),
                    }
                )
            cell_body = {
                "operation_index": operation_index,
                "operation": operation,
                "semantic_atom": semantic_atom_for_operation(operation),
                "bindings": bindings,
            }
            action_cells.append(
                {
                    **cell_body,
                    "operation_id": _stable_id(
                        "intermodel-operation",
                        interchange_key,
                        operation_index,
                        operation,
                    ),
                }
            )

    binding_count = sum(len(cell["bindings"]) for cell in action_cells)
    body = {
        "schema": CODE_LEDGER_SCHEMA,
        "model_count": len(inputs),
        "aligned": aligned,
        "interchange_keys": sorted(keys),
        "operation_paths": [list(path) for path in sorted(paths)],
        "code_face_axis": list(CODE_LANGUAGE_FACES_18),
        "sources": source_rows,
        "cross_code_token_nest": cross_code_token_nest,
        "action_cells": action_cells,
        "metrics": {
            "action_cell_count": len(action_cells),
            "binding_count": binding_count,
            "all_bindings_byte_exact": bool(binding_count)
            and all(
                bool(binding["byte_hex"])
                for cell in action_cells
                for binding in cell["bindings"]
            ),
            "source_byte_count": sum(
                row["source_seam_ledger"]["source_byte_count"] for row in source_rows
            ),
            "token_seam_count": sum(
                row["source_seam_ledger"]["metrics"]["seam_count"]
                for row in source_rows
            ),
            "cross_code_nested_token_count": cross_code_token_nest["metrics"][
                "token_count"
            ],
            "cross_code_nested_address_collision_count": cross_code_token_nest[
                "metrics"
            ]["nested_address_collision_count"],
        },
        "authority": {
            "training_intake": "NOT_AUTHORIZED",
            "execution": "NOT_AUTHORIZED",
            "merge": "NOT_AUTHORIZED",
            "promotion": "NOT_AUTHORIZED",
        },
        "claim_boundary": {
            "same_source_token_matches_use_exact_bytes": True,
            "cross_language_matches_require_equal_operation_signature": True,
            "operation_signature_is_not_program_equivalence_proof": True,
            "code_faces_are_support_addresses_not_runtime_proof": True,
            "token_nest_similarity_is_not_execution_authority": True,
            "compiler_and_governance_remain_external": True,
        },
    }
    return {**body, "ledger_sha256": _json_sha256(body)}


def verify_code_intermodel_ledger(
    inputs: Sequence[CodeModelInput], ledger: Mapping[str, Any]
) -> bool:
    try:
        return dict(ledger) == build_code_intermodel_ledger(inputs)
    except (IntermodelTokenError, TypeError, ValueError, KeyError):
        return False


__all__ = [
    "BINARY_ATLAS_SCHEMA",
    "CODE_LEDGER_SCHEMA",
    "CODE_LANGUAGE_FACES_18",
    "CodeModelInput",
    "IntermodelTokenError",
    "SEAM_LEDGER_SCHEMA",
    "TOKEN_TRACE_SCHEMA",
    "build_binary_token_atlas",
    "build_code_intermodel_ledger",
    "build_intermodel_seam_ledger",
    "canonical_json",
    "trace_byte_tokenizer",
    "trace_code_lexical",
    "trace_from_offsets",
    "trace_sacred_tongue",
    "verify_binary_token_atlas",
    "verify_code_intermodel_ledger",
    "verify_intermodel_seam_ledger",
    "verify_model_token_trace",
]
