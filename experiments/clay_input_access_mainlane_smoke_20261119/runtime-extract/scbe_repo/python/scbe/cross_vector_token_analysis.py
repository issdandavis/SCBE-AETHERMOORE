"""Auditable cross-vector analysis for mathematical and linguistic token streams.

This module keeps four views separate:

* canonical UTF-8 identity and byte span;
* six-tongue linguistic trits from :mod:`atomic_tokenization`;
* deterministic math/syntax features;
* occupancy and sparse relay output from :mod:`algebraic_radial_token_table`.

The views are coordinate charts over the same source tokens.  They are not
independent evidence and this module makes no learned-comprehension claim.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
from typing import Iterable, Literal, Sequence

from .algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    RadialTableSpec,
    TokenCarrier,
)
from .atomic_tokenization import map_token_to_atomic_state
from .bit_spine import BitSpine
from .tongue_diff import differential as tongue_differential


Mode = Literal["auto", "math", "linguistic"]
AXES = (
    "byte_center",
    "bit_polarity",
    "byte_trit_polarity",
    "byte_length",
    "tau_KO",
    "tau_AV",
    "tau_RU",
    "tau_CA",
    "tau_UM",
    "tau_DR",
    "semantic_band",
    "negative_state",
    "dual_state",
    "semantic_resolved",
    "kind_coordinate",
    "math_polarity",
    "math_precedence",
    "math_arity",
    "numeric_value",
    "sequence_position",
)

CHANNEL_AXES = {
    "transport": (
        "byte_center",
        "bit_polarity",
        "byte_trit_polarity",
        "byte_length",
    ),
    "linguistic": (
        "tau_KO",
        "tau_AV",
        "tau_RU",
        "tau_CA",
        "tau_UM",
        "tau_DR",
        "semantic_band",
        "negative_state",
        "dual_state",
        "semantic_resolved",
    ),
    "math": (
        "kind_coordinate",
        "math_polarity",
        "math_precedence",
        "math_arity",
        "numeric_value",
    ),
    "sequence": ("sequence_position",),
}

_AXIS_CHANNEL = {
    axis: channel
    for channel, channel_axes in CHANNEL_AXES.items()
    for axis in channel_axes
}

_TOKEN_RE = re.compile(
    r"(?P<number>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<identifier>[^\W\d]\w*)"
    r"|(?P<operator>\*\*|//|==|!=|<=|>=|:=|->|[+\-*/%^=<>])"
    r"|(?P<punct>[()[\]{},.:;])"
    r"|(?P<other>\S)",
    flags=re.UNICODE,
)

_KIND_COORDINATE = {
    "number": -1.0,
    "identifier": -0.5,
    "operator": 0.0,
    "punct": 0.5,
    "other": 1.0,
}
_MATH_OPERATOR = {
    "+": (1.0, 1.0, 2.0),
    "-": (-1.0, 1.0, 2.0),
    "*": (0.75, 2.0, 2.0),
    "/": (-0.75, 2.0, 2.0),
    "//": (-0.625, 2.0, 2.0),
    "%": (-0.5, 2.0, 2.0),
    "**": (1.0, 3.0, 2.0),
    "^": (0.875, 3.0, 2.0),
    "=": (0.0, 0.25, 2.0),
    ":=": (0.0, 0.25, 2.0),
    "==": (0.25, 0.5, 2.0),
    "!=": (-0.25, 0.5, 2.0),
    "<": (-0.5, 0.5, 2.0),
    "<=": (-0.25, 0.5, 2.0),
    ">": (0.5, 0.5, 2.0),
    ">=": (0.25, 0.5, 2.0),
    "->": (0.5, 0.25, 2.0),
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _trit(value: float, tolerance: float = 1e-12) -> int:
    return 1 if value > tolerance else -1 if value < -tolerance else 0


def _cosine(left: Sequence[float], right: Sequence[float]) -> float | None:
    left_norm = math.sqrt(math.fsum(value * value for value in left))
    right_norm = math.sqrt(math.fsum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return math.fsum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


@dataclass(frozen=True, slots=True)
class VectorToken:
    occurrence_id: str
    text: str
    normalized: str
    kind: str
    char_start: int
    char_end: int
    byte_start: int
    byte_end: int
    canonical_id: str
    utf8_bytes: tuple[int, ...]
    bits: str
    byte_trits: tuple[int, ...]
    semantic_class: str
    semantic_resolved: bool
    semantic_source: str
    tau: tuple[int, ...]
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class AlignmentRow:
    input_index: int | None
    output_index: int | None
    relation: str
    input_text: str | None
    output_text: str | None
    cosine: float | None
    l2_distance: float | None
    delta: tuple[float, ...] | None
    delta_trits: tuple[int, ...] | None


@dataclass(frozen=True, slots=True)
class AxisDifferential:
    axis: str
    channel: str
    input_value: float
    output_value: float
    delta: float
    orientation_trit: int
    zero_kind: str


def detect_mode(text: str) -> Literal["math", "linguistic"]:
    """Choose math only when an explicit operator or numeric expression exists."""

    tokens = list(_TOKEN_RE.finditer(text))
    has_operator = any(match.lastgroup == "operator" for match in tokens)
    has_number = any(match.lastgroup == "number" for match in tokens)
    return "math" if has_operator or has_number else "linguistic"


def _numeric_coordinate(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        return 0.0
    if not math.isfinite(value):
        raise ValueError("numeric tokens must be finite")
    return math.copysign(math.tanh(math.log1p(abs(value)) / 8.0), value)


def tokenize(text: str, *, mode: Mode = "auto", side: str = "input") -> tuple[VectorToken, ...]:
    """Tokenize text and derive the sixteen declared analysis axes."""

    selected_mode = detect_mode(text) if mode == "auto" else mode
    matches = list(_TOKEN_RE.finditer(text))
    output: list[VectorToken] = []
    byte_offsets = [0]
    for character in text:
        byte_offsets.append(byte_offsets[-1] + len(character.encode("utf-8")))

    denominator = max(1, len(matches) - 1)
    for index, match in enumerate(matches):
        token = match.group(0)
        spine = BitSpine(token.encode("utf-8"))
        token_bytes = tuple(spine.data)
        bits = spine.bits()
        byte_trits = tuple(spine.trits())
        kind = str(match.lastgroup)
        context = "math" if selected_mode == "math" else "linguistic"
        atomic = map_token_to_atomic_state(token, context_class=context)
        polarity, precedence, arity = _MATH_OPERATOR.get(token, (0.0, 0.0, 0.0))
        dual = 0.0 if atomic.dual_state is None else -1.0 if atomic.dual_state == 0 else 1.0
        position = 0.0 if len(matches) == 1 else (2.0 * index / denominator) - 1.0
        vector = (
            math.fsum((value / 127.5) - 1.0 for value in token_bytes) / len(token_bytes),
            (bits.count("1") - bits.count("0")) / len(bits),
            math.fsum(byte_trits) / len(byte_trits),
            math.tanh(math.log1p(len(token_bytes)) / 4.0),
            *(float(value) for value in atomic.tau.as_tuple()),
            float(atomic.band_flag),
            1.0 if atomic.negative_state else -1.0,
            dual,
            1.0 if atomic.semantic_resolved else 0.0,
            _KIND_COORDINATE[kind],
            polarity,
            precedence / 3.0,
            arity / 2.0,
            _numeric_coordinate(token) if kind == "number" else 0.0,
            position,
        )
        if len(vector) != len(AXES):
            raise AssertionError("vector schema and axis ledger diverged")
        byte_start = byte_offsets[match.start()]
        byte_end = byte_offsets[match.end()]
        canonical_id = f"utf8:{token.encode('utf-8').hex()}"
        output.append(
            VectorToken(
                occurrence_id=f"{side}:{index}:{byte_start}-{byte_end}",
                text=token,
                normalized=token.casefold() if kind == "identifier" else token,
                kind=kind,
                char_start=match.start(),
                char_end=match.end(),
                byte_start=byte_start,
                byte_end=byte_end,
                canonical_id=canonical_id,
                utf8_bytes=token_bytes,
                bits=bits,
                byte_trits=byte_trits,
                semantic_class=atomic.semantic_class,
                semantic_resolved=atomic.semantic_resolved,
                semantic_source=atomic.semantic_source,
                tau=atomic.tau.as_tuple(),
                vector=vector,
            )
        )
    return tuple(output)


def _substitution_score(left: VectorToken, right: VectorToken) -> float:
    if left.normalized == right.normalized and left.kind == right.kind:
        return 3.0
    if left.kind == right.kind:
        return 0.5
    return -1.0


def align(input_tokens: Sequence[VectorToken], output_tokens: Sequence[VectorToken]) -> tuple[AlignmentRow, ...]:
    """Globally align two token sequences with deterministic tie-breaking."""

    gap = -1.25
    rows, columns = len(input_tokens) + 1, len(output_tokens) + 1
    score = [[0.0] * columns for _ in range(rows)]
    trace = [[""] * columns for _ in range(rows)]
    for i in range(1, rows):
        score[i][0], trace[i][0] = i * gap, "delete"
    for j in range(1, columns):
        score[0][j], trace[0][j] = j * gap, "insert"
    for i in range(1, rows):
        for j in range(1, columns):
            candidates = (
                (score[i - 1][j - 1] + _substitution_score(input_tokens[i - 1], output_tokens[j - 1]), "pair", 2),
                (score[i - 1][j] + gap, "delete", 1),
                (score[i][j - 1] + gap, "insert", 0),
            )
            best = max(candidates, key=lambda item: (item[0], item[2]))
            score[i][j], trace[i][j] = best[0], best[1]

    aligned: list[AlignmentRow] = []
    i, j = len(input_tokens), len(output_tokens)
    zero = (0.0,) * len(AXES)
    while i or j:
        action = trace[i][j]
        if action == "pair":
            left, right = input_tokens[i - 1], output_tokens[j - 1]
            delta = tuple(b - a for a, b in zip(left.vector, right.vector, strict=True))
            relation = "unchanged" if left.normalized == right.normalized and left.kind == right.kind else "substituted"
            aligned.append(
                AlignmentRow(
                    i - 1,
                    j - 1,
                    relation,
                    left.text,
                    right.text,
                    _cosine(left.vector, right.vector),
                    math.sqrt(math.fsum(value * value for value in delta)),
                    delta,
                    tuple(_trit(value) for value in delta),
                )
            )
            i -= 1
            j -= 1
        elif action == "delete":
            left = input_tokens[i - 1]
            delta = tuple(-value for value in left.vector)
            aligned.append(
                AlignmentRow(i - 1, None, "deleted", left.text, None, None, math.sqrt(math.fsum(v * v for v in delta)), delta, tuple(_trit(v) for v in delta))
            )
            i -= 1
        else:
            right = output_tokens[j - 1]
            delta = tuple(value - base for value, base in zip(right.vector, zero, strict=True))
            aligned.append(
                AlignmentRow(None, j - 1, "inserted", None, right.text, None, math.sqrt(math.fsum(v * v for v in delta)), delta, tuple(_trit(v) for v in delta))
            )
            j -= 1
    return tuple(reversed(aligned))


def _mean_vector(tokens: Sequence[VectorToken]) -> tuple[float, ...]:
    if not tokens:
        return (0.0,) * len(AXES)
    return tuple(math.fsum(token.vector[axis] for token in tokens) / len(tokens) for axis in range(len(AXES)))


def _axis_differentials(
    input_mean: Sequence[float], output_mean: Sequence[float]
) -> tuple[AxisDifferential, ...]:
    rows: list[AxisDifferential] = []
    for axis, input_value, output_value in zip(AXES, input_mean, output_mean, strict=True):
        delta = output_value - input_value
        orientation = _trit(delta)
        rows.append(
            AxisDifferential(
                axis=axis,
                channel=_AXIS_CHANNEL[axis],
                input_value=input_value,
                output_value=output_value,
                delta=delta,
                orientation_trit=orientation,
                zero_kind="EXACT_NEUTRAL" if orientation == 0 else "NOT_ZERO",
            )
        )
    return tuple(rows)


def _channel_differentials(axis_rows: Sequence[AxisDifferential]) -> list[dict[str, object]]:
    rows_by_axis = {row.axis: row for row in axis_rows}
    output: list[dict[str, object]] = []
    for channel, axes in CHANNEL_AXES.items():
        rows = [rows_by_axis[axis] for axis in axes]
        output.append(
            {
                "channel": channel,
                "axes": list(axes),
                "input": [row.input_value for row in rows],
                "output": [row.output_value for row in rows],
                "delta": [row.delta for row in rows],
                "orientation_trits": [row.orientation_trit for row in rows],
                "delta_l2": math.sqrt(math.fsum(row.delta * row.delta for row in rows)),
                "active_axis_count": sum(row.orientation_trit != 0 for row in rows),
            }
        )
    return output


def _radial_receipt(
    input_tokens: Sequence[VectorToken],
    output_tokens: Sequence[VectorToken],
    aggregate_delta: Sequence[float],
    *,
    seed: int,
) -> dict[str, object]:
    spec = RadialTableSpec(cell_count=64, sector_count=8, dimensions=len(AXES), depth_count=4, seed=seed)
    table = AlgebraicRadialTokenTable(spec)
    sector_parameters = tuple(float(aggregate_delta[index]) for index in range(spec.sector_count))
    cells = table.move(sector_parameters)
    carriers = [TokenCarrier(token.canonical_id, token.vector) for token in (*input_tokens, *output_tokens)]
    occupancies = table.assign(carriers, cells)
    split = len(input_tokens)
    input_occupancies, output_occupancies = occupancies[:split], occupancies[split:]
    relays = table.build_relays(cells)
    state = {cell_id: [0.0, 0.0, 0.0] for cell_id in range(spec.cell_count)}
    for occupancy in input_occupancies:
        if occupancy.cell_id is not None:
            state[occupancy.cell_id][0] += 1.0
            state[occupancy.cell_id][2] -= 1.0
    for occupancy in output_occupancies:
        if occupancy.cell_id is not None:
            state[occupancy.cell_id][1] += 1.0
            state[occupancy.cell_id][2] += 1.0
    flashes: list[dict[str, object]] = []
    current = {key: tuple(value) for key, value in state.items()}
    for depth in range(spec.depth_count):
        current = table.flash(current, relays, depth=depth, residual=True)
        ranked = sorted(
            current.items(),
            key=lambda item: (-math.sqrt(math.fsum(value * value for value in item[1])), item[0]),
        )[:8]
        flashes.append({"depth": depth, "top_cells": [{"cell_id": cell_id, "state": list(values)} for cell_id, values in ranked]})
    mechanics = table.receipt(cells=cells, occupancies=occupancies, relays=relays, sector_parameters=sector_parameters)
    return {
        "spec": asdict(spec),
        "sector_parameters": list(sector_parameters),
        "input_cells": [row.cell_id for row in input_occupancies],
        "output_cells": [row.cell_id for row in output_occupancies],
        "relay_count": len(relays),
        "relay_trit_histogram": {str(value): sum(edge.trit == value for edge in relays) for value in (-1, 0, 1)},
        "flashes": flashes,
        "mechanics_receipt_sha256": mechanics["receipt_sha256"],
    }


def analyze(input_text: str, output_text: str, *, mode: Mode = "auto", seed: int = 20261110) -> dict[str, object]:
    """Analyze an input/output pair and return a reconstructable ledger."""

    input_mode = detect_mode(input_text) if mode == "auto" else mode
    output_mode = detect_mode(output_text) if mode == "auto" else mode
    input_tokens = tokenize(input_text, mode=input_mode, side="input")
    output_tokens = tokenize(output_text, mode=output_mode, side="output")
    rows = align(input_tokens, output_tokens)
    input_mean, output_mean = _mean_vector(input_tokens), _mean_vector(output_tokens)
    delta = tuple(b - a for a, b in zip(input_mean, output_mean, strict=True))
    axis_rows = _axis_differentials(input_mean, output_mean)
    core: dict[str, object] = {
        "schema": "scbe.cross-vector-token-analysis.v2",
        "claim_boundary": "deterministic coordinate analysis; no learned comprehension or independent-view claim",
        "axes": list(AXES),
        "input": {"text": input_text, "mode": input_mode, "tokens": [asdict(token) for token in input_tokens]},
        "output": {"text": output_text, "mode": output_mode, "tokens": [asdict(token) for token in output_tokens]},
        "analysis": {
            "alignment": [asdict(row) for row in rows],
            "relation_counts": {relation: sum(row.relation == relation for row in rows) for relation in ("unchanged", "substituted", "inserted", "deleted")},
            "input_mean": list(input_mean),
            "output_mean": list(output_mean),
            "aggregate_delta": list(delta),
            "aggregate_delta_trits": [_trit(value) for value in delta],
            "axis_differential": [asdict(row) for row in axis_rows],
            "channel_differential": _channel_differentials(axis_rows),
            "aggregate_cosine": _cosine(input_mean, output_mean),
            "tongue_differential": tongue_differential(input_text, output_text),
            "radial": _radial_receipt(input_tokens, output_tokens, delta, seed=seed),
        },
    }
    return {**core, "receipt_sha256": sha256(_canonical_json(core)).hexdigest()}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, dest="input_text")
    parser.add_argument("--output", required=True, dest="output_text")
    parser.add_argument("--mode", choices=("auto", "math", "linguistic"), default="auto")
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--json", action="store_true", help="emit the complete JSON receipt")
    args = parser.parse_args(list(argv) if argv is not None else None)
    receipt = analyze(args.input_text, args.output_text, mode=args.mode, seed=args.seed)
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        analysis = receipt["analysis"]
        print(f"receipt: {receipt['receipt_sha256']}")
        print(f"modes: {receipt['input']['mode']} -> {receipt['output']['mode']}")
        print(f"relations: {analysis['relation_counts']}")
        print(f"delta trits: {analysis['aggregate_delta_trits']}")
        print("channels:")
        for channel in analysis["channel_differential"]:
            print(
                f"  {channel['channel']}: active={channel['active_axis_count']}/"
                f"{len(channel['axes'])} l2={channel['delta_l2']:.6f} "
                f"trits={channel['orientation_trits']}"
            )
        print(f"tongues: {analysis['tongue_differential']}")
        print(f"radial output cells: {analysis['radial']['output_cells']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AXES",
    "CHANNEL_AXES",
    "AlignmentRow",
    "AxisDifferential",
    "VectorToken",
    "align",
    "analyze",
    "detect_mode",
    "tokenize",
]
