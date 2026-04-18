from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES
from src.geoseal_cli import TONGUE_PHI_WEIGHTS
from src.symphonic.multipath import TRIT_TABLES

_LOWER_TO_UPPER = {code: code.upper() for code in TONGUES}
_UPPER_TO_INDEX = {code: idx for idx, code in enumerate(("KO", "AV", "RU", "CA", "UM", "DR"))}


@dataclass(frozen=True)
class BraidAlignmentReport:
    payload: bytes
    semantic_tongue: str
    op_tongue: str
    ops: tuple[str, ...]
    roundtrip_ok: bool
    semantic_alignment: float
    atomic_home_alignment: float
    phi_underlay_alignment: float
    harmonic_fingerprint: float
    overall_score: float


def _normalise_tongue_code(code: str) -> str:
    lowered = code.lower()
    if lowered not in TONGUES:
        raise KeyError(f"Unknown Sacred Tongue code: {code}")
    return lowered


def _table_for(lower_tongue: str):
    return TRIT_TABLES[_LOWER_TO_UPPER[lower_tongue]]


def _table_ops(table) -> list[str]:
    if hasattr(table, "ops"):
        return list(table.ops)
    if hasattr(table, "CA_OPS"):
        return list(table.CA_OPS)
    raise TypeError("Unsupported trit table type: missing ops list")


def _table_trit_stream(table, ops: Sequence[str]) -> np.ndarray:
    if hasattr(table, "trit_stream"):
        return table.trit_stream(list(ops))
    if hasattr(table, "TRIT_MATRIX") and hasattr(table, "OP_ID"):
        return np.stack([table.TRIT_MATRIX[table.OP_ID[op]] for op in ops])
    raise TypeError("Unsupported trit table type: missing trit stream support")


def sample_ops_for_tongue(tongue_code: str, count: int = 4) -> tuple[str, ...]:
    lower = _normalise_tongue_code(tongue_code)
    table = _table_for(lower)
    ops = _table_ops(table)
    if count <= 0:
        raise ValueError("count must be positive")
    return tuple(ops[: min(count, len(ops))])


def evaluate_semantic_atomic_braid(
    payload: bytes,
    semantic_tongue: str,
    op_tongue: str,
    ops: Sequence[str] | None = None,
) -> BraidAlignmentReport:
    semantic = _normalise_tongue_code(semantic_tongue)
    operational = _normalise_tongue_code(op_tongue)

    token_stream = tuple(SACRED_TONGUE_TOKENIZER.encode_bytes(semantic, payload))
    roundtrip_ok = SACRED_TONGUE_TOKENIZER.decode_tokens(semantic, list(token_stream)) == payload
    harmonic_fingerprint = SACRED_TONGUE_TOKENIZER.compute_harmonic_fingerprint(semantic, list(token_stream))

    table = _table_for(operational)
    op_stream = tuple(ops) if ops is not None else sample_ops_for_tongue(operational)
    trit_stream = _table_trit_stream(table, op_stream)

    home_index = _UPPER_TO_INDEX[_LOWER_TO_UPPER[semantic]]
    atomic_home_alignment = float(np.mean((trit_stream[:, home_index] + 1.0) / 2.0))

    semantic_alignment = 1.0 if semantic == operational else 0.0
    phi_expected = TONGUE_PHI_WEIGHTS[_LOWER_TO_UPPER[semantic]]
    phi_actual = TONGUE_PHI_WEIGHTS[_LOWER_TO_UPPER[operational]]
    phi_underlay_alignment = 1.0 / (1.0 + abs(phi_expected - phi_actual))

    overall_score = (
        0.25 * semantic_alignment
        + 0.20 * (1.0 if roundtrip_ok else 0.0)
        + 0.40 * atomic_home_alignment
        + 0.15 * phi_underlay_alignment
    )

    return BraidAlignmentReport(
        payload=payload,
        semantic_tongue=semantic,
        op_tongue=operational,
        ops=op_stream,
        roundtrip_ok=roundtrip_ok,
        semantic_alignment=semantic_alignment,
        atomic_home_alignment=atomic_home_alignment,
        phi_underlay_alignment=phi_underlay_alignment,
        harmonic_fingerprint=harmonic_fingerprint,
        overall_score=overall_score,
    )
