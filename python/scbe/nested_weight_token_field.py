"""Nested matrix pockets driven by a weighted token path.

This is the executable reference for a specific SCBE geometry:

* several square/matrix representations share one field and one seed region;
* a token path supplies signed routing direction and non-negative growth energy;
* per-layer growth is summed, powered, and converted to one bounded multiplier;
* every layer receives that same multiplier, preserving all nesting ratios;
* the stack rotates in the plane whose local z-axis is the path tangent; and
* the key region sits behind the observed path by a declared chart offset.

The output is an address/provenance surface, not a cryptographic primitive.
Seed text, token weights, time, lore, and geometry add no secret entropy. A
signature or key-exchange protocol may bind the resulting receipt as context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import math
from typing import Iterable, Sequence

SCHEMA = "scbe.nested-weight-token-field.v1"
DEFAULT_LAYER_COUNT = 10
MAX_LAYER_COUNT = 64
_EPSILON = 1e-12

Vector3 = tuple[float, float, float]
Matrix4 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]


class NestedWeightFieldError(ValueError):
    """The requested field would not have a finite, replayable geometry."""


@dataclass(frozen=True, slots=True)
class WeightedTokenPoint:
    """One token observation in the path.

    ``weight`` is signed: its sign can oppose or reinforce the path direction.
    Growth uses its magnitude so negative evidence does not create an invalid
    negative side length. ``xyz`` is a declared representation coordinate; it
    is not inferred to be physical position.
    """

    token_id: str
    weight: float
    xyz: Vector3

    def __post_init__(self) -> None:
        if not isinstance(self.token_id, str) or not self.token_id:
            raise NestedWeightFieldError("token_id must be non-empty text")
        if not _finite(self.weight):
            raise NestedWeightFieldError("token weight must be finite")
        if len(self.xyz) != 3 or not all(_finite(value) for value in self.xyz):
            raise NestedWeightFieldError(
                "token coordinates must be three finite values"
            )


@dataclass(frozen=True, slots=True)
class NestedWeightFieldSpec:
    """Bounded controls for one nested field."""

    layer_count: int = DEFAULT_LAYER_COUNT
    nesting_ratio: float = 0.65
    base_side: float = 1.0
    growth_power: float = 2.0
    growth_gain: float = 0.2
    key_depth: float = 0.125
    coordinate_decimals: int = 12

    def __post_init__(self) -> None:
        if (
            isinstance(self.layer_count, bool)
            or not isinstance(self.layer_count, int)
            or not 1 <= self.layer_count <= MAX_LAYER_COUNT
        ):
            raise NestedWeightFieldError(f"layer_count must be in 1..{MAX_LAYER_COUNT}")
        if not _finite(self.nesting_ratio) or not 0.0 < self.nesting_ratio < 1.0:
            raise NestedWeightFieldError(
                "nesting_ratio must be strictly between 0 and 1"
            )
        if not _finite(self.base_side) or self.base_side <= 0.0:
            raise NestedWeightFieldError("base_side must be positive and finite")
        if not _finite(self.growth_power) or not 0.0 < self.growth_power <= 8.0:
            raise NestedWeightFieldError("growth_power must be in (0, 8]")
        if not _finite(self.growth_gain) or not 0.0 <= self.growth_gain <= 2.0:
            raise NestedWeightFieldError("growth_gain must be in [0, 2]")
        if not _finite(self.key_depth) or self.key_depth < 0.0:
            raise NestedWeightFieldError("key_depth must be non-negative and finite")
        if (
            isinstance(self.coordinate_decimals, bool)
            or not isinstance(self.coordinate_decimals, int)
            or not 6 <= self.coordinate_decimals <= 15
        ):
            raise NestedWeightFieldError("coordinate_decimals must be in 6..15")


@dataclass(frozen=True, slots=True)
class NestedMatrixLayer:
    index: int
    raw_growth: float
    side: float
    matrix: Matrix4
    vertices: tuple[Vector3, Vector3, Vector3, Vector3]


@dataclass(frozen=True, slots=True)
class NestedWeightTokenField:
    schema: str
    spec: NestedWeightFieldSpec
    seed_sha256: str
    token_path_sha256: str
    token_ids: tuple[str, ...]
    key_anchor: Vector3
    path_centroid: Vector3
    tangent_axis: Vector3
    rotation_radians: float
    path_energy: float
    powered_growth: float
    common_growth_ratio: float
    nesting_ratio: float
    layers: tuple[NestedMatrixLayer, ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def receipt_body(self) -> dict[str, object]:
        """Return the canonical payload covered by ``receipt_sha256``."""

        return {
            "schema": self.schema,
            "seed_sha256": self.seed_sha256,
            "token_path_sha256": self.token_path_sha256,
            "token_ids": list(self.token_ids),
            "spec": asdict(self.spec),
            "path_centroid": self.path_centroid,
            "key_anchor": self.key_anchor,
            "tangent_axis": self.tangent_axis,
            "rotation_radians": self.rotation_radians,
            "path_energy": self.path_energy,
            "powered_growth": self.powered_growth,
            "common_growth_ratio": self.common_growth_ratio,
            "layers": [asdict(layer) for layer in self.layers],
        }

    def receipt_is_valid(self) -> bool:
        """Verify that no receipt-covered field has changed."""

        expected = sha256(_canonical_bytes(self.receipt_body())).hexdigest()
        return expected == self.receipt_sha256


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _add(left: Vector3, right: Vector3) -> Vector3:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _scale(vector: Vector3, scalar: float) -> Vector3:
    return (vector[0] * scalar, vector[1] * scalar, vector[2] * scalar)


def _dot(left: Vector3, right: Vector3) -> float:
    return math.fsum(a * b for a, b in zip(left, right, strict=True))


def _cross(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _norm(vector: Vector3) -> float:
    return math.sqrt(_dot(vector, vector))


def _unit(vector: Vector3, *, label: str) -> Vector3:
    length = _norm(vector)
    if length <= _EPSILON:
        raise NestedWeightFieldError(f"{label} has no usable direction")
    return _scale(vector, 1.0 / length)


def _distance(left: Vector3, right: Vector3) -> float:
    return _norm(_subtract(left, right))


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _round_vector(vector: Vector3, decimals: int) -> Vector3:
    return tuple(round(value, decimals) for value in vector)  # type: ignore[return-value]


def _round_matrix(matrix: Matrix4, decimals: int) -> Matrix4:
    return tuple(
        tuple(round(value, decimals) for value in row) for row in matrix
    )  # type: ignore[return-value]


def _seed_phase(seed_digest: bytes) -> float:
    numerator = int.from_bytes(seed_digest[:8], "big")
    return math.tau * numerator / float(1 << 64)


def _path_centroid(points: Sequence[WeightedTokenPoint]) -> Vector3:
    masses = [abs(point.weight) for point in points]
    total = math.fsum(masses)
    if total <= _EPSILON:
        raise NestedWeightFieldError(
            "the token path needs at least one non-zero weight"
        )
    return tuple(
        math.fsum(
            mass * point.xyz[axis] for mass, point in zip(masses, points, strict=True)
        )
        / total
        for axis in range(3)
    )  # type: ignore[return-value]


def _path_tangent(points: Sequence[WeightedTokenPoint]) -> Vector3:
    segments = [
        _subtract(right.xyz, left.xyz)
        for left, right in zip(points, points[1:])
        if _distance(left.xyz, right.xyz) > _EPSILON
    ]
    if not segments:
        raise NestedWeightFieldError("the token path needs two distinct coordinates")
    direction = (
        math.fsum(segment[0] for segment in segments),
        math.fsum(segment[1] for segment in segments),
        math.fsum(segment[2] for segment in segments),
    )
    if _norm(direction) <= _EPSILON:
        direction = _subtract(points[-1].xyz, points[0].xyz)
    if _norm(direction) <= _EPSILON:
        direction = max(segments, key=_norm)
    return _unit(direction, label="token path tangent")


def _orthogonal_frame(tangent: Vector3) -> tuple[Vector3, Vector3]:
    reference: Vector3 = (0.0, 0.0, 1.0)
    if abs(_dot(tangent, reference)) > 0.9:
        reference = (0.0, 1.0, 0.0)
    first = _unit(_cross(tangent, reference), label="first tangent-plane axis")
    second = _unit(_cross(tangent, first), label="second tangent-plane axis")
    return first, second


def _rotate_plane(
    first: Vector3, second: Vector3, angle: float
) -> tuple[Vector3, Vector3]:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        _add(_scale(first, cosine), _scale(second, sine)),
        _add(_scale(first, -sine), _scale(second, cosine)),
    )


def _path_energy(points: Sequence[WeightedTokenPoint]) -> float:
    magnitude_rms = math.sqrt(
        math.fsum(point.weight * point.weight for point in points) / len(points)
    )
    weighted_length = math.fsum(
        (abs(left.weight) + abs(right.weight)) * 0.5 * _distance(left.xyz, right.xyz)
        for left, right in zip(points, points[1:])
    )
    weight_mass = math.fsum(abs(point.weight) for point in points)
    normalized_length = weighted_length / max(weight_mass, _EPSILON)
    return magnitude_rms + normalized_length


def _path_rotation(
    points: Sequence[WeightedTokenPoint],
    centroid: Vector3,
    first: Vector3,
    second: Vector3,
    seed_phase: float,
) -> float:
    first_moment = math.fsum(
        point.weight * _dot(_subtract(point.xyz, centroid), first) for point in points
    )
    second_moment = math.fsum(
        point.weight * _dot(_subtract(point.xyz, centroid), second) for point in points
    )
    if math.hypot(first_moment, second_moment) <= _EPSILON:
        return seed_phase
    return seed_phase + math.atan2(second_moment, first_moment)


def _layer_matrix(
    anchor: Vector3,
    first: Vector3,
    second: Vector3,
    tangent: Vector3,
    side: float,
) -> Matrix4:
    return (
        (side * first[0], side * second[0], tangent[0], anchor[0]),
        (side * first[1], side * second[1], tangent[1], anchor[1]),
        (side * first[2], side * second[2], tangent[2], anchor[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


def _vertices(
    anchor: Vector3, first: Vector3, second: Vector3, side: float
) -> tuple[Vector3, Vector3, Vector3, Vector3]:
    half_first = _scale(first, side / 2.0)
    half_second = _scale(second, side / 2.0)
    return (
        _subtract(_subtract(anchor, half_first), half_second),
        _add(_subtract(anchor, half_second), half_first),
        _add(_add(anchor, half_first), half_second),
        _add(_subtract(anchor, half_first), half_second),
    )


def build_nested_weight_token_field(
    points: Iterable[WeightedTokenPoint],
    *,
    field_seed: bytes | str,
    spec: NestedWeightFieldSpec = NestedWeightFieldSpec(),
) -> NestedWeightTokenField:
    """Build a replayable nested field from the complete weighted token path.

    The shared growth ratio is

    ``rho = exp(gain * tanh((sum_i g_i / n) ** power))``

    with ``g_i = path_energy * nesting_ratio**i``. Applying ``rho`` to every
    side length preserves ``side_i / side_j`` exactly up to floating-point
    representation. The exponential is bounded by ``exp(growth_gain)``.
    """

    path = tuple(points)
    if len(path) < 2:
        raise NestedWeightFieldError("the token path needs at least two points")
    if isinstance(field_seed, str):
        seed_bytes = field_seed.encode("utf-8")
    elif isinstance(field_seed, bytes):
        seed_bytes = field_seed
    else:
        raise NestedWeightFieldError("field_seed must be bytes or text")
    if not seed_bytes:
        raise NestedWeightFieldError("field_seed must not be empty")

    seed_hash = sha256(b"SCBE-NESTED-WEIGHT-FIELD-SEED-v1\0" + seed_bytes).digest()
    path_payload = [
        {
            "token_id": point.token_id,
            "weight": point.weight,
            "xyz": list(point.xyz),
        }
        for point in path
    ]
    token_path_sha256 = sha256(_canonical_bytes(path_payload)).hexdigest()
    centroid = _path_centroid(path)
    tangent = _path_tangent(path)
    first, second = _orthogonal_frame(tangent)
    phase = _path_rotation(path, centroid, first, second, _seed_phase(seed_hash))
    rotated_first, rotated_second = _rotate_plane(first, second, phase)

    # "Behind" is an explicit chart direction: the negative second tangent-plane
    # axis. It is not claimed to hide the key region from an observer.
    key_anchor = _subtract(centroid, _scale(second, spec.key_depth))
    energy = _path_energy(path)
    raw_growth = tuple(
        energy * spec.nesting_ratio**index for index in range(spec.layer_count)
    )
    mean_growth = math.fsum(raw_growth) / spec.layer_count
    powered_growth = mean_growth**spec.growth_power
    common_ratio = math.exp(spec.growth_gain * math.tanh(powered_growth))

    layers = []
    for index, growth in enumerate(raw_growth):
        side = spec.base_side * spec.nesting_ratio**index * common_ratio
        matrix = _round_matrix(
            _layer_matrix(key_anchor, rotated_first, rotated_second, tangent, side),
            spec.coordinate_decimals,
        )
        vertices = tuple(
            _round_vector(vertex, spec.coordinate_decimals)
            for vertex in _vertices(key_anchor, rotated_first, rotated_second, side)
        )
        layers.append(
            NestedMatrixLayer(
                index=index,
                raw_growth=round(growth, spec.coordinate_decimals),
                side=round(side, spec.coordinate_decimals),
                matrix=matrix,
                vertices=vertices,  # type: ignore[arg-type]
            )
        )

    field = NestedWeightTokenField(
        schema=SCHEMA,
        spec=spec,
        seed_sha256=seed_hash.hex(),
        token_path_sha256=token_path_sha256,
        token_ids=tuple(point.token_id for point in path),
        key_anchor=_round_vector(key_anchor, spec.coordinate_decimals),
        path_centroid=_round_vector(centroid, spec.coordinate_decimals),
        tangent_axis=_round_vector(tangent, spec.coordinate_decimals),
        rotation_radians=round(phase, spec.coordinate_decimals),
        path_energy=round(energy, spec.coordinate_decimals),
        powered_growth=round(powered_growth, spec.coordinate_decimals),
        common_growth_ratio=round(common_ratio, spec.coordinate_decimals),
        nesting_ratio=spec.nesting_ratio,
        layers=tuple(layers),
        receipt_sha256="",
    )
    receipt_sha256 = sha256(_canonical_bytes(field.receipt_body())).hexdigest()
    return replace(field, receipt_sha256=receipt_sha256)


def world_to_layer_local(
    field: NestedWeightTokenField, layer_index: int, point: Vector3
) -> Vector3:
    """Invert one layer's affine frame for audit and round-trip tests."""

    if not 0 <= layer_index < len(field.layers):
        raise NestedWeightFieldError("layer_index is outside the field")
    layer = field.layers[layer_index]
    matrix = layer.matrix
    first = (matrix[0][0], matrix[1][0], matrix[2][0])
    second = (matrix[0][1], matrix[1][1], matrix[2][1])
    tangent = (matrix[0][2], matrix[1][2], matrix[2][2])
    translation = (matrix[0][3], matrix[1][3], matrix[2][3])
    offset = _subtract(point, translation)

    # Invert the emitted matrix rather than assuming its rounded columns remain
    # perfectly orthogonal. Cramer's rule is small and stable for this 3x3
    # basis, whose first two columns are scaled by a strictly positive side.
    determinant = _dot(first, _cross(second, tangent))
    if abs(determinant) <= _EPSILON:
        raise NestedWeightFieldError("layer matrix is not invertible")
    return (
        _dot(offset, _cross(second, tangent)) / determinant,
        _dot(first, _cross(offset, tangent)) / determinant,
        _dot(first, _cross(second, offset)) / determinant,
    )


def ratios_are_preserved(
    field: NestedWeightTokenField, tolerance: float = 1e-10
) -> bool:
    """Check the load-bearing invariant across all adjacent layers."""

    if not _finite(tolerance) or tolerance < 0.0:
        raise NestedWeightFieldError("tolerance must be non-negative and finite")
    return all(
        math.isclose(
            inner.side / outer.side,
            field.nesting_ratio,
            rel_tol=tolerance,
            abs_tol=tolerance,
        )
        for outer, inner in zip(field.layers, field.layers[1:])
    )
