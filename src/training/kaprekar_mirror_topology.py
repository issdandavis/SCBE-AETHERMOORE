"""Deterministic Kaprekar attractor features with a mirrored conjugate realm.

This module is a shadow-mode training experiment. It does not participate in
governance, encryption, payload encoding, or write authority.

For a fixed-width decimal state ``x``:

* ``K(x)`` is the usual Kaprekar descending-minus-ascending digit map.
* ``M(x)`` reverses the digits.
* ``K_m(x) = M(K(M(x)))`` is the mirror-realm transition.

The two dynamics are conjugate, so a primary path and its mirrored path have
the same convergence depth. For width four, the ordinary non-repdigit basin
bottoms at 6174 and the mirror basin bottoms at 4716.

The map is intentionally many-to-one. Its outputs are auxiliary topology
features and must always remain attached to an exact payload identifier.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

State = str
Point3D = tuple[float, float, float]


@dataclass(frozen=True)
class AttractorTrace:
    """One deterministic path into a fixed point or finite cycle."""

    start: State
    path: tuple[State, ...]
    cycle: tuple[State, ...]
    depth: int

    @property
    def period(self) -> int:
        return len(self.cycle)

    @property
    def bottom(self) -> State:
        """Return the first cycle state reached by this path."""

        return self.cycle[0]

    @property
    def is_fixed_point(self) -> bool:
        return self.period == 1


@dataclass(frozen=True)
class MirrorTopologyPair:
    """Paired primary/mirror features for one fixed-width decimal state."""

    state: State
    mirror_state: State
    palindrome_envelope: State
    mirror_pair_id: State
    is_mirror_seam: bool
    primary_trace: AttractorTrace
    mirror_trace: AttractorTrace
    primary_point: Point3D
    mirror_point: Point3D

    @property
    def primary_bottom(self) -> State:
        return self.primary_trace.bottom

    @property
    def mirror_bottom(self) -> State:
        return self.mirror_trace.bottom

    @property
    def depth(self) -> int:
        return self.primary_trace.depth


class KaprekarMirrorTopology:
    """Build mirrored attractor-basin features for fixed-width decimals.

    The returned 3D points lie strictly inside the Euclidean unit ball and can
    be consumed by a Poincare-ball experiment. They are not inserted into any
    canonical SCBE/PHDM state layout.
    """

    def __init__(
        self,
        *,
        width: int = 4,
        radial_scale: float = 0.5,
        max_planar_radius: float = 0.75,
        realm_offset: float = 0.2,
        max_steps: int = 10_000,
    ) -> None:
        if width < 2:
            raise ValueError("width must be at least 2")
        if radial_scale <= 0.0:
            raise ValueError("radial_scale must be positive")
        if not 0.0 < max_planar_radius < 1.0:
            raise ValueError("max_planar_radius must be in (0, 1)")
        if not 0.0 <= realm_offset < 1.0:
            raise ValueError("realm_offset must be in [0, 1)")
        if math.hypot(max_planar_radius, realm_offset) >= 1.0:
            raise ValueError(
                "planar radius and realm offset must remain inside the unit ball"
            )
        if max_steps < 1:
            raise ValueError("max_steps must be positive")

        self.width = width
        self.radial_scale = float(radial_scale)
        self.max_planar_radius = float(max_planar_radius)
        self.realm_offset = float(realm_offset)
        self.max_steps = int(max_steps)

    def normalize(self, value: int | str) -> State:
        """Return a zero-padded fixed-width decimal state."""

        if isinstance(value, bool):
            raise TypeError("boolean values are not decimal states")
        if isinstance(value, int):
            if value < 0 or value >= 10**self.width:
                raise ValueError(f"integer state must be in [0, {10**self.width})")
            return f"{value:0{self.width}d}"
        if not isinstance(value, str):
            raise TypeError("state must be an integer or decimal string")
        if not value or not value.isascii() or not value.isdigit():
            raise ValueError("string state must contain ASCII decimal digits")
        if len(value) > self.width:
            raise ValueError(f"string state cannot exceed width {self.width}")
        return value.zfill(self.width)

    def mirror(self, value: int | str) -> State:
        """Reflect a state by reversing its fixed-width digit sequence."""

        return self.normalize(value)[::-1]

    def palindrome(self, value: int | str) -> State:
        """Wrap a state and its reflection in a reversible palindrome."""

        state = self.normalize(value)
        return state + state[::-1]

    def kaprekar_step(self, value: int | str) -> State:
        """Apply one descending-minus-ascending fixed-width digit step."""

        state = self.normalize(value)
        ascending = "".join(sorted(state))
        descending = ascending[::-1]
        result = int(descending) - int(ascending)
        return f"{result:0{self.width}d}"

    def mirror_step(self, value: int | str) -> State:
        """Apply the conjugate mirror transition M(K(M(x)))."""

        return self.mirror(self.kaprekar_step(self.mirror(value)))

    def trace(
        self,
        value: int | str,
        *,
        realm: str = "primary",
    ) -> AttractorTrace:
        """Follow a state until a fixed point or cycle is encountered."""

        state = self.normalize(value)
        if realm == "primary":
            transition = self.kaprekar_step
        elif realm == "mirror":
            transition = self.mirror_step
        else:
            raise ValueError("realm must be 'primary' or 'mirror'")
        return self._trace_transition(state, transition)

    def pair(self, value: int | str) -> MirrorTopologyPair:
        """Return conjugate traces and bounded mirror-realm coordinates."""

        state = self.normalize(value)
        mirror_state = self.mirror(state)
        primary_trace = self.trace(state, realm="primary")
        mirror_trace = self.trace(mirror_state, realm="mirror")

        expected_mirror_path = tuple(self.mirror(item) for item in primary_trace.path)
        expected_mirror_cycle = tuple(self.mirror(item) for item in primary_trace.cycle)
        if (
            mirror_trace.path != expected_mirror_path
            or mirror_trace.cycle != expected_mirror_cycle
        ):
            raise RuntimeError("mirror conjugacy invariant failed")

        is_mirror_seam = state == mirror_state
        mirror_pair_id = min(state, mirror_state)
        primary_point, mirror_point = self._paired_points(
            mirror_pair_id=mirror_pair_id,
            depth=primary_trace.depth,
            is_mirror_seam=is_mirror_seam,
        )

        return MirrorTopologyPair(
            state=state,
            mirror_state=mirror_state,
            palindrome_envelope=self.palindrome(state),
            mirror_pair_id=mirror_pair_id,
            is_mirror_seam=is_mirror_seam,
            primary_trace=primary_trace,
            mirror_trace=mirror_trace,
            primary_point=primary_point,
            mirror_point=mirror_point,
        )

    def radial_depth(self, depth: int) -> float:
        """Map integer convergence depth to a bounded Poincare radius."""

        if depth < 0:
            raise ValueError("depth cannot be negative")
        return self.max_planar_radius * math.tanh(
            self.radial_scale * float(depth) / 2.0
        )

    def _trace_transition(
        self,
        start: State,
        transition: Callable[[State], State],
    ) -> AttractorTrace:
        seen: dict[State, int] = {}
        path: list[State] = []
        current = start

        while current not in seen:
            if len(path) >= self.max_steps:
                raise RuntimeError(
                    f"transition did not cycle within {self.max_steps} steps"
                )
            seen[current] = len(path)
            path.append(current)
            current = transition(current)

        cycle_start = seen[current]
        return AttractorTrace(
            start=start,
            path=tuple(path),
            cycle=tuple(path[cycle_start:]),
            depth=cycle_start,
        )

    def _paired_points(
        self,
        *,
        mirror_pair_id: State,
        depth: int,
        is_mirror_seam: bool,
    ) -> tuple[Point3D, Point3D]:
        pair_index = int(mirror_pair_id)
        angle = 2.0 * math.pi * (pair_index + 0.5) / float(10**self.width)
        radius = self.radial_depth(depth)
        x_coord = radius * math.cos(angle)
        y_coord = radius * math.sin(angle)

        if is_mirror_seam:
            point = (x_coord, y_coord, 0.0)
            return point, point

        primary = (x_coord, y_coord, self.realm_offset)
        reflected = (x_coord, -y_coord, -self.realm_offset)
        return primary, reflected
