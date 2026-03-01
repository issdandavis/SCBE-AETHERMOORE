"""
Ray Caster — Light Beams Through Hyperbolic Governance Space
=============================================================

"Like a light beam down a mirror hallway, reflector the beam to
the right angles to get the path realigned, and you can layer 1
beam over itself in a non-canceling fashion to extend the light
distance."

Core idea: connections between memories/data exist as paths through
hyperbolic space. When you lose a path, you know one exists — so
you cast beams to find it.

Three beam types:
  1. LASER   — direct line between two points in Poincare ball
  2. SCATTER — fan of beams from a point, probing for reflections
  3. TRACE   — follow an existing braid path, checking for breaks

Physics engine: SCBE's harmonic wall H(d,R) = R^(d^2)
  - Beams travel cheaply near safe regions (d ≈ 0, cost ≈ 1)
  - Beams reflect off governance boundaries (high cost surfaces)
  - Adversarial regions absorb/scatter beams (cost → infinity)
  - Scalar physics: same formulas work at bit, token, and document scales

"What's small is big, what's big is small" — Fibonacci at all scales.
The same phi-scaled cost function governs bit-level fingerprints
and document-level semantic paths.

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

PHI = 1.618033988749895


# ---------------------------------------------------------------------------
#  Types
# ---------------------------------------------------------------------------

class BeamType(str, Enum):
    LASER = "laser"       # Direct point-to-point
    SCATTER = "scatter"   # Fan of probing beams
    TRACE = "trace"       # Follow existing path


class ReflectionType(str, Enum):
    SPECULAR = "specular"     # Perfect mirror reflection
    DIFFUSE = "diffuse"       # Scattered by governance boundary
    ABSORBED = "absorbed"     # Beam dies (adversarial region)
    TRANSMITTED = "transmitted"  # Passes through (safe region)


@dataclass
class Point:
    """A point in hyperbolic space (Poincare ball coordinates)."""
    coords: List[float]

    @property
    def dimension(self) -> int:
        return len(self.coords)

    @property
    def norm(self) -> float:
        return math.sqrt(sum(c * c for c in self.coords))

    def clamped(self, max_norm: float = 0.95) -> "Point":
        """Clamp to inside the Poincare ball."""
        n = self.norm
        if n <= max_norm:
            return self
        scale = max_norm / n
        return Point([c * scale for c in self.coords])

    def distance_to(self, other: "Point") -> float:
        """Hyperbolic distance in Poincare ball.

        d_H = arccosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
        """
        diff_sq = sum((a - b) ** 2 for a, b in zip(self.coords, other.coords))
        u_sq = sum(c * c for c in self.coords)
        v_sq = sum(c * c for c in other.coords)

        denom = (1.0 - u_sq) * (1.0 - v_sq)
        if denom <= 0:
            return float("inf")

        arg = 1.0 + 2.0 * diff_sq / denom
        if arg < 1.0:
            arg = 1.0
        return math.acosh(arg)

    def midpoint(self, other: "Point") -> "Point":
        """Euclidean midpoint (approximate geodesic midpoint for small distances)."""
        return Point([(a + b) / 2 for a, b in zip(self.coords, other.coords)]).clamped()

    def direction_to(self, other: "Point") -> List[float]:
        """Unit direction vector from self to other."""
        diff = [b - a for a, b in zip(self.coords, other.coords)]
        mag = math.sqrt(sum(d * d for d in diff))
        if mag < 1e-12:
            return [0.0] * self.dimension
        return [d / mag for d in diff]

    def step(self, direction: List[float], distance: float) -> "Point":
        """Take a step in the given direction."""
        new = [c + d * distance for c, d in zip(self.coords, direction)]
        return Point(new).clamped()


@dataclass
class Reflection:
    """A beam reflection event."""
    point: Point
    reflection_type: ReflectionType
    surface_cost: float      # Harmonic wall cost at reflection point
    normal: List[float]      # Surface normal at reflection
    beam_energy: float       # Remaining beam energy after reflection


@dataclass
class BeamSegment:
    """One segment of a beam's path between reflections."""
    start: Point
    end: Point
    energy: float
    cost_traversed: float
    length: float


@dataclass
class BeamResult:
    """Complete result of a beam cast."""
    beam_type: BeamType
    origin: Point
    target: Optional[Point]
    segments: List[BeamSegment]
    reflections: List[Reflection]
    total_cost: float
    total_length: float
    final_energy: float
    path_found: bool
    beam_id: str = ""

    def __post_init__(self):
        if not self.beam_id:
            raw = f"{self.beam_type}:{time.time()}"
            self.beam_id = hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class ScatterResult:
    """Result of a scatter cast (multiple beams)."""
    origin: Point
    beams: List[BeamResult]
    strongest_path: Optional[BeamResult]
    coverage_score: float  # What fraction of space was probed
    scatter_id: str = ""

    def __post_init__(self):
        if not self.scatter_id:
            raw = f"scatter:{time.time()}"
            self.scatter_id = hashlib.sha256(raw.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
#  Harmonic Wall — the "physics" of the simulation
# ---------------------------------------------------------------------------

def harmonic_wall(d: float, R: float = PHI) -> float:
    """The harmonic wall cost function: H(d,R) = R^(d^2).

    This IS the physics engine. Same formula at all scales:
      - Bit level: d = fingerprint distance
      - Token level: d = tongue distance
      - Document level: d = semantic distance
      - System level: d = braid distance

    "What's small is big" — same phi scaling everywhere.

    Args:
        d: Distance from the safe region (rail center).
        R: Base of exponential (default: phi).

    Returns:
        Cost >= 1.0. Grows exponentially with d^2.
    """
    return R ** (d * d)


def harmonic_gradient(d: float, R: float = PHI) -> float:
    """Gradient of harmonic wall: dH/dd = 2d * ln(R) * R^(d^2).

    This determines the "reflective force" at a boundary.
    Higher gradient = sharper reflection angle.
    """
    if abs(d) < 1e-12:
        return 0.0
    return 2.0 * d * math.log(R) * harmonic_wall(d, R)


def beam_energy_after_reflection(
    incoming_energy: float,
    surface_cost: float,
    reflection_type: ReflectionType,
) -> float:
    """Compute remaining beam energy after a reflection.

    Energy loss is proportional to the surface cost.
    Specular (mirror) reflections lose less than diffuse.
    Absorbed beams die.
    Transmitted beams pass through.
    """
    if reflection_type == ReflectionType.ABSORBED:
        return 0.0
    if reflection_type == ReflectionType.TRANSMITTED:
        return incoming_energy * 0.95  # Small transmission loss
    if reflection_type == ReflectionType.SPECULAR:
        # Mirror reflection: lose energy proportional to 1/cost
        return incoming_energy * (1.0 / max(1.0, surface_cost))
    if reflection_type == ReflectionType.DIFFUSE:
        # Diffuse: lose more energy
        return incoming_energy * (0.5 / max(1.0, surface_cost))
    return 0.0


# ---------------------------------------------------------------------------
#  Ray Caster — The Core Engine
# ---------------------------------------------------------------------------

class RayCaster:
    """Cast beams through hyperbolic governance space.

    The space has "physics" defined by the harmonic wall.
    Beams travel easily through safe regions and reflect off
    or get absorbed by governance boundaries.

    Three cast modes:
      laser()   — direct beam between two points
      scatter() — fan of beams probing from a point
      trace()   — follow and verify an existing path
    """

    def __init__(
        self,
        *,
        dimension: int = 6,
        step_size: float = 0.05,
        max_steps: int = 200,
        cost_threshold: float = 10.0,
        energy_threshold: float = 0.01,
    ):
        self.dimension = dimension
        self.step_size = step_size
        self.max_steps = max_steps
        self.cost_threshold = cost_threshold
        self.energy_threshold = energy_threshold
        self._cast_count = 0
        self._origin = Point([0.0] * dimension)  # Safe origin

    # ------------------------------------------------------------------
    #  LASER — direct point-to-point beam
    # ------------------------------------------------------------------

    def laser(self, origin: Point, target: Point) -> BeamResult:
        """Cast a laser beam from origin to target.

        The beam follows a straight line (Euclidean) through
        the Poincare ball. At governance boundaries (high cost),
        the beam reflects specularly.

        "If you can draw a straight line between things you have
        a connection."
        """
        self._cast_count += 1
        segments: List[BeamSegment] = []
        reflections: List[Reflection] = []
        energy = 1.0
        total_cost = 0.0
        total_length = 0.0

        current = origin
        direction = origin.direction_to(target)

        for step in range(self.max_steps):
            if energy < self.energy_threshold:
                break

            # Take a step
            next_point = current.step(direction, self.step_size)

            # Check cost at this point
            d = next_point.distance_to(self._origin)
            cost = harmonic_wall(d)

            # Check if we've reached the target
            dist_to_target = current.distance_to(target)
            if dist_to_target < self.step_size * 2:
                # Arrived
                seg = BeamSegment(
                    start=current, end=target,
                    energy=energy, cost_traversed=cost,
                    length=dist_to_target,
                )
                segments.append(seg)
                total_length += dist_to_target
                return BeamResult(
                    beam_type=BeamType.LASER,
                    origin=origin, target=target,
                    segments=segments, reflections=reflections,
                    total_cost=total_cost, total_length=total_length,
                    final_energy=energy, path_found=True,
                )

            if cost > self.cost_threshold:
                # Hit a governance boundary — reflect
                gradient = harmonic_gradient(d)
                ref_type = self._classify_reflection(cost, gradient)

                # Compute surface normal (gradient of cost function)
                normal = self._cost_gradient_direction(next_point)

                # Reflect direction
                if ref_type in (ReflectionType.SPECULAR, ReflectionType.DIFFUSE):
                    direction = self._reflect(direction, normal)

                energy = beam_energy_after_reflection(energy, cost, ref_type)

                reflections.append(Reflection(
                    point=next_point,
                    reflection_type=ref_type,
                    surface_cost=cost,
                    normal=normal,
                    beam_energy=energy,
                ))

                if ref_type == ReflectionType.ABSORBED:
                    break
            else:
                # Safe travel
                seg = BeamSegment(
                    start=current, end=next_point,
                    energy=energy, cost_traversed=cost,
                    length=self.step_size,
                )
                segments.append(seg)
                total_cost += cost
                total_length += self.step_size
                current = next_point

        return BeamResult(
            beam_type=BeamType.LASER,
            origin=origin, target=target,
            segments=segments, reflections=reflections,
            total_cost=total_cost, total_length=total_length,
            final_energy=energy, path_found=False,
        )

    # ------------------------------------------------------------------
    #  SCATTER — fan of probing beams
    # ------------------------------------------------------------------

    def scatter(
        self,
        origin: Point,
        n_beams: int = 12,
        beam_length: int = 50,
    ) -> ScatterResult:
        """Cast a scatter pattern — fan of beams probing from origin.

        "Lasers and scatter casts and ray casting is useful since
        it can use near metaphorical stuff, apply the projections
        to test the theory."
        """
        self._cast_count += n_beams
        beams: List[BeamResult] = []

        # Generate evenly distributed directions using golden angle
        golden_angle = math.pi * (3.0 - math.sqrt(5.0))  # ~2.399 rad

        for i in range(n_beams):
            # Generate direction using phi-based distribution
            direction = [0.0] * self.dimension
            for d in range(self.dimension):
                angle = (i * golden_angle + d * math.pi / self.dimension)
                direction[d] = math.cos(angle) * (0.3 + 0.7 * math.sin(i * golden_angle / 2))

            # Normalize
            mag = math.sqrt(sum(x * x for x in direction))
            if mag > 1e-12:
                direction = [x / mag for x in direction]

            # Create target along this direction
            target = origin.step(direction, 0.8)

            # Cast with limited steps
            saved_max = self.max_steps
            self.max_steps = beam_length
            beam = self.laser(origin, target)
            self.max_steps = saved_max
            beams.append(beam)

        # Find strongest path (most energy remaining, longest)
        strongest = None
        best_score = 0.0
        for b in beams:
            score = b.final_energy * b.total_length
            if score > best_score:
                best_score = score
                strongest = b

        # Coverage: how much of the space did we probe?
        total_length = sum(b.total_length for b in beams)
        max_possible = n_beams * beam_length * self.step_size
        coverage = total_length / max(max_possible, 1e-12)

        return ScatterResult(
            origin=origin,
            beams=beams,
            strongest_path=strongest,
            coverage_score=min(1.0, coverage),
        )

    # ------------------------------------------------------------------
    #  TRACE — follow and verify an existing path
    # ------------------------------------------------------------------

    def trace(self, waypoints: List[Point]) -> BeamResult:
        """Trace along a sequence of waypoints, checking path integrity.

        "If you lose the path, you know one exists, then you just
        have to reflector the beam to the right angles to get the
        path realigned."
        """
        if len(waypoints) < 2:
            return BeamResult(
                beam_type=BeamType.TRACE,
                origin=waypoints[0] if waypoints else Point([0.0] * self.dimension),
                target=None,
                segments=[], reflections=[],
                total_cost=0.0, total_length=0.0,
                final_energy=1.0, path_found=len(waypoints) >= 1,
            )

        self._cast_count += 1
        segments: List[BeamSegment] = []
        reflections: List[Reflection] = []
        total_cost = 0.0
        total_length = 0.0
        energy = 1.0
        path_broken = False

        for i in range(len(waypoints) - 1):
            wp_a = waypoints[i]
            wp_b = waypoints[i + 1]

            # Check cost at segment midpoint
            mid = wp_a.midpoint(wp_b)
            d_mid = mid.distance_to(self._origin)
            cost = harmonic_wall(d_mid)
            length = wp_a.distance_to(wp_b)

            if cost > self.cost_threshold:
                # Path broken at this segment — try to find reflection
                normal = self._cost_gradient_direction(mid)
                ref_type = self._classify_reflection(cost, harmonic_gradient(d_mid))
                energy = beam_energy_after_reflection(energy, cost, ref_type)

                reflections.append(Reflection(
                    point=mid,
                    reflection_type=ref_type,
                    surface_cost=cost,
                    normal=normal,
                    beam_energy=energy,
                ))

                if ref_type == ReflectionType.ABSORBED:
                    path_broken = True
                    break
            else:
                seg = BeamSegment(
                    start=wp_a, end=wp_b,
                    energy=energy, cost_traversed=cost,
                    length=length,
                )
                segments.append(seg)
                total_cost += cost
                total_length += length

        return BeamResult(
            beam_type=BeamType.TRACE,
            origin=waypoints[0],
            target=waypoints[-1],
            segments=segments, reflections=reflections,
            total_cost=total_cost, total_length=total_length,
            final_energy=energy, path_found=not path_broken,
        )

    # ------------------------------------------------------------------
    #  AMPLIFY — layer beams non-cancelingly
    # ------------------------------------------------------------------

    def amplify(self, beams: List[BeamResult]) -> BeamResult:
        """Layer beams over each other non-cancelingly to extend range.

        "You can layer 1 beam over itself in a non-canceling fashion
        to make the beam length be pushed by itself to extend the
        light distance."

        Takes multiple beams and combines their energy constructively.
        Overlapping segments add energy (like constructive interference).
        """
        if not beams:
            return BeamResult(
                beam_type=BeamType.LASER,
                origin=Point([0.0] * self.dimension),
                target=None,
                segments=[], reflections=[],
                total_cost=0.0, total_length=0.0,
                final_energy=0.0, path_found=False,
            )

        # Combine all segments
        all_segments: List[BeamSegment] = []
        all_reflections: List[Reflection] = []
        total_cost = 0.0
        total_length = 0.0

        for beam in beams:
            for seg in beam.segments:
                # Boost energy by layering
                boosted = BeamSegment(
                    start=seg.start, end=seg.end,
                    energy=seg.energy * len(beams),  # Constructive interference
                    cost_traversed=seg.cost_traversed,
                    length=seg.length,
                )
                all_segments.append(boosted)
                total_cost += seg.cost_traversed
                total_length += seg.length

            all_reflections.extend(beam.reflections)

        # Combined energy: sum of all beam energies (non-canceling)
        combined_energy = sum(b.final_energy for b in beams)

        # Use first beam's origin and last beam's target
        origin = beams[0].origin
        target = beams[-1].target

        # Path found if ANY beam found its path
        any_found = any(b.path_found for b in beams)

        return BeamResult(
            beam_type=BeamType.LASER,
            origin=origin, target=target,
            segments=all_segments, reflections=all_reflections,
            total_cost=total_cost, total_length=total_length,
            final_energy=combined_energy, path_found=any_found,
        )

    # ------------------------------------------------------------------
    #  Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "step_size": self.step_size,
            "max_steps": self.max_steps,
            "cost_threshold": self.cost_threshold,
            "energy_threshold": self.energy_threshold,
            "total_casts": self._cast_count,
        }

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _cost_gradient_direction(self, point: Point) -> List[float]:
        """Compute the gradient direction of the cost function.

        This is the surface normal at governance boundaries.
        Points away from the origin (toward higher cost).
        """
        # Gradient of d(point, origin) points radially outward
        n = point.norm
        if n < 1e-12:
            return [1.0] + [0.0] * (self.dimension - 1)
        return [c / n for c in point.coords]

    def _reflect(self, direction: List[float], normal: List[float]) -> List[float]:
        """Reflect direction off a surface defined by normal.

        Standard specular reflection: d' = d - 2(d.n)n
        """
        dot = sum(a * b for a, b in zip(direction, normal))
        reflected = [d - 2.0 * dot * n for d, n in zip(direction, normal)]

        # Normalize
        mag = math.sqrt(sum(r * r for r in reflected))
        if mag < 1e-12:
            return direction  # Degenerate case
        return [r / mag for r in reflected]

    def _classify_reflection(self, cost: float, gradient: float) -> ReflectionType:
        """Classify what happens when a beam hits a high-cost region."""
        if cost > 100.0:
            return ReflectionType.ABSORBED  # Adversarial: beam dies
        if cost > 20.0:
            return ReflectionType.DIFFUSE   # High governance: scattered
        if gradient > 5.0:
            return ReflectionType.SPECULAR  # Sharp boundary: mirror
        return ReflectionType.TRANSMITTED   # Gentle boundary: pass through
