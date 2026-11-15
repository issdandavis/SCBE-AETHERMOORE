"""Bounded, framework-neutral model view over HeldContextPacket v1."""

from __future__ import annotations

from dataclasses import dataclass

from held_context import HeldContextPacket, LaneRole, PacketError, Q_SCALE, select_visible_lanes


@dataclass(frozen=True, slots=True)
class LaneSpan:
    lane_id: int
    role: int
    evidence: int
    token_start: int
    token_end: int
    route_start: int
    route_end: int
    exact_payload_bytes: int


@dataclass(frozen=True, slots=True)
class HeldContextModelView:
    token_ids: tuple[int, ...]
    token_lane_ids: tuple[int, ...]
    route_values: tuple[float, ...]
    route_lane_ids: tuple[int, ...]
    lane_spans: tuple[LaneSpan, ...]
    exact_payloads: tuple[tuple[int, bytes], ...]
    token_budget: int
    truncated: bool


def build_model_view(
    packet: HeldContextPacket,
    *,
    current_sequence: int,
    maximum_tokens: int | None = None,
) -> HeldContextModelView:
    """Project visible lanes without collapsing evidence or exact source bytes.

    The result intentionally contains plain tuples rather than a framework tensor.
    A PyTorch, NumPy, Rust, or Java caller may choose its own numeric dtype while
    the packet remains the byte-exact authority.
    """

    packet.validate()
    if maximum_tokens is not None and maximum_tokens < 0:
        raise PacketError("maximum_tokens cannot be negative")
    budget = packet.token_budget if maximum_tokens is None else min(packet.token_budget, maximum_tokens)
    tokens: list[int] = []
    token_lanes: list[int] = []
    routes: list[float] = []
    route_lanes: list[int] = []
    spans: list[LaneSpan] = []
    exact_payloads: list[tuple[int, bytes]] = []
    truncated = False

    for lane in select_visible_lanes(packet, current_sequence=current_sequence):
        token_start = len(tokens)
        remaining = max(0, budget - len(tokens))
        selected = lane.token_ids[:remaining]
        tokens.extend(selected)
        token_lanes.extend([lane.lane_id] * len(selected))
        if len(selected) != len(lane.token_ids):
            truncated = True
        route_start = len(routes)
        routes.extend(value / Q_SCALE for value in lane.route_q1e6)
        route_lanes.extend([lane.lane_id] * len(lane.route_q1e6))
        if lane.payload:
            exact_payloads.append((lane.lane_id, lane.payload))
        spans.append(
            LaneSpan(
                lane_id=lane.lane_id,
                role=int(lane.role),
                evidence=int(lane.evidence),
                token_start=token_start,
                token_end=len(tokens),
                route_start=route_start,
                route_end=len(routes),
                exact_payload_bytes=len(lane.payload),
            )
        )
    if len(tokens) > budget:
        raise AssertionError("adapter exceeded bounded token budget")
    if any(span.role == int(LaneRole.OBSERVED) and span.token_end < span.token_start for span in spans):
        raise AssertionError("invalid lane span")
    return HeldContextModelView(
        token_ids=tuple(tokens),
        token_lane_ids=tuple(token_lanes),
        route_values=tuple(routes),
        route_lane_ids=tuple(route_lanes),
        lane_spans=tuple(spans),
        exact_payloads=tuple(exact_payloads),
        token_budget=budget,
        truncated=truncated,
    )


__all__ = ["HeldContextModelView", "LaneSpan", "build_model_view"]
