"""Exact oriented-zero guards and receipted graph transitions.

This module turns a narrow mathematical idea into a small hybrid automaton:

* ``u(r) = C h / (r + h)`` maps a nonnegative radius to a bounded coordinate
  that approaches the exact ceiling ``C`` as ``r`` approaches zero;
* the sign is stored separately as ``-1``, ``0``, or ``+1`` so an exact zero
  may remember which side reached it without relying on IEEE signed zero;
* an enter guard authorizes a graph transition only for a unique
  ``(region, side, context)`` edge;
* a wider exit guard, a reset outside that guard, a minimum dwell, and a
  finite jump budget prevent zero-boundary chatter and Zeno-style cycling;
* every step is deterministic and hash linked for reproducible audit.

The ceiling is a coordinate transform, not entropy and not division by zero.
An unoriented zero remains unresolved and is quarantined.  The receipt chain
is tamper evident, not authenticated; a production caller must sign or anchor
its head with an independent key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
import re
from typing import Literal, Sequence

Direction = Literal[-1, 0, 1]
Outcome = Literal["APPROACH", "HOLD", "REARM", "JUMP", "QUARANTINE", "DENY"]

GENESIS_SHA256 = "0" * 64
MAX_EXACT_BITS = 4096
MAX_REGIONS = 1024
MAX_EDGES = 4096
MAX_TRACE_STEPS = 1_000_000
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
_OUTCOMES: frozenset[str] = frozenset({"APPROACH", "HOLD", "REARM", "JUMP", "QUARANTINE", "DENY"})


def _require_fraction(value: object, name: str) -> Fraction:
    if type(value) is not Fraction:
        raise TypeError(f"{name} must be an exact Fraction")
    if abs(value.numerator).bit_length() > MAX_EXACT_BITS or value.denominator.bit_length() > MAX_EXACT_BITS:
        raise ValueError(f"{name} exceeds the {MAX_EXACT_BITS}-bit exact-arithmetic limit")
    return value


def _require_plain_int(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a plain integer of at least {minimum}")
    if value.bit_length() > MAX_EXACT_BITS:
        raise ValueError(f"{name} exceeds the {MAX_EXACT_BITS}-bit integer limit")
    return value


def _require_identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{name} is not a stable identifier")
    return value


def _require_sha256(value: object, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _fraction_payload(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class CeilingMap:
    """Exact bounded chart ``u(r) = ceiling*scale/(r+scale)``."""

    ceiling: Fraction
    scale: Fraction

    def __post_init__(self) -> None:
        if _require_fraction(self.ceiling, "ceiling") <= 0:
            raise ValueError("ceiling must be positive")
        if _require_fraction(self.scale, "scale") <= 0:
            raise ValueError("scale must be positive")

    def project(self, radius: Fraction) -> Fraction:
        """Map a radius to ``(0, ceiling]`` without a zero denominator."""

        radius = _require_fraction(radius, "radius")
        if radius < 0:
            raise ValueError("radius must be nonnegative")
        result = self.ceiling * self.scale / (radius + self.scale)
        return _require_fraction(result, "projected coordinate")

    def gap(self, radius: Fraction) -> Fraction:
        """Return the exact remaining distance to the ceiling."""

        return _require_fraction(self.ceiling - self.project(radius), "ceiling gap")

    def unproject(self, coordinate: Fraction) -> Fraction:
        """Recover the finite radius from a positive bounded coordinate."""

        coordinate = _require_fraction(coordinate, "coordinate")
        if coordinate <= 0 or coordinate > self.ceiling:
            raise ValueError("coordinate must lie in (0, ceiling]")
        result = self.scale * (self.ceiling - coordinate) / coordinate
        return _require_fraction(result, "unprojected radius")

    def to_dict(self) -> dict[str, object]:
        return {
            "ceiling": _fraction_payload(self.ceiling),
            "scale": _fraction_payload(self.scale),
        }


@dataclass(frozen=True)
class Region:
    """One chart with separate enter and exit radii."""

    region_id: str
    enter_radius: Fraction
    exit_radius: Fraction
    chart: CeilingMap

    def __post_init__(self) -> None:
        _require_identifier(self.region_id, "region_id")
        enter = _require_fraction(self.enter_radius, "enter_radius")
        exit_radius = _require_fraction(self.exit_radius, "exit_radius")
        if enter < 0 or exit_radius <= enter:
            raise ValueError("region guards require 0 <= enter_radius < exit_radius")
        if not isinstance(self.chart, CeilingMap):
            raise TypeError("region chart must be a CeilingMap")

    def to_dict(self) -> dict[str, object]:
        return {
            "region_id": self.region_id,
            "enter_radius": _fraction_payload(self.enter_radius),
            "exit_radius": _fraction_payload(self.exit_radius),
            "chart": self.chart.to_dict(),
        }


@dataclass(frozen=True)
class RegionEdge:
    """A unique authorized jump for one oriented side and context."""

    source: str
    side: Literal[-1, 1]
    context: str
    destination: str
    reset_radius: Fraction

    def __post_init__(self) -> None:
        _require_identifier(self.source, "edge source")
        _require_identifier(self.destination, "edge destination")
        _require_identifier(self.context, "edge context")
        if self.side not in (-1, 1) or isinstance(self.side, bool):
            raise ValueError("an edge side must be -1 or +1")
        if _require_fraction(self.reset_radius, "reset_radius") < 0:
            raise ValueError("reset radius must be nonnegative")

    @property
    def key(self) -> tuple[str, Literal[-1, 1], str]:
        return self.source, self.side, self.context

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "side": self.side,
            "context": self.context,
            "destination": self.destination,
            "reset_radius": _fraction_payload(self.reset_radius),
        }


@dataclass(frozen=True)
class RegionGraph:
    """Immutable graph and anti-chatter policy."""

    regions: tuple[Region, ...]
    edges: tuple[RegionEdge, ...]
    jump_budget: int
    minimum_dwell_steps: int = 2
    _digest_sha256: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.regions) is not tuple or not self.regions:
            raise TypeError("regions must be a nonempty immutable tuple")
        if type(self.edges) is not tuple:
            raise TypeError("edges must be an immutable tuple")
        if len(self.regions) > MAX_REGIONS or len(self.edges) > MAX_EDGES:
            raise ValueError("graph exceeds its bounded region or edge count")
        if any(not isinstance(region, Region) for region in self.regions):
            raise TypeError("every graph region must be a Region")
        if any(not isinstance(edge, RegionEdge) for edge in self.edges):
            raise TypeError("every graph edge must be a RegionEdge")
        _require_plain_int(self.jump_budget, "jump_budget", minimum=1)
        _require_plain_int(self.minimum_dwell_steps, "minimum_dwell_steps", minimum=1)
        if self.jump_budget > MAX_TRACE_STEPS or self.minimum_dwell_steps > MAX_TRACE_STEPS:
            raise ValueError("graph jump or dwell bound exceeds the trace limit")

        by_id = {region.region_id: region for region in self.regions}
        if len(by_id) != len(self.regions):
            raise ValueError("region IDs must be unique")
        keys = {edge.key for edge in self.edges}
        if len(keys) != len(self.edges):
            raise ValueError("ambiguous graph edges are forbidden")
        for edge in self.edges:
            if edge.source not in by_id or edge.destination not in by_id:
                raise ValueError("every graph edge must connect declared regions")
            if edge.reset_radius < by_id[edge.destination].exit_radius:
                raise ValueError("an edge reset must land outside the destination exit guard")
        object.__setattr__(self, "_digest_sha256", _digest(self.to_dict()))

    @property
    def digest(self) -> str:
        return self._digest_sha256

    def region(self, region_id: str) -> Region:
        _require_identifier(region_id, "region_id")
        for region in self.regions:
            if region.region_id == region_id:
                return region
        raise ValueError("state references an unknown region")

    def edge(self, source: str, side: Direction, context: str) -> RegionEdge | None:
        if side not in (-1, 1):
            return None
        matches = [edge for edge in self.edges if edge.key == (source, side, context)]
        if len(matches) > 1:
            raise ValueError("ambiguous transition graph")
        return matches[0] if matches else None

    def validate_state(self, state: "HybridState") -> None:
        if not isinstance(state, HybridState):
            raise TypeError("state must be a HybridState")
        self.region(state.region_id)
        if state.jumps > self.jump_budget:
            raise ValueError("state exceeds the graph jump budget")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "scbe.oriented-zero-region-graph.v1",
            "regions": [region.to_dict() for region in self.regions],
            "edges": [edge.to_dict() for edge in self.edges],
            "jump_budget": self.jump_budget,
            "minimum_dwell_steps": self.minimum_dwell_steps,
        }


@dataclass(frozen=True)
class OrientedObservation:
    """An exact coordinate and its remembered side at zero."""

    coordinate: Fraction
    side: Direction
    context: str = "default"

    def __post_init__(self) -> None:
        coordinate = _require_fraction(self.coordinate, "observation coordinate")
        if self.side not in (-1, 0, 1) or isinstance(self.side, bool):
            raise ValueError("observation side must be -1, 0, or +1")
        expected = 1 if coordinate > 0 else -1 if coordinate < 0 else 0
        if coordinate != 0 and self.side != expected:
            raise ValueError("a nonzero observation side must match its coordinate")
        _require_identifier(self.context, "observation context")

    @classmethod
    def from_coordinate(cls, coordinate: Fraction, *, context: str = "default") -> "OrientedObservation":
        coordinate = _require_fraction(coordinate, "observation coordinate")
        side: Direction = 1 if coordinate > 0 else -1 if coordinate < 0 else 0
        return cls(coordinate, side, context)

    @property
    def radius(self) -> Fraction:
        return abs(self.coordinate)


@dataclass(frozen=True)
class HybridState:
    """Deterministic state of the oriented-zero automaton."""

    region_id: str
    radius: Fraction
    side: Direction = 0
    armed: bool = True
    step: int = 0
    jumps: int = 0
    last_jump_step: int | None = None
    receipt_head_sha256: str = GENESIS_SHA256

    def __post_init__(self) -> None:
        _require_identifier(self.region_id, "state region_id")
        radius = _require_fraction(self.radius, "state radius")
        if radius < 0:
            raise ValueError("state radius must be nonnegative")
        if self.side not in (-1, 0, 1) or isinstance(self.side, bool):
            raise ValueError("state side must be -1, 0, or +1")
        if radius > 0 and self.side == 0:
            raise ValueError("a nonzero state needs an oriented side")
        if type(self.armed) is not bool:
            raise TypeError("state armed flag must be bool")
        _require_plain_int(self.step, "state step")
        _require_plain_int(self.jumps, "state jumps")
        if (self.jumps == 0) != (self.last_jump_step is None):
            raise ValueError("jump count and last-jump marker must agree")
        if self.last_jump_step is not None:
            _require_plain_int(self.last_jump_step, "last_jump_step", minimum=1)
            if self.last_jump_step > self.step:
                raise ValueError("last jump cannot occur after the current step")
        _require_sha256(self.receipt_head_sha256, "receipt head")

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "scbe.oriented-zero-hybrid-state.v1",
            "region_id": self.region_id,
            "radius": _fraction_payload(self.radius),
            "side": self.side,
            "armed": self.armed,
            "step": self.step,
            "jumps": self.jumps,
            "last_jump_step": self.last_jump_step,
            "receipt_head_sha256": self.receipt_head_sha256,
        }


@dataclass(frozen=True)
class TransitionReceipt:
    """Hash-linked evidence for one observation and state transition."""

    index: int
    graph_sha256: str
    previous_sha256: str
    state_before_sha256: str
    source_region: str
    destination_region: str
    context: str
    side: Direction
    observed_coordinate: Fraction
    observed_radius: Fraction
    ceiling_coordinate: Fraction
    ceiling_gap: Fraction
    armed_before: bool
    armed_after: bool
    outcome: Outcome
    reason: str
    jumps_before: int
    jumps_after: int
    reset_radius: Fraction | None
    receipt_sha256: str

    def __post_init__(self) -> None:
        _require_plain_int(self.index, "receipt index", minimum=1)
        for value, name in (
            (self.graph_sha256, "graph digest"),
            (self.previous_sha256, "previous digest"),
            (self.state_before_sha256, "state-before digest"),
            (self.receipt_sha256, "receipt digest"),
        ):
            _require_sha256(value, name)
        _require_identifier(self.source_region, "receipt source")
        _require_identifier(self.destination_region, "receipt destination")
        _require_identifier(self.context, "receipt context")
        if self.side not in (-1, 0, 1) or isinstance(self.side, bool):
            raise ValueError("receipt side must be -1, 0, or +1")
        for value, name in (
            (self.observed_coordinate, "observed coordinate"),
            (self.observed_radius, "observed radius"),
            (self.ceiling_coordinate, "ceiling coordinate"),
            (self.ceiling_gap, "ceiling gap"),
        ):
            _require_fraction(value, name)
        if self.observed_radius != abs(self.observed_coordinate) or self.observed_radius < 0:
            raise ValueError("receipt radius must match the absolute observation")
        if self.observed_coordinate != 0 and self.side != (1 if self.observed_coordinate > 0 else -1):
            raise ValueError("receipt side must match a nonzero observation")
        if self.ceiling_coordinate <= 0 or self.ceiling_gap < 0:
            raise ValueError("receipt chart coordinates must be nonnegative with a positive projection")
        if self.reset_radius is not None:
            if _require_fraction(self.reset_radius, "receipt reset radius") < 0:
                raise ValueError("receipt reset radius must be nonnegative")
        if type(self.armed_before) is not bool or type(self.armed_after) is not bool:
            raise TypeError("receipt armed flags must be bool")
        if self.outcome not in _OUTCOMES:
            raise ValueError("unknown receipt outcome")
        _require_identifier(self.reason, "receipt reason")
        _require_plain_int(self.jumps_before, "receipt jumps_before")
        _require_plain_int(self.jumps_after, "receipt jumps_after")
        if self.outcome == "JUMP":
            if self.reset_radius is None or self.jumps_after != self.jumps_before + 1 or self.armed_after:
                raise ValueError("jump receipts require one charged jump, a reset, and disarming")
        elif self.reset_radius is not None or self.jumps_after != self.jumps_before:
            raise ValueError("non-jump receipts cannot reset or change the jump count")

    def payload_without_digest(self) -> dict[str, object]:
        return {
            "schema": "scbe.oriented-zero-transition-receipt.v1",
            "index": self.index,
            "graph_sha256": self.graph_sha256,
            "previous_sha256": self.previous_sha256,
            "state_before_sha256": self.state_before_sha256,
            "source_region": self.source_region,
            "destination_region": self.destination_region,
            "context": self.context,
            "side": self.side,
            "observed_coordinate": _fraction_payload(self.observed_coordinate),
            "observed_radius": _fraction_payload(self.observed_radius),
            "ceiling_coordinate": _fraction_payload(self.ceiling_coordinate),
            "ceiling_gap": _fraction_payload(self.ceiling_gap),
            "armed_before": self.armed_before,
            "armed_after": self.armed_after,
            "outcome": self.outcome,
            "reason": self.reason,
            "jumps_before": self.jumps_before,
            "jumps_after": self.jumps_after,
            "reset_radius": None if self.reset_radius is None else _fraction_payload(self.reset_radius),
        }

    def verify_digest(self) -> bool:
        return self.receipt_sha256 == _digest(self.payload_without_digest())


@dataclass(frozen=True)
class StepResult:
    state: HybridState
    receipt: TransitionReceipt


@dataclass(frozen=True)
class TraceResult:
    state: HybridState
    receipts: tuple[TransitionReceipt, ...]


def advance(graph: RegionGraph, state: HybridState, observation: OrientedObservation) -> StepResult:
    """Apply one exact observation to the hybrid state."""

    if not isinstance(graph, RegionGraph):
        raise TypeError("graph must be a RegionGraph")
    graph.validate_state(state)
    if not isinstance(observation, OrientedObservation):
        raise TypeError("observation must be an OrientedObservation")

    region = graph.region(state.region_id)
    radius = observation.radius
    ceiling_coordinate = region.chart.project(radius)
    ceiling_gap = region.chart.gap(radius)
    next_step = state.step + 1
    destination = state.region_id
    result_radius = radius
    armed_after = state.armed
    jumps_after = state.jumps
    last_jump_step = state.last_jump_step
    reset_radius: Fraction | None = None

    if not state.armed:
        if radius >= region.exit_radius:
            outcome: Outcome = "REARM"
            reason = "outside-exit-guard"
            armed_after = True
        else:
            outcome = "HOLD"
            reason = "hysteresis-disarmed"
    elif radius > region.enter_radius:
        outcome = "APPROACH"
        reason = "outside-enter-guard"
    elif observation.side == 0:
        outcome = "QUARANTINE"
        reason = "unresolved-neutral-zero"
        armed_after = False
    elif state.jumps >= graph.jump_budget:
        outcome = "DENY"
        reason = "jump-budget-exhausted"
        armed_after = False
    elif state.last_jump_step is not None and next_step - state.last_jump_step < graph.minimum_dwell_steps:
        outcome = "HOLD"
        reason = "minimum-dwell-not-met"
        armed_after = False
    else:
        edge = graph.edge(state.region_id, observation.side, observation.context)
        if edge is None:
            outcome = "DENY"
            reason = "no-authorized-edge"
            armed_after = False
        else:
            outcome = "JUMP"
            reason = "oriented-enter-guard"
            destination = edge.destination
            reset_radius = edge.reset_radius
            result_radius = edge.reset_radius
            armed_after = False
            jumps_after += 1
            last_jump_step = next_step

    fields: dict[str, object] = {
        "index": next_step,
        "graph_sha256": graph.digest,
        "previous_sha256": state.receipt_head_sha256,
        "state_before_sha256": state.digest,
        "source_region": state.region_id,
        "destination_region": destination,
        "context": observation.context,
        "side": observation.side,
        "observed_coordinate": observation.coordinate,
        "observed_radius": radius,
        "ceiling_coordinate": ceiling_coordinate,
        "ceiling_gap": ceiling_gap,
        "armed_before": state.armed,
        "armed_after": armed_after,
        "outcome": outcome,
        "reason": reason,
        "jumps_before": state.jumps,
        "jumps_after": jumps_after,
        "reset_radius": reset_radius,
    }
    temporary = TransitionReceipt(**fields, receipt_sha256=GENESIS_SHA256)  # type: ignore[arg-type]
    receipt_digest = _digest(temporary.payload_without_digest())
    receipt = TransitionReceipt(**fields, receipt_sha256=receipt_digest)  # type: ignore[arg-type]
    new_state = HybridState(
        region_id=destination,
        radius=result_radius,
        side=observation.side,
        armed=armed_after,
        step=next_step,
        jumps=jumps_after,
        last_jump_step=last_jump_step,
        receipt_head_sha256=receipt.receipt_sha256,
    )
    return StepResult(new_state, receipt)


def run_trace(
    graph: RegionGraph,
    initial_state: HybridState,
    observations: Sequence[OrientedObservation],
) -> TraceResult:
    """Run a finite deterministic trace."""

    if len(observations) > MAX_TRACE_STEPS:
        raise ValueError("trace exceeds the bounded observation count")
    state = initial_state
    receipts: list[TransitionReceipt] = []
    for observation in observations:
        result = advance(graph, state, observation)
        state = result.state
        receipts.append(result.receipt)
    return TraceResult(state, tuple(receipts))


def verify_receipt_chain(
    graph: RegionGraph,
    receipts: Sequence[TransitionReceipt],
    *,
    initial_head_sha256: str = GENESIS_SHA256,
    initial_step: int = 0,
) -> bool:
    """Verify hashes, graph binding, ordering, and region continuity."""

    if not isinstance(graph, RegionGraph):
        return False
    _require_sha256(initial_head_sha256, "initial receipt head")
    _require_plain_int(initial_step, "initial step")
    if len(receipts) > MAX_TRACE_STEPS:
        return False
    previous = initial_head_sha256
    current_region: str | None = None
    expected_index = initial_step + 1
    for receipt in receipts:
        if not isinstance(receipt, TransitionReceipt):
            return False
        if receipt.graph_sha256 != graph.digest or receipt.previous_sha256 != previous or not receipt.verify_digest():
            return False
        if current_region is None:
            current_region = receipt.source_region
        if receipt.index != expected_index or receipt.source_region != current_region:
            return False
        if receipt.outcome != "JUMP" and receipt.destination_region != receipt.source_region:
            return False
        current_region = receipt.destination_region
        previous = receipt.receipt_sha256
        expected_index += 1
    return True


def replay_matches(
    graph: RegionGraph,
    initial_state: HybridState,
    observations: Sequence[OrientedObservation],
    receipts: Sequence[TransitionReceipt],
) -> bool:
    """Re-execute observations and compare every complete receipt."""

    result = run_trace(graph, initial_state, observations)
    return tuple(receipts) == result.receipts and verify_receipt_chain(
        graph,
        receipts,
        initial_head_sha256=initial_state.receipt_head_sha256,
        initial_step=initial_state.step,
    )


def linearized_jump_route(graph: RegionGraph, receipts: Sequence[TransitionReceipt]) -> tuple[str, ...]:
    """Return the ordered region path after the target trace has been observed."""

    if not receipts:
        return ()
    if not verify_receipt_chain(
        graph,
        receipts,
        initial_head_sha256=receipts[0].previous_sha256,
        initial_step=receipts[0].index - 1,
    ):
        raise ValueError("cannot linearize an invalid receipt chain")
    route = [receipts[0].source_region]
    route.extend(receipt.destination_region for receipt in receipts if receipt.outcome == "JUMP")
    return tuple(route)


__all__ = [
    "CeilingMap",
    "Direction",
    "GENESIS_SHA256",
    "HybridState",
    "MAX_EDGES",
    "MAX_EXACT_BITS",
    "MAX_REGIONS",
    "MAX_TRACE_STEPS",
    "OrientedObservation",
    "Outcome",
    "Region",
    "RegionEdge",
    "RegionGraph",
    "StepResult",
    "TraceResult",
    "TransitionReceipt",
    "advance",
    "linearized_jump_route",
    "replay_matches",
    "run_trace",
    "verify_receipt_chain",
]
