from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from python.scbe.atomic_context_bundle import (
    _solve_box_equality_qp,
    build_atomic_context_bundle,
    compute_drift_clock,
    equilibrate_semantic_charge,
    fuse_atomic_context,
)
from python.scbe.chemical_fusion import fuse_atomic_states
from python.scbe.reaction_state import sha256_value
from scripts.research.atomic_context_stitch_demo import build_demo_receipt

TABLE_HASH = sha256_value({"fixture": "atomic-context-table"})


def _bundle(*, neighbor_count: int = 2, step_clock: int = 12):
    return build_atomic_context_bundle(
        ["not", "build", "the", "compiler"],
        tokenizer_id="fixture-b256-v1",
        token_table_sha256=TABLE_HASH,
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        positions=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.25), (3.0, 0.0)],
        language="en",
        context_class="operator",
        context_epoch=3,
        step_clock=step_clock,
        total_charge=0.0,
        neighbor_count=neighbor_count,
    )


def test_bundle_is_deterministic_and_keeps_exact_token_identity() -> None:
    left = _bundle()
    right = _bundle()

    assert left == right
    assert left.bundle_hash == right.bundle_hash
    assert [node.atomic_state.token for node in left.nodes] == [
        "not",
        "build",
        "the",
        "compiler",
    ]
    assert len({node.node_id for node in left.nodes}) == len(left.nodes)


def test_semantic_charge_is_finite_conserved_and_deterministic() -> None:
    bundle = _bundle()
    first = equilibrate_semantic_charge(bundle)
    second = equilibrate_semantic_charge(bundle)

    assert first == second
    assert first.result_hash == second.result_hash
    assert first.conservation_error <= 1e-12
    assert first.projected_residual <= 1e-9
    assert first.converged is True
    assert math.isfinite(first.condition_number)
    assert all(math.isfinite(value) for value in first.charges.values())


def test_local_edges_change_the_equilibrium_without_changing_identity() -> None:
    isolated = _bundle(neighbor_count=0)
    connected = _bundle(neighbor_count=2)
    isolated_result = equilibrate_semantic_charge(isolated)
    connected_result = equilibrate_semantic_charge(connected)

    assert [node.atomic_state.token for node in isolated.nodes] == [node.atomic_state.token for node in connected.nodes]
    assert isolated_result.charge_by_node != connected_result.charge_by_node
    assert connected_result.edge_tension


def test_zero_charge_gain_reproduces_the_frozen_fusion_baseline() -> None:
    bundle = _bundle()
    equilibrium = equilibrate_semantic_charge(bundle)
    stitched = fuse_atomic_context(bundle, equilibrium, charge_gain=0.0)
    node_index = {node.node_id: index for index, node in enumerate(bundle.nodes)}
    edges = [(node_index[edge.source_id], node_index[edge.target_id]) for edge in bundle.edges]
    edge_weights = {(node_index[edge.source_id], node_index[edge.target_id]): edge.coupling for edge in bundle.edges}
    baseline = fuse_atomic_states(
        [node.atomic_state for node in bundle.nodes],
        weights=[1.0] * len(bundle.nodes),
        edges=edges,
        edge_weights=edge_weights,
    )

    assert stitched == baseline


def test_bounded_charge_gain_changes_votes_but_not_frozen_states() -> None:
    bundle = _bundle()
    equilibrium = equilibrate_semantic_charge(bundle)
    baseline = fuse_atomic_context(bundle, equilibrium, charge_gain=0.0)
    intervention = fuse_atomic_context(bundle, equilibrium, charge_gain=0.5)

    assert intervention.states == baseline.states
    assert intervention.reconstruction_votes != baseline.reconstruction_votes


def test_drift_clock_is_separate_from_wrapped_phase_and_slows_under_pressure() -> None:
    bundle = _bundle(step_clock=12)
    equilibrium = equilibrate_semantic_charge(bundle)
    calm = compute_drift_clock(bundle, equilibrium)
    pressured = compute_drift_clock(bundle, equilibrium, congestion=2.0, route_cost=1.0)

    assert calm.step_clock == pressured.step_clock == 12
    assert 0.0 <= calm.wrapped_phase_radians < 2.0 * math.pi
    assert pressured.model_time_increment < calm.model_time_increment
    assert "not photon propagation" in pressured.claim_boundary


def test_bundle_rejects_a_fake_or_missing_token_table_digest() -> None:
    with pytest.raises(ValueError, match="token_table_sha256"):
        build_atomic_context_bundle(
            ["build"],
            tokenizer_id="fixture",
            token_table_sha256="not-a-digest",
            runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        )


def test_charge_cap_rejects_an_impossible_total() -> None:
    bundle = build_atomic_context_bundle(
        ["build", "token"],
        tokenizer_id="fixture-b256-v1",
        token_table_sha256=TABLE_HASH,
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        total_charge=4.0,
    )
    with pytest.raises(ValueError, match="incompatible"):
        equilibrate_semantic_charge(bundle, max_abs_charge=1.0)


def test_feasible_active_charge_cap_reaches_the_box_constrained_optimum() -> None:
    equilibrium = equilibrate_semantic_charge(_bundle(), max_abs_charge=0.5)

    assert equilibrium.converged is True
    assert equilibrium.active_bound_count > 0
    assert equilibrium.conservation_error <= 1e-9
    assert equilibrium.projected_residual <= 1e-9
    assert max(abs(value) for value in equilibrium.charges.values()) <= 0.5 + 1e-12
    assert equilibrium.energy == pytest.approx(-1.2536633985, abs=1e-9)


def test_active_set_reopens_a_bound_to_reach_a_near_saturated_total() -> None:
    cap = 0.1339936712379145
    total = 0.39381220734476796
    system = np.diag([0.6005362145431703, 1.186298742503191, 1.8519197207257094])
    linear = np.asarray(
        [3.8703729231577, 0.23759326373917533, 0.27707262434454094],
        dtype=np.float64,
    )

    solution, _lagrange, active_count, projected_residual = _solve_box_equality_qp(
        system,
        linear,
        total=total,
        cap=cap,
        tolerance=1e-9,
    )

    assert float(np.sum(solution)) == pytest.approx(total, abs=1e-10)
    assert float(np.max(np.abs(solution))) <= cap + 1e-12
    assert active_count == 2
    assert projected_residual <= 1e-8


def test_bundle_identity_binds_charge_language_and_context() -> None:
    baseline = _bundle()
    charged = build_atomic_context_bundle(
        ["not", "build", "the", "compiler"],
        tokenizer_id="fixture-b256-v1",
        token_table_sha256=TABLE_HASH,
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        language="en",
        context_class="operator",
        total_charge=0.25,
    )
    other_context = build_atomic_context_bundle(
        ["not", "build", "the", "compiler"],
        tokenizer_id="fixture-b256-v1",
        token_table_sha256=TABLE_HASH,
        runtime_profile="PY_REFERENCE14+ATOMIC_STITCH_V1",
        language="en",
        context_class="narrative",
    )

    assert len({baseline.bundle_id, charged.bundle_id, other_context.bundle_id}) == 3


def test_public_frozen_results_normalize_sequence_inputs_to_tuples() -> None:
    bundle = _bundle()
    rebuilt_bundle = replace(bundle, nodes=list(bundle.nodes), edges=list(bundle.edges))
    equilibrium = equilibrate_semantic_charge(bundle)
    rebuilt_equilibrium = replace(
        equilibrium,
        charge_by_node=list(equilibrium.charge_by_node),
        edge_tension=list(equilibrium.edge_tension),
    )

    assert isinstance(rebuilt_bundle.nodes, tuple)
    assert isinstance(rebuilt_bundle.edges, tuple)
    assert isinstance(rebuilt_equilibrium.charge_by_node, tuple)
    assert isinstance(rebuilt_equilibrium.edge_tension, tuple)


def test_durable_demo_receipt_matches_the_executable_mechanics() -> None:
    path = Path("docs/research/ATOMIC_NODE_CONTEXT_STITCH_RESULT_20261113.json")
    durable = json.loads(path.read_text(encoding="utf-8"))
    rebuilt = build_demo_receipt(["not", "build", "the", "compiler"], charge_gain=0.25)

    assert durable == rebuilt
    assert durable["claim_status"] == "PASS_MECHANICS_ONLY"
    assert durable["training_authorized"] is False
