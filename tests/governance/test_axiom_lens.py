import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from symphonic_cipher.scbe_aethermoore.axiom_grouped.axiom_lens import (
    AXIOM_INDEX,
    AXIOM_ORDER,
    AxiomLensConfig,
    build_axiom_lens,
)


def _complete_fixture():
    reference = np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 0.0],
        ]
    )
    current = np.asarray(
        [
            [0.2, 0.1],
            [1.5, 0.2],
            [3.2, -0.1],
        ]
    )
    edges = np.asarray([[0, 1], [1, 2]])
    symmetry = np.stack((reference + 0.1, reference - 0.2))
    composed = reference + np.asarray([[0.0, 0.3], [0.2, 0.0], [-0.1, 0.2]])
    timestamps = np.asarray([2.0, 1.0, 3.0])
    return current, reference, edges, symmetry, composed, timestamps


def test_identical_complete_views_have_zero_residual():
    states = np.asarray([[0.2, 0.3], [0.4, 0.5], [0.6, 0.7]])
    result = build_axiom_lens(
        states,
        edges=[[0, 1], [1, 2]],
        reference_states=states,
        timestamps=[0.0, 1.0, 2.0],
        symmetry_states=states,
        composed_states=states,
    )

    assert result.node_residuals.shape == (3, 5)
    assert result.state_gradients_by_axiom.shape == (5, 3, 2)
    assert result.time_gradients_by_axiom.shape == (5, 3)
    assert np.all(result.node_observed)
    assert np.allclose(result.node_residuals, 0.0)
    assert np.allclose(result.node_compliance, 1.0)
    assert result.total_loss == pytest.approx(0.0)
    assert result.overall_coverage == pytest.approx(1.0)
    assert result.evidence_status == "complete"
    assert result.dominant_axiom == (None, None, None)


def test_missing_evidence_is_unobserved_not_a_pass():
    result = build_axiom_lens([[1.0, 2.0], [2.0, 3.0]], edges=[[0, 1]])

    assert not np.any(result.node_observed)
    assert np.all(np.isnan(result.node_compliance))
    assert all(value is None for value in result.loss_by_axiom.values())
    assert result.total_loss == pytest.approx(0.0)
    assert result.overall_coverage == pytest.approx(0.0)
    assert result.evidence_status == "unobserved"
    receipt = result.to_dict()
    assert receipt["node_compliance"] == [[None] * 5, [None] * 5]
    assert "NaN" not in json.dumps(receipt, allow_nan=False)
    assert result.dominant_axiom == (None, None)


def test_each_supplied_view_contributes_to_the_five_axis_field():
    current, reference, edges, symmetry, composed, timestamps = _complete_fixture()
    result = build_axiom_lens(
        current,
        edges=edges,
        reference_states=reference,
        timestamps=timestamps,
        symmetry_states=symmetry,
        composed_states=composed,
    )

    assert set(result.loss_by_axiom) == set(AXIOM_ORDER)
    assert all(
        result.loss_by_axiom[name] is not None and result.loss_by_axiom[name] > 0.0
        for name in AXIOM_ORDER
    )
    assert result.evidence_status == "complete"
    assert np.all(np.isfinite(result.node_residuals))
    assert np.all(np.isfinite(result.state_gradient))
    assert np.all(np.isfinite(result.time_gradient))
    assert result.edge_observed[:, AXIOM_INDEX["locality"]].all()
    assert result.edge_observed[:, AXIOM_INDEX["causality"]].all()


def test_state_gradient_matches_finite_difference():
    current, reference, edges, symmetry, composed, _ = _complete_fixture()
    config = AxiomLensConfig(weights=(0.7, 1.3, 0.0, 0.9, 1.1))
    result = build_axiom_lens(
        current,
        edges=edges,
        reference_states=reference,
        symmetry_states=symmetry,
        composed_states=composed,
        config=config,
    )

    numerical = np.zeros_like(current)
    epsilon = 1e-6
    for node in range(current.shape[0]):
        for feature in range(current.shape[1]):
            plus = current.copy()
            minus = current.copy()
            plus[node, feature] += epsilon
            minus[node, feature] -= epsilon
            plus_loss = build_axiom_lens(
                plus,
                edges=edges,
                reference_states=reference,
                symmetry_states=symmetry,
                composed_states=composed,
                config=config,
            ).total_loss
            minus_loss = build_axiom_lens(
                minus,
                edges=edges,
                reference_states=reference,
                symmetry_states=symmetry,
                composed_states=composed,
                config=config,
            ).total_loss
            numerical[node, feature] = (plus_loss - minus_loss) / (2.0 * epsilon)

    assert result.state_gradient == pytest.approx(numerical, rel=1e-5, abs=1e-6)


def test_time_gradient_matches_finite_difference():
    states = np.asarray([[0.0], [1.0], [2.0]])
    timestamps = np.asarray([2.0, 1.0, 0.5])
    edges = np.asarray([[0, 1], [1, 2]])
    config = AxiomLensConfig(weights=(0.0, 0.0, 1.7, 0.0, 0.0), time_scale=2.0)
    result = build_axiom_lens(states, edges=edges, timestamps=timestamps, config=config)

    numerical = np.zeros_like(timestamps)
    epsilon = 1e-6
    for node in range(timestamps.shape[0]):
        plus = timestamps.copy()
        minus = timestamps.copy()
        plus[node] += epsilon
        minus[node] -= epsilon
        plus_loss = build_axiom_lens(
            states, edges=edges, timestamps=plus, config=config
        ).total_loss
        minus_loss = build_axiom_lens(
            states, edges=edges, timestamps=minus, config=config
        ).total_loss
        numerical[node] = (plus_loss - minus_loss) / (2.0 * epsilon)

    assert result.time_gradient == pytest.approx(numerical, rel=1e-6, abs=1e-6)


def test_stereo_projection_is_deterministic_and_non_mutating():
    current, reference, edges, symmetry, composed, timestamps = _complete_fixture()
    original = current.copy()
    kwargs = {
        "edges": edges,
        "reference_states": reference,
        "timestamps": timestamps,
        "symmetry_states": symmetry,
        "composed_states": composed,
    }

    first = build_axiom_lens(current, **kwargs)
    second = build_axiom_lens(current, **kwargs)

    assert np.array_equal(current, original)
    assert np.array_equal(first.offset_xyz, second.offset_xyz)
    assert np.all(first.left_offset_xyz[:, 0] <= first.offset_xyz[:, 0])
    assert np.all(first.right_offset_xyz[:, 0] >= first.offset_xyz[:, 0])
    assert first.to_dict()["schema"] == "scbe.axiom-lens.v1"


@pytest.mark.parametrize(
    ("edges", "match"),
    [
        ([[0, 2]], "outside the node range"),
        ([[0, 0]], "self edges"),
        ([[0, 0.5]], "integers"),
    ],
)
def test_invalid_edges_are_rejected(edges, match):
    with pytest.raises(ValueError, match=match):
        build_axiom_lens([[0.0], [1.0]], edges=edges)


def test_repository_root_import_uses_the_canonical_lens():
    repo_root = Path(__file__).resolve().parents[2]
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from symphonic_cipher.scbe_aethermoore.axiom_grouped "
                "import build_axiom_lens; "
                "print(build_axiom_lens([[0.0], [1.0]]).to_dict()['schema'])"
            ),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == "scbe.axiom-lens.v1"


def test_configuration_rejects_non_finite_values():
    with pytest.raises(ValueError, match="finite"):
        AxiomLensConfig(time_scale=float("nan"))


def test_canonical_axiom_registry_and_document_shims_are_consistent():
    repo_root = Path(__file__).resolve().parents[2]
    registry = yaml.safe_load(
        (repo_root / "config" / "scbe_core_axioms_v1.yaml").read_text(encoding="utf-8")
    )

    missing_sources = [
        relative_path
        for relative_path in registry["canonical_sources"]
        if not (repo_root / relative_path).exists()
    ]
    assert missing_sources == []
    assert registry["formula_regime_authority"] == (
        "docs/specs/CANONICAL_FORMULA_REGISTRY.md"
    )
    assert [item["name"] for item in registry["formula_regimes"]] == [
        "BOUNDED_SCORE",
        "BOUNDED_WALL",
        "QUADRATIC_EXP_COST",
        "PI_EXP_COST",
    ]

    formula_registry = (
        repo_root / "docs" / "specs" / "CANONICAL_FORMULA_REGISTRY.md"
    ).read_text(encoding="utf-8")
    for regime in (
        "BOUNDED_SCORE",
        "BOUNDED_WALL",
        "QUADRATIC_EXP_COST",
        "PI_EXP_COST",
    ):
        assert regime in formula_registry

    layer_index = (repo_root / "docs" / "specs" / "LAYER_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "BOUNDED_SCORE" in layer_index
    assert "FLIGHT_GOVERNANCE_COUPLING.md" not in layer_index
    assert "F1 0.813" not in layer_index

    assert "Documentation Shim" in (repo_root / "docs" / "LAYER_INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "Documentation Shim" in (
        repo_root / "docs" / "specs" / "CANONICAL_SYSTEM_STATE.md"
    ).read_text(encoding="utf-8")
