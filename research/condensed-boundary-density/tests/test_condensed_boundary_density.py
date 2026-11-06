from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

import condensed_boundary_density as cbd


def two_concepts(
    *,
    phase_scramble: bool = False,
    binding_shuffle: bool = False,
    mass_scale: float = 1.0,
):
    phases_a = (0.0, 0.05, -0.04)
    phases_b = (
        (0.0, 2 * math.pi / 3, 4 * math.pi / 3)
        if phase_scramble
        else (0.02, -0.03, 0.04)
    )
    cells = []
    for prefix, seed, phases in (
        ("a", "concept-a", phases_a),
        ("b", "concept-b", phases_b),
    ):
        for dimension, (layer, phase, mass) in enumerate(
            zip(("token", "context", "policy"), phases, (1.0, 0.9, 1.1))
        ):
            cells.append(
                cbd.BoundaryCell(
                    f"{prefix}{dimension}",
                    dimension,
                    layer,
                    seed,
                    mass=mass * mass_scale,
                    phase=phase,
                    frequency=0.7 + 0.2 * dimension,
                    trits=(1, 0, -1),
                )
            )
    links = [
        cbd.TransportLink("a0", "a1", 1.0, kind="sibling"),
        cbd.TransportLink("a1", "a2", 1.0, kind="sibling"),
        cbd.TransportLink("a0", "a2", 0.8, kind="sibling"),
        cbd.TransportLink("b0", "b1", 1.0, kind="sibling"),
        cbd.TransportLink("b1", "b2", 1.0, kind="sibling"),
        cbd.TransportLink("b0", "b2", 0.8, kind="sibling"),
        cbd.TransportLink("a2", "b2", 0.08, kind="context"),
    ]
    if binding_shuffle:
        links[0] = cbd.TransportLink("a0", "b1", 1.0, kind="sibling")
        links[3] = cbd.TransportLink("b0", "a1", 1.0, kind="sibling")
    return cells, links


def test_boundary_of_boundary_and_hodge_are_valid():
    boundaries, _ = cbd.oriented_triangle()
    assert np.array_equal(boundaries[1] @ boundaries[2], np.zeros((3, 1)))
    for dimension in range(3):
        laplacian = cbd.hodge_laplacian(boundaries, dimension)
        assert np.allclose(laplacian, laplacian.T)
        assert np.linalg.eigvalsh(laplacian).min(initial=0.0) >= -1e-10


def test_barycentric_lift_keeps_orientation_as_phase():
    boundaries, ids = cbd.oriented_triangle()
    links = cbd.barycentric_links(boundaries, ids)
    assert len(links) == 9
    assert {round(link.phase, 8) for link in links} == {0.0, round(math.pi, 8)}


def test_connection_laplacian_is_hermitian_positive_semidefinite():
    cells, links = two_concepts()
    laplacian = cbd.connection_laplacian(cells, links)
    assert np.allclose(laplacian, laplacian.conj().T)
    assert np.linalg.eigvalsh(laplacian).min(initial=0.0) >= -1e-10


def test_single_node_cannot_be_a_poly_nodal_condensate():
    cells, links = two_concepts()
    metrics = cbd.cluster_metrics(cells, links, ["a0"])
    assert metrics["poly_nodal_factor"] == 0.0
    assert metrics["condensation_index"] == 0.0


def test_phase_coherence_separates_aligned_and_scrambled_clusters():
    aligned_cells, aligned_links = two_concepts(phase_scramble=False)
    scrambled_cells, scrambled_links = two_concepts(phase_scramble=True)
    aligned = cbd.cluster_metrics(aligned_cells, aligned_links, ["b0", "b1", "b2"])
    scrambled = cbd.cluster_metrics(
        scrambled_cells, scrambled_links, ["b0", "b1", "b2"]
    )
    assert aligned["coherence"] > 0.99
    assert scrambled["coherence"] < 0.1
    assert aligned["condensation_index"] > scrambled["condensation_index"]


def test_shuffled_sibling_binding_is_explicitly_rejected():
    cells, links = two_concepts(binding_shuffle=True)
    with pytest.raises(ValueError, match="concept seeds"):
        cbd.connection_laplacian(cells, links)
    measured = cbd.sheaf_consistency(cells, links)
    assert measured["binding_violations"] == 2
    assert measured["consistency"] < 1.0


def test_more_cluster_mass_lowers_the_same_internal_frequencies():
    cells, links = two_concepts(mass_scale=1.0)
    heavy_cells, heavy_links = two_concepts(mass_scale=4.0)
    light = cbd.normal_modes(cells[:3], links[:3])["frequencies"]
    heavy = cbd.normal_modes(heavy_cells[:3], heavy_links[:3])["frequencies"]
    assert np.allclose(heavy, light / 2.0, atol=1e-8)


def test_cluster_coarsening_preserves_energy_on_cluster_constant_states():
    cells, links = two_concepts()
    result = cbd.coarsen_partition(
        cells, links, [("a0", "a1", "a2"), ("b0", "b1", "b2")]
    )
    coarse_state = np.asarray([0.4 + 0.2j, -0.3 + 0.1j])
    fine_state = result["lift"] @ coarse_state
    fine_energy = np.real(np.vdot(fine_state, result["fine_laplacian"] @ fine_state))
    coarse_energy = np.real(
        np.vdot(coarse_state, result["coarse_laplacian"] @ coarse_state)
    )
    assert np.isclose(fine_energy, coarse_energy)
    assert np.allclose(np.diag(result["coarse_mass"]), [3.0, 3.0])


def test_recursive_cell_cluster_meta_cell_coarsening_matches_direct_map():
    cells, links = two_concepts()
    fine = cbd.coarsen_partition(cells, links, [("a0", "a1", "a2"), ("b0", "b1", "b2")])
    leaf_to_subcluster = np.asarray(
        [
            [1, 0, 0, 0],
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
    )
    subcluster_to_concept = np.asarray([[1, 0], [1, 0], [0, 1], [0, 1]])
    hierarchy = cbd.coarsen_operator_hierarchy(
        fine["fine_laplacian"],
        fine["fine_mass"],
        (leaf_to_subcluster, subcluster_to_concept),
    )
    assert np.array_equal(hierarchy["total_lift"], fine["lift"])
    assert np.allclose(hierarchy["coarse_laplacian"], fine["coarse_laplacian"])
    assert np.allclose(hierarchy["coarse_mass"], fine["coarse_mass"])
    state = np.asarray([0.3 + 0.2j, -0.5 + 0.1j])
    fine_state = hierarchy["total_lift"] @ state
    assert np.isclose(
        np.vdot(fine_state, fine["fine_laplacian"] @ fine_state),
        np.vdot(state, hierarchy["coarse_laplacian"] @ state),
    )


def fabric_contracts(base_rule: str | None = None):
    base_rule = base_rule or hashlib.sha256(b"shared-cell-rule-v1").hexdigest()
    leaves = [
        cbd.RepeatedCellContract(
            f"{concept}{slot}",
            (concept_index, slot),
            concept,
            base_rule,
            16,
            8,
        )
        for concept_index, concept in enumerate(("rose", "thorn"))
        for slot in range(3)
    ]
    metas = [
        cbd.RepeatedCellContract(
            concept,
            (concept_index,),
            concept,
            base_rule,
            16,
            8,
            generation=1,
            child_ids=tuple(f"{concept}{slot}" for slot in range(3)),
        )
        for concept_index, concept in enumerate(("rose", "thorn"))
    ]
    root = cbd.RepeatedCellContract(
        "wafer",
        (0,),
        "root",
        base_rule,
        16,
        8,
        generation=2,
        child_ids=("rose", "thorn"),
    )
    return leaves + metas + [root]


def test_repeated_cell_manifest_preserves_shared_rule_and_recursive_lineage():
    contracts = fabric_contracts()
    result = cbd.validate_repeated_fabric(contracts)
    assert result["cell_count"] == 9
    assert result["leaf_count"] == 6
    assert result["meta_cell_count"] == 3
    assert result["max_generation"] == 2
    assert len(result["manifest_sha256"]) == 64
    assert result == cbd.validate_repeated_fabric(list(reversed(contracts)))


def test_repeated_fabric_rejects_one_private_base_rule_disguised_as_a_cell():
    contracts = fabric_contracts()
    changed = hashlib.sha256(b"private-unmatched-rule").hexdigest()
    leaf = contracts[0]
    contracts[0] = cbd.RepeatedCellContract(
        leaf.cell_id,
        leaf.address,
        leaf.sector_id,
        changed,
        leaf.state_width,
        leaf.message_width,
    )
    with pytest.raises(ValueError, match="shared base rule"):
        cbd.validate_repeated_fabric(contracts)


def test_exact_output_trace_reconstructs_linear_transport():
    cells, links = two_concepts()
    readout = np.asarray([0.3, -0.2j, 0.5, -0.1, 0.2j, 0.4])
    result = cbd.step_with_trace(cells, links, readout, dt=0.03, diffusion=0.08)
    assert abs(result["trace_residual"]) < 1e-12
    assert len(result["output_terms"]) == len(cells) + 1
    assert {
        term["seed_id"] for term in result["output_terms"] if term["kind"] == "cell"
    } == {"concept-a", "concept-b"}


def test_unstable_explicit_step_is_refused():
    cells, links = two_concepts()
    with pytest.raises(ValueError, match="stability"):
        cbd.transition_operator(cells, links, dt=10.0, diffusion=10.0)


def test_cluster_metrics_are_invariant_to_cell_order():
    cells, links = two_concepts()
    expected = cbd.cluster_metrics(cells, links, ["a0", "a1", "a2"])
    observed = cbd.cluster_metrics(
        list(reversed(cells)), list(reversed(links)), ["a2", "a0", "a1"]
    )
    for key in expected:
        assert (
            observed[key] == pytest.approx(expected[key])
            if isinstance(expected[key], float)
            else observed[key] == expected[key]
        )
