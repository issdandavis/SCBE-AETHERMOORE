from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from itertools import product
import random

import pytest

from src.crypto import oriented_zero_hybrid as H


def f(numerator: int, denominator: int = 1) -> Fraction:
    return Fraction(numerator, denominator)


def region(region_id: str, *, enter: Fraction = f(1, 16), exit_radius: Fraction = f(1, 8)) -> H.Region:
    return H.Region(region_id, enter, exit_radius, H.CeilingMap(f(7), f(1, 4)))


def graph(*, jump_budget: int = 4, minimum_dwell_steps: int = 2) -> H.RegionGraph:
    regions = tuple(region(name) for name in ("root", "positive", "negative"))
    edges = tuple(
        H.RegionEdge(source, side, "default", "positive" if side > 0 else "negative", f(1, 4))
        for source in ("root", "positive", "negative")
        for side in (-1, 1)
    )
    return H.RegionGraph(regions, edges, jump_budget, minimum_dwell_steps)


def initial() -> H.HybridState:
    return H.HybridState("root", f(1), side=1)


def observation(value: Fraction, *, side: H.Direction | None = None, context: str = "default") -> H.OrientedObservation:
    if side is None:
        return H.OrientedObservation.from_coordinate(value, context=context)
    return H.OrientedObservation(value, side, context)


class TestCeilingMap:
    def test_zero_maps_to_exact_ceiling(self) -> None:
        chart = H.CeilingMap(f(11), f(3, 5))
        assert chart.project(f(0)) == f(11)
        assert chart.gap(f(0)) == f(0)

    def test_approach_is_exact_monotone_and_bounded(self) -> None:
        chart = H.CeilingMap(f(13), f(2, 3))
        radii = [f(1, 2**depth) for depth in range(20)]
        coordinates = [chart.project(radius) for radius in radii]
        gaps = [chart.gap(radius) for radius in radii]
        assert all(f(0) < value < chart.ceiling for value in coordinates)
        assert coordinates == sorted(coordinates)
        assert gaps == sorted(gaps, reverse=True)
        assert all(value + gap == chart.ceiling for value, gap in zip(coordinates, gaps, strict=True))

    def test_projection_round_trip_is_exact(self) -> None:
        chart = H.CeilingMap(f(17, 3), f(23, 7))
        for radius in (f(0), f(1, 10**50), f(5, 9), f(10**80 + 3, 10**40 + 7)):
            assert chart.unproject(chart.project(radius)) == radius

    def test_gap_has_expected_closed_form(self) -> None:
        chart = H.CeilingMap(f(5), f(3))
        for radius in (f(0), f(1, 9), f(3), f(10**100)):
            assert chart.gap(radius) == chart.ceiling * radius / (radius + chart.scale)

    def test_exact_arithmetic_has_a_bit_length_resource_bound(self) -> None:
        chart = H.CeilingMap(f(1), f(1))
        largest_allowed = Fraction((1 << (H.MAX_EXACT_BITS - 1)) - 1)
        assert chart.project(largest_allowed) > 0
        with pytest.raises(ValueError, match="bit exact-arithmetic limit"):
            chart.project(Fraction(1 << H.MAX_EXACT_BITS))

    def test_inverse_refuses_a_derived_value_beyond_the_bit_bound(self) -> None:
        chart = H.CeilingMap(Fraction((1 << (H.MAX_EXACT_BITS - 1)) - 1), f(1))
        tiny = Fraction(1, (1 << (H.MAX_EXACT_BITS - 1)) - 1)
        with pytest.raises(ValueError, match="bit exact-arithmetic limit"):
            chart.unproject(tiny)

    @pytest.mark.parametrize(
        "ceiling,scale",
        [(f(0), f(1)), (f(-1), f(1)), (f(1), f(0)), (f(1), f(-1)), (1, f(1)), (f(1), 1)],
    )
    def test_invalid_chart_parameters_are_refused(self, ceiling: object, scale: object) -> None:
        with pytest.raises((TypeError, ValueError)):
            H.CeilingMap(ceiling, scale)  # type: ignore[arg-type]

    @pytest.mark.parametrize("radius", [f(-1), 0, 0.0, True])
    def test_invalid_radius_is_refused(self, radius: object) -> None:
        with pytest.raises((TypeError, ValueError)):
            H.CeilingMap(f(1), f(1)).project(radius)  # type: ignore[arg-type]

    @pytest.mark.parametrize("coordinate", [f(0), f(-1), f(2), 1, 0.5])
    def test_invalid_inverse_coordinate_is_refused(self, coordinate: object) -> None:
        with pytest.raises((TypeError, ValueError)):
            H.CeilingMap(f(1), f(1)).unproject(coordinate)  # type: ignore[arg-type]


class TestGraphValidation:
    def test_graph_digest_is_deterministic(self) -> None:
        assert graph().digest == graph().digest
        assert len(graph().digest) == 64

    def test_graph_digest_binds_edge_order(self) -> None:
        first = graph()
        second = H.RegionGraph(
            first.regions, tuple(reversed(first.edges)), first.jump_budget, first.minimum_dwell_steps
        )
        assert first.digest != second.digest

    def test_duplicate_region_is_refused(self) -> None:
        item = region("same")
        with pytest.raises(ValueError, match="unique"):
            H.RegionGraph((item, item), (), 1)

    def test_ambiguous_edge_is_refused(self) -> None:
        item = region("root")
        edge = H.RegionEdge("root", 1, "default", "root", f(1, 4))
        with pytest.raises(ValueError, match="ambiguous"):
            H.RegionGraph((item,), (edge, edge), 1)

    def test_unknown_edge_endpoint_is_refused(self) -> None:
        edge = H.RegionEdge("root", 1, "default", "missing", f(1, 4))
        with pytest.raises(ValueError, match="declared"):
            H.RegionGraph((region("root"),), (edge,), 1)

    def test_unknown_region_lookup_is_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown"):
            graph().region("missing")

    def test_reset_inside_exit_guard_is_refused(self) -> None:
        edge = H.RegionEdge("root", 1, "default", "root", f(1, 9))
        with pytest.raises(ValueError, match="outside"):
            H.RegionGraph((region("root"),), (edge,), 1)

    def test_negative_edge_reset_is_refused(self) -> None:
        with pytest.raises(ValueError, match="nonnegative"):
            H.RegionEdge("root", 1, "default", "root", f(-1))

    @pytest.mark.parametrize("side", [-2, 0, 2, True])
    def test_edges_require_oriented_nonzero_side(self, side: object) -> None:
        with pytest.raises(ValueError):
            H.RegionEdge("root", side, "default", "root", f(1))  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "regions,edges",
        [([region("root")], ()), ((region("root"),), []), ((), ()), (("root",), ())],
    )
    def test_graph_collections_are_typed_immutable_tuples(self, regions: object, edges: object) -> None:
        with pytest.raises(TypeError):
            H.RegionGraph(regions, edges, 1)  # type: ignore[arg-type]

    def test_wrong_edge_member_type_is_refused(self) -> None:
        with pytest.raises(TypeError, match="RegionEdge"):
            H.RegionGraph((region("root"),), ("not-an-edge",), 1)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "jump_budget,dwell",
        [
            (0, 2),
            (1, 0),
            (True, 2),
            (1, 2.5),
            (H.MAX_TRACE_STEPS + 1, 2),
            (1, H.MAX_TRACE_STEPS + 1),
            (1 << H.MAX_EXACT_BITS, 2),
        ],
    )
    def test_graph_limits_require_positive_plain_integers(self, jump_budget: object, dwell: object) -> None:
        with pytest.raises(ValueError):
            H.RegionGraph((region("root"),), (), jump_budget, dwell)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "regions,edges",
        [
            ((region("root"),) * (H.MAX_REGIONS + 1), ()),
            (
                (region("root"),),
                (H.RegionEdge("root", 1, "default", "root", f(1, 4)),) * (H.MAX_EDGES + 1),
            ),
        ],
    )
    def test_graph_size_is_bounded_before_expensive_validation(
        self, regions: tuple[H.Region, ...], edges: tuple[H.RegionEdge, ...]
    ) -> None:
        with pytest.raises(ValueError, match="bounded"):
            H.RegionGraph(regions, edges, 1)

    @pytest.mark.parametrize("enter,exit_radius", [(f(-1), f(1)), (f(1), f(1)), (f(2), f(1)), (0, f(1))])
    def test_invalid_guard_geometry_is_refused(self, enter: object, exit_radius: object) -> None:
        with pytest.raises((TypeError, ValueError)):
            H.Region("root", enter, exit_radius, H.CeilingMap(f(1), f(1)))  # type: ignore[arg-type]

    def test_region_requires_a_chart_and_stable_identifier(self) -> None:
        with pytest.raises(TypeError, match="CeilingMap"):
            H.Region("root", f(0), f(1), object())  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="identifier"):
            H.Region("bad region", f(0), f(1), H.CeilingMap(f(1), f(1)))

    def test_neutral_edge_lookup_has_no_implicit_route(self) -> None:
        assert graph().edge("root", 0, "default") is None

    def test_runtime_duplicate_edge_tamper_fails_closed(self) -> None:
        configured = graph()
        object.__setattr__(configured, "edges", configured.edges + (configured.edges[0],))
        with pytest.raises(ValueError, match="ambiguous"):
            configured.edge(*configured.edges[0].key)


class TestOrientedObservation:
    @pytest.mark.parametrize("value,side", [(f(3), 1), (f(-3), -1), (f(0), -1), (f(0), 0), (f(0), 1)])
    def test_valid_orientations(self, value: Fraction, side: H.Direction) -> None:
        item = H.OrientedObservation(value, side)
        assert item.radius == abs(value)

    @pytest.mark.parametrize("value,side", [(f(1), -1), (f(1), 0), (f(-1), 1), (f(-1), 0)])
    def test_nonzero_coordinate_side_must_match(self, value: Fraction, side: H.Direction) -> None:
        with pytest.raises(ValueError, match="match"):
            H.OrientedObservation(value, side)

    @pytest.mark.parametrize("value", [0, 0.0, True])
    def test_observation_rejects_inexact_types(self, value: object) -> None:
        with pytest.raises(TypeError):
            H.OrientedObservation(value, 0)  # type: ignore[arg-type]

    def test_observation_rejects_a_side_outside_the_trit_alphabet(self) -> None:
        with pytest.raises(ValueError, match=r"-1, 0, or \+1"):
            H.OrientedObservation(f(0), 2)  # type: ignore[arg-type]

    def test_factory_does_not_invent_orientation_at_zero(self) -> None:
        assert H.OrientedObservation.from_coordinate(f(0)).side == 0


class TestTransitions:
    def test_outside_enter_guard_only_approaches(self) -> None:
        result = H.advance(graph(), initial(), observation(f(1, 4)))
        assert result.receipt.outcome == "APPROACH"
        assert result.state.region_id == "root"
        assert result.state.jumps == 0

    def test_exact_enter_guard_jumps_by_positive_side(self) -> None:
        result = H.advance(graph(), initial(), observation(f(1, 16)))
        assert result.receipt.outcome == "JUMP"
        assert result.receipt.ceiling_coordinate == f(28, 5)
        assert result.receipt.ceiling_gap == f(7, 5)
        assert result.state.region_id == "positive"
        assert result.state.radius == f(1, 4)
        assert result.state.armed is False

    def test_negative_side_selects_negative_region(self) -> None:
        result = H.advance(graph(), initial(), observation(f(-1, 32)))
        assert result.receipt.outcome == "JUMP"
        assert result.state.region_id == "negative"

    @pytest.mark.parametrize("side,destination", [(-1, "negative"), (1, "positive")])
    def test_exact_zero_can_retain_a_resolved_side(self, side: H.Direction, destination: str) -> None:
        result = H.advance(graph(), initial(), observation(f(0), side=side))
        assert result.receipt.outcome == "JUMP"
        assert result.state.region_id == destination
        assert result.receipt.ceiling_gap == 0

    def test_unoriented_zero_is_quarantined(self) -> None:
        result = H.advance(graph(), initial(), observation(f(0), side=0))
        assert result.receipt.outcome == "QUARANTINE"
        assert result.receipt.reason == "unresolved-neutral-zero"
        assert result.state.region_id == "root"
        assert result.state.jumps == 0
        assert result.state.armed is False

    def test_missing_context_fails_closed(self) -> None:
        result = H.advance(graph(), initial(), observation(f(0), side=1, context="unknown"))
        assert result.receipt.outcome == "DENY"
        assert result.receipt.reason == "no-authorized-edge"
        assert result.state.jumps == 0

    def test_hysteresis_requires_exit_before_another_jump(self) -> None:
        configured = graph()
        first = H.advance(configured, initial(), observation(f(0), side=1))
        held = H.advance(configured, first.state, observation(f(1, 32)))
        rearmed = H.advance(configured, held.state, observation(f(1, 8)))
        second = H.advance(configured, rearmed.state, observation(f(-1, 32)))
        assert [item.receipt.outcome for item in (first, held, rearmed, second)] == [
            "JUMP",
            "HOLD",
            "REARM",
            "JUMP",
        ]
        assert second.state.region_id == "negative"

    def test_exit_threshold_is_inclusive(self) -> None:
        configured = graph()
        jumped = H.advance(configured, initial(), observation(f(0), side=1))
        assert H.advance(configured, jumped.state, observation(f(1, 8))).receipt.outcome == "REARM"

    def test_below_exit_threshold_stays_disarmed(self) -> None:
        configured = graph()
        jumped = H.advance(configured, initial(), observation(f(0), side=1))
        held = H.advance(configured, jumped.state, observation(f(1, 8) - f(1, 10**20)))
        assert held.receipt.outcome == "HOLD"
        assert held.state.armed is False

    def test_minimum_dwell_blocks_early_reentry(self) -> None:
        configured = graph(minimum_dwell_steps=4)
        first = H.advance(configured, initial(), observation(f(0), side=1))
        rearmed = H.advance(configured, first.state, observation(f(1, 4)))
        held = H.advance(configured, rearmed.state, observation(f(0), side=-1))
        assert held.receipt.reason == "minimum-dwell-not-met"
        rearmed_again = H.advance(configured, held.state, observation(f(1, 4)))
        allowed = H.advance(configured, rearmed_again.state, observation(f(0), side=-1))
        assert allowed.receipt.outcome == "JUMP"

    def test_jump_budget_fails_closed(self) -> None:
        configured = graph(jump_budget=1)
        first = H.advance(configured, initial(), observation(f(0), side=1))
        rearmed = H.advance(configured, first.state, observation(f(1, 4)))
        denied = H.advance(configured, rearmed.state, observation(f(0), side=-1))
        assert denied.receipt.outcome == "DENY"
        assert denied.receipt.reason == "jump-budget-exhausted"
        assert denied.state.jumps == 1

    def test_repeated_zero_observations_cannot_chatter(self) -> None:
        observations = [observation(f(0), side=1)] * 100
        result = H.run_trace(graph(jump_budget=100), initial(), observations)
        assert sum(receipt.outcome == "JUMP" for receipt in result.receipts) == 1
        assert all(receipt.outcome == "HOLD" for receipt in result.receipts[1:])

    def test_context_selects_an_explicit_alternate_route(self) -> None:
        regions = (region("root"), region("audit"))
        edges = (H.RegionEdge("root", 1, "audit", "audit", f(1, 4)),)
        configured = H.RegionGraph(regions, edges, 1)
        result = H.advance(configured, initial(), observation(f(0), side=1, context="audit"))
        assert result.state.region_id == "audit"

    def test_state_exceeding_budget_is_rejected(self) -> None:
        corrupt = replace(initial(), step=1, jumps=5, last_jump_step=1)
        with pytest.raises(ValueError, match="budget"):
            H.advance(graph(jump_budget=4), corrupt, observation(f(1)))

    @pytest.mark.parametrize(
        "changes",
        [
            {"radius": f(-1)},
            {"side": 2},
            {"side": 0},
            {"armed": 1},
            {"step": 1, "jumps": 1, "last_jump_step": None},
            {"step": 1, "jumps": 0, "last_jump_step": 1},
            {"step": 1, "jumps": 1, "last_jump_step": 2},
            {"receipt_head_sha256": "not-a-hash"},
        ],
    )
    def test_invalid_state_shapes_are_refused(self, changes: dict[str, object]) -> None:
        with pytest.raises((TypeError, ValueError)):
            replace(initial(), **changes)

    def test_advance_requires_typed_graph_state_and_observation(self) -> None:
        configured = graph()
        with pytest.raises(TypeError, match="graph"):
            H.advance(object(), initial(), observation(f(1)))  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="state"):
            configured.validate_state(object())  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="observation"):
            H.advance(configured, initial(), object())  # type: ignore[arg-type]


class TestReceiptsAndReplay:
    def trace(self) -> tuple[H.RegionGraph, H.HybridState, list[H.OrientedObservation], H.TraceResult]:
        configured = graph()
        start = initial()
        observations = [
            observation(f(1, 4)),
            observation(f(0), side=1),
            observation(f(1, 4)),
            observation(f(0), side=-1),
        ]
        return configured, start, observations, H.run_trace(configured, start, observations)

    def test_receipt_binds_graph_state_and_exact_chart_values(self) -> None:
        configured, start, _, result = self.trace()
        first = result.receipts[0]
        assert first.graph_sha256 == configured.digest
        assert first.state_before_sha256 == start.digest
        assert first.previous_sha256 == start.receipt_head_sha256
        assert first.ceiling_coordinate + first.ceiling_gap == configured.region("root").chart.ceiling

    def test_receipt_chain_and_deterministic_replay_pass(self) -> None:
        configured, start, observations, result = self.trace()
        assert H.verify_receipt_chain(configured, result.receipts)
        assert H.replay_matches(configured, start, observations, result.receipts)
        assert result.state.receipt_head_sha256 == result.receipts[-1].receipt_sha256

    def test_tampered_receipt_is_detected(self) -> None:
        configured, _, _, result = self.trace()
        altered = list(result.receipts)
        altered[1] = replace(altered[1], reason="outside-enter-guard")
        assert not H.verify_receipt_chain(configured, altered)

    def test_reordered_receipts_are_detected(self) -> None:
        configured, _, _, result = self.trace()
        altered = list(result.receipts)
        altered[1], altered[2] = altered[2], altered[1]
        assert not H.verify_receipt_chain(configured, altered)

    def test_receipt_is_bound_to_graph_policy(self) -> None:
        _, _, _, result = self.trace()
        assert not H.verify_receipt_chain(graph(jump_budget=5), result.receipts)

    def test_changed_observation_fails_full_replay(self) -> None:
        configured, start, observations, result = self.trace()
        observations[0] = observation(f(1, 3))
        assert not H.replay_matches(configured, start, observations, result.receipts)

    def test_route_linearizes_only_completed_jumps(self) -> None:
        configured, _, _, result = self.trace()
        assert H.linearized_jump_route(configured, result.receipts) == ("root", "positive", "negative")

    def test_invalid_chain_cannot_be_linearized(self) -> None:
        configured, _, _, result = self.trace()
        altered = list(result.receipts)
        altered[-1] = replace(altered[-1], destination_region="positive")
        with pytest.raises(ValueError, match="invalid"):
            H.linearized_jump_route(configured, altered)

    def test_empty_trace_has_empty_linearization(self) -> None:
        assert H.linearized_jump_route(graph(), ()) == ()

    def test_trace_and_receipt_verification_refuse_unbounded_sequences(self) -> None:
        class OversizedSequence:
            def __len__(self) -> int:
                return H.MAX_TRACE_STEPS + 1

            def __iter__(self):
                raise AssertionError("bounded check must happen before iteration")

        values = OversizedSequence()
        with pytest.raises(ValueError, match="bounded"):
            H.run_trace(graph(), initial(), values)  # type: ignore[arg-type]
        assert not H.verify_receipt_chain(graph(), values)  # type: ignore[arg-type]

    def test_untyped_chain_member_is_refused(self) -> None:
        assert not H.verify_receipt_chain(graph(), [object()])  # type: ignore[list-item]
        assert not H.verify_receipt_chain(object(), ())  # type: ignore[arg-type]

    def test_genesis_chain_cannot_skip_its_first_index(self) -> None:
        configured = graph()
        receipt = H.advance(configured, initial(), observation(f(1, 4))).receipt
        altered = replace(receipt, index=99)
        altered = replace(altered, receipt_sha256=H._digest(altered.payload_without_digest()))
        assert altered.verify_digest()
        assert not H.verify_receipt_chain(configured, (altered,))

    def test_replay_from_a_nonzero_continuation_step_uses_that_index(self) -> None:
        configured = graph()
        prefix = H.advance(configured, initial(), observation(f(1, 4)))
        observations = [observation(f(1, 3)), observation(f(1, 5))]
        continuation = H.run_trace(configured, prefix.state, observations)
        assert H.verify_receipt_chain(
            configured,
            continuation.receipts,
            initial_head_sha256=prefix.state.receipt_head_sha256,
            initial_step=prefix.state.step,
        )
        assert H.replay_matches(configured, prefix.state, observations, continuation.receipts)

    def test_rehashed_index_and_region_discontinuities_are_refused(self) -> None:
        configured = graph()
        observations = [observation(f(1, 4)), observation(f(1, 3))]
        result = H.run_trace(configured, initial(), observations)

        bad_index = replace(result.receipts[1], index=result.receipts[1].index + 1)
        bad_index = replace(bad_index, receipt_sha256=H._digest(bad_index.payload_without_digest()))
        assert not H.verify_receipt_chain(configured, (result.receipts[0], bad_index))

        bad_source = replace(result.receipts[1], source_region="negative")
        bad_source = replace(bad_source, receipt_sha256=H._digest(bad_source.payload_without_digest()))
        assert not H.verify_receipt_chain(configured, (result.receipts[0], bad_source))

    def test_rehashed_nonjump_destination_change_is_refused(self) -> None:
        configured = graph()
        receipt = H.advance(configured, initial(), observation(f(1, 4))).receipt
        altered = replace(receipt, destination_region="positive")
        altered = replace(altered, receipt_sha256=H._digest(altered.payload_without_digest()))
        assert altered.verify_digest()
        assert not H.verify_receipt_chain(configured, (altered,))

    @pytest.mark.parametrize(
        "changes",
        [
            {"side": 2},
            {"observed_radius": f(99)},
            {"observed_coordinate": f(-1, 4), "side": 1, "observed_radius": f(1, 4)},
            {"ceiling_coordinate": f(0)},
            {"ceiling_gap": f(-1)},
            {"armed_before": 1},
            {"outcome": "UNKNOWN"},
            {"reset_radius": f(-1)},
            {"jumps_after": 1},
        ],
    )
    def test_receipt_rejects_internally_inconsistent_fields(self, changes: dict[str, object]) -> None:
        receipt = H.advance(graph(), initial(), observation(f(1, 4))).receipt
        with pytest.raises((TypeError, ValueError)):
            replace(receipt, **changes)

    def test_jump_receipt_requires_reset_increment_and_disarming(self) -> None:
        receipt = H.advance(graph(), initial(), observation(f(0), side=1)).receipt
        for changes in ({"reset_radius": None}, {"jumps_after": 0}, {"armed_after": True}):
            with pytest.raises(ValueError, match="jump receipts"):
                replace(receipt, **changes)


class TestFiniteModelProperties:
    def test_exhaustive_short_traces_preserve_invariants(self) -> None:
        configured = graph(jump_budget=3)
        alphabet = (
            observation(f(1, 4)),
            observation(f(-1, 4)),
            observation(f(1, 32)),
            observation(f(-1, 32)),
            observation(f(0), side=0),
        )
        for trace in product(alphabet, repeat=5):
            result = H.run_trace(configured, initial(), trace)
            assert result.state.jumps <= configured.jump_budget
            assert H.verify_receipt_chain(configured, result.receipts)
            outcomes = [receipt.outcome for receipt in result.receipts]
            assert all(not (left == right == "JUMP") for left, right in zip(outcomes, outcomes[1:]))
            for receipt in result.receipts:
                assert receipt.observed_radius >= 0
                assert (
                    receipt.ceiling_coordinate + receipt.ceiling_gap
                    == configured.region(receipt.source_region).chart.ceiling
                )
                assert 0 < receipt.ceiling_coordinate <= configured.region(receipt.source_region).chart.ceiling

    def test_random_long_traces_are_deterministic_and_bounded(self) -> None:
        configured = graph(jump_budget=7, minimum_dwell_steps=3)
        for seed in range(100):
            rng = random.Random(seed)
            values = (f(0), f(1, 64), f(1, 16), f(1, 8), f(1, 4))
            observations: list[H.OrientedObservation] = []
            for _ in range(100):
                radius = rng.choice(values)
                side: H.Direction = rng.choice((-1, 0, 1)) if radius == 0 else rng.choice((-1, 1))
                coordinate = radius * side
                observations.append(observation(coordinate, side=side))
            first = H.run_trace(configured, initial(), observations)
            second = H.run_trace(configured, initial(), observations)
            assert first == second
            assert first.state.jumps <= configured.jump_budget
            assert H.replay_matches(configured, initial(), observations, first.receipts)
