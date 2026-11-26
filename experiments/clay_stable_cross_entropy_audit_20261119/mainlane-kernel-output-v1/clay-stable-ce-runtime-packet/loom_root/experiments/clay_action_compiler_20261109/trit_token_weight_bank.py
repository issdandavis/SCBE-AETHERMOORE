"""Token-derived ternary weights and exact routing diagnostics.

The base bank is not randomly initialized.  Every row is algebraically derived
from a canonical transport byte, balanced-trit token coordinates, radial phase,
and a Six-Tongue view index.  The resulting weights are in ``{-1, 0, +1}`` and
are immutable.  Future training may learn a separately sealed residual, but it
must not rewrite the canonical bank or the token registry.

This module also records source-family provenance.  A local patent draft is not
silently treated as filed claim text; callers receive the exact path, hash, and
declared evidence class for each source used by a manifest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

from action_compiler import TONGUE_ORDER, radial_power_weight
from developmental_game_sandbox import ACTION_BYTES, ACTION_NAMES


SCHEMA = "clay.trit-token-weight-bank.v1"
RELATION_SCHEMA = "clay.trit-token-relation-graph.v1"
TONGUES = tuple(TONGUE_ORDER)
DEFAULT_PATENT_DRAFT = Path(
    r"C:\Users\issda\SCBE-AETHERMOORE\symphonic_cipher\scbe_aethermoore\PATENT_SPECIFICATION.md"
)
DEFAULT_PATENT_AUDIT = Path(r"C:\dev\clay-architecture-book-v2\manuscript\09_patent_audit.md")
DEFAULT_TOKEN_REFERENCE = Path(
    r"C:\Users\issda\SCBE-AETHERMOORE\notes\System Library\Indexes\Tokenizer Sacred Eggs Canonical Reference.md"
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def balanced_trits(value: int, width: int) -> tuple[int, ...]:
    if value < 0 or width < 1:
        raise ValueError("balanced-trit input must be non-negative with positive width")
    result: list[int] = []
    carry = value
    for _ in range(width):
        carry, digit = divmod(carry, 3)
        if digit == 2:
            digit = -1
            carry += 1
        result.append(digit)
    if carry:
        raise ValueError("balanced-trit width is too small for value")
    return tuple(result)


def _trit_mod(value: int) -> int:
    return {0: 0, 1: 1, 2: -1}[value % 3]


@dataclass(frozen=True, slots=True)
class SourceReceipt:
    source_id: str
    path: str
    sha256: str
    evidence_class: str
    use: str


def default_source_receipts() -> tuple[SourceReceipt, ...]:
    declared = (
        (
            "LOCAL-PATENT-DRAFT",
            DEFAULT_PATENT_DRAFT,
            "engineering draft; not asserted to be exact filed claim bytes",
            "phase/geodesic coefficient lineage only",
        ),
        (
            "ARCHITECTURE-PATENT-AUDIT",
            DEFAULT_PATENT_AUDIT,
            "internal source-family audit",
            "claim-family and evidence-boundary guardrail",
        ),
        (
            "TOKENIZER-CANONICAL-REFERENCE",
            DEFAULT_TOKEN_REFERENCE,
            "local canonical design reference",
            "byte/trit/token identity lineage",
        ),
    )
    receipts: list[SourceReceipt] = []
    for source_id, path, evidence_class, use in declared:
        if path.is_file():
            receipts.append(SourceReceipt(source_id, str(path), file_sha256(path), evidence_class, use))
    return tuple(receipts)


@dataclass(frozen=True, slots=True)
class CanonicalToken:
    family: str
    name: str
    token_id: int
    transport_byte: int
    method_trits: tuple[int, int, int]
    phase_numerator: int
    phase_denominator: int
    power_residue: int

    def __post_init__(self) -> None:
        if not self.family or not self.name:
            raise ValueError("canonical token family/name cannot be empty")
        if self.token_id < 0 or not 0 <= self.transport_byte <= 255:
            raise ValueError("canonical token id/byte is outside its bounded range")
        if len(self.method_trits) != 3 or any(value not in {-1, 0, 1} for value in self.method_trits):
            raise ValueError("canonical token needs exactly three balanced method trits")
        if self.phase_denominator < 1 or not 0 <= self.phase_numerator < self.phase_denominator:
            raise ValueError("canonical token phase lies outside its ring")


def developmental_action_tokens() -> tuple[CanonicalToken, ...]:
    result = []
    for token_id, (name, transport_byte) in enumerate(zip(ACTION_NAMES, ACTION_BYTES)):
        row = radial_power_weight(token_id, len(ACTION_NAMES))
        result.append(
            CanonicalToken(
                family="developmental-action",
                name=name,
                token_id=token_id,
                transport_byte=transport_byte,
                method_trits=row.trits,
                phase_numerator=row.phase_numerator,
                phase_denominator=row.phase_denominator,
                power_residue=row.power_residue,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class WeightRow:
    row_id: str
    family: str
    token_name: str
    token_id: int
    transport_byte: int
    tongue: str
    tongue_index: int
    weights: tuple[int, ...]
    base_features: tuple[int, ...]
    row_sha256: str


@dataclass(frozen=True, slots=True)
class TokenWeightBank:
    width: int
    rows: tuple[WeightRow, ...]
    sources: tuple[SourceReceipt, ...]
    bank_sha256: str

    def row(self, family: str, token_id: int, tongue: str) -> WeightRow:
        for value in self.rows:
            if value.family == family and value.token_id == token_id and value.tongue == tongue:
                return value
        raise KeyError((family, token_id, tongue))

    def verify(self) -> bool:
        if self.width < 8 or not self.rows:
            return False
        for row in self.rows:
            body = {
                "row_id": row.row_id,
                "family": row.family,
                "token_name": row.token_name,
                "token_id": row.token_id,
                "transport_byte": row.transport_byte,
                "tongue": row.tongue,
                "tongue_index": row.tongue_index,
                "weights": row.weights,
                "base_features": row.base_features,
            }
            if (
                len(row.weights) != self.width
                or any(value not in {-1, 0, 1} for value in row.weights)
                or row.row_sha256 != sha256_json(body)
            ):
                return False
        manifest = {
            "schema": SCHEMA,
            "width": self.width,
            "rows": [asdict(row) for row in self.rows],
            "sources": [asdict(source) for source in self.sources],
            "derivation": "signed-byte-bits + balanced-byte-trits + method-trits + phase-trits + tongue-trits -> cyclic ternary convolution",
        }
        return self.bank_sha256 == sha256_json(manifest)


def _base_features(token: CanonicalToken, tongue_index: int) -> tuple[int, ...]:
    signed_bits = tuple(1 if token.transport_byte & (1 << bit) else -1 for bit in range(8))
    byte_trits = balanced_trits(token.transport_byte, 6)
    phase_trits = balanced_trits(token.phase_numerator, 3)
    residue_trits = balanced_trits(token.power_residue, 7)
    tongue_trits = balanced_trits(tongue_index, 3)
    return (
        *signed_bits,
        *byte_trits,
        *token.method_trits,
        *phase_trits,
        *residue_trits,
        *tongue_trits,
    )


def _expand_weights(base: tuple[int, ...], *, width: int, token_id: int, tongue_index: int) -> tuple[int, ...]:
    if width < 8:
        raise ValueError("weight width must be at least eight")
    # Six Tongues are reversible views of one canonical token, not six new
    # facts.  Keep three quarters of every row tongue-invariant and confine the
    # view-specific modulation to a declared overlay.
    core = base[:-3]
    tongue = base[-3:]
    size = len(core)
    core_width = max(1, 3 * width // 4)
    weights: list[int] = []
    for column in range(width):
        left = core[column % size]
        right = core[(3 * column + token_id + 1) % size]
        diagonal = core[(5 * column + token_id + 1) % size]
        phase = core[(column + 2 * token_id + 1) % size]
        if column < core_width:
            weights.append(_trit_mod(left + right - diagonal + phase))
        else:
            view = tongue[(column - core_width) % len(tongue)]
            weights.append(_trit_mod(left + right - diagonal + phase + view))
    return tuple(weights)


def build_weight_bank(
    tokens: Iterable[CanonicalToken] | None = None,
    *,
    width: int = 64,
    sources: Iterable[SourceReceipt] | None = None,
) -> TokenWeightBank:
    canonical_tokens = tuple(tokens if tokens is not None else developmental_action_tokens())
    if not canonical_tokens:
        raise ValueError("weight bank needs at least one canonical token")
    token_keys = [(token.family, token.token_id) for token in canonical_tokens]
    if len(set(token_keys)) != len(token_keys):
        raise ValueError("canonical token family/id pairs must be unique")
    rows: list[WeightRow] = []
    for token in sorted(canonical_tokens, key=lambda value: (value.family, value.token_id)):
        for tongue_index, tongue in enumerate(TONGUES):
            base = _base_features(token, tongue_index)
            weights = _expand_weights(base, width=width, token_id=token.token_id, tongue_index=tongue_index)
            row_id = f"{token.family}:{token.token_id}:{tongue}"
            body = {
                "row_id": row_id,
                "family": token.family,
                "token_name": token.name,
                "token_id": token.token_id,
                "transport_byte": token.transport_byte,
                "tongue": tongue,
                "tongue_index": tongue_index,
                "weights": weights,
                "base_features": base,
            }
            rows.append(WeightRow(**body, row_sha256=sha256_json(body)))
    source_rows = tuple(sources if sources is not None else default_source_receipts())
    manifest = {
        "schema": SCHEMA,
        "width": width,
        "rows": [asdict(row) for row in rows],
        "sources": [asdict(source) for source in source_rows],
        "derivation": "signed-byte-bits + balanced-byte-trits + method-trits + phase-trits + tongue-trits -> cyclic ternary convolution",
    }
    return TokenWeightBank(width, tuple(rows), source_rows, sha256_json(manifest))


@dataclass(frozen=True, slots=True)
class RelationEdge:
    source_row_id: str
    target_row_id: str
    weighted_distance: str
    cosine_similarity: float
    same_canonical_token: bool


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _token_distance(left: WeightRow, right: WeightRow) -> Fraction:
    """Exact draft-lineage distance with coefficients 2, 1.5, 1, 0.5.

    The factors are represented after multiplying through by two: 4,3,2,1.
    This is an engineering feature derived from the local draft specification,
    not a statement about patent scope or validity.
    """

    byte_hamming = sum(
        ((left.transport_byte >> bit) & 1) != ((right.transport_byte >> bit) & 1)
        for bit in range(8)
    )
    feature_hamming = sum(a != b for a, b in zip(left.base_features, right.base_features))
    token_gap = abs(left.token_id - right.token_id)
    tongue_gap = abs(left.tongue_index - right.tongue_index)
    tongue_gap = min(tongue_gap, len(TONGUES) - tongue_gap)
    return (
        4 * Fraction(byte_hamming, 8) ** 2
        + 3 * Fraction(feature_hamming, len(left.base_features)) ** 2
        + 2 * Fraction(token_gap, max(1, len(ACTION_NAMES) - 1)) ** 2
        + Fraction(tongue_gap, len(TONGUES) // 2) ** 2
    )


def _cosine(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def relation_graph(bank: TokenWeightBank, *, neighbors: int = 3) -> tuple[RelationEdge, ...]:
    if not bank.verify():
        raise ValueError("cannot derive relations from an invalid weight bank")
    if neighbors < 1:
        raise ValueError("relation graph needs at least one neighbor")
    result: list[RelationEdge] = []
    for source in bank.rows:
        candidates = []
        for target in bank.rows:
            if source.row_id == target.row_id:
                continue
            distance = _token_distance(source, target)
            similarity = _cosine(source.weights, target.weights)
            candidates.append((distance, -similarity, target.row_id, target, similarity))
        for distance, _, _, target, similarity in sorted(candidates)[:neighbors]:
            result.append(
                RelationEdge(
                    source.row_id,
                    target.row_id,
                    _fraction_text(distance),
                    similarity,
                    source.family == target.family and source.token_id == target.token_id,
                )
            )
    return tuple(result)


def route_weight_vector(bank: TokenWeightBank, vector: Iterable[int]) -> tuple[WeightRow, int]:
    """Route a ternary vector to the maximum-dot row with exact tie breaking."""

    values = tuple(int(value) for value in vector)
    if len(values) != bank.width or any(value not in {-1, 0, 1} for value in values):
        raise ValueError("routing vector must match the ternary bank width")
    scored = [
        (sum(a * b for a, b in zip(values, row.weights)), row.row_id, row)
        for row in bank.rows
    ]
    score, _, selected = max(scored, key=lambda item: (item[0], tuple(-ord(c) for c in item[1])))
    return selected, score


def apply_sealed_residual(
    bank: TokenWeightBank,
    residual: dict[str, tuple[float, ...]],
    *,
    scale: float,
) -> dict[str, tuple[float, ...]]:
    """Compose trainable residuals without mutating the immutable base bank."""

    if not bank.verify() or not math.isfinite(scale) or not 0 <= scale <= 1:
        raise ValueError("invalid base bank or residual scale")
    if set(residual) - {row.row_id for row in bank.rows}:
        raise ValueError("residual contains an unknown token row")
    result: dict[str, tuple[float, ...]] = {}
    for row in bank.rows:
        delta = residual.get(row.row_id, (0.0,) * bank.width)
        if len(delta) != bank.width or any(not math.isfinite(value) for value in delta):
            raise ValueError("residual row width/value is invalid")
        result[row.row_id] = tuple(float(base) + scale * value for base, value in zip(row.weights, delta))
    return result


__all__ = [
    "RELATION_SCHEMA",
    "SCHEMA",
    "TONGUES",
    "CanonicalToken",
    "RelationEdge",
    "SourceReceipt",
    "TokenWeightBank",
    "WeightRow",
    "apply_sealed_residual",
    "balanced_trits",
    "build_weight_bank",
    "default_source_receipts",
    "developmental_action_tokens",
    "file_sha256",
    "relation_graph",
    "route_weight_vector",
]
